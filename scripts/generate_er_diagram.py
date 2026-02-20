#!/usr/bin/env python3
"""Generate a Mermaid ER diagram from a PostgreSQL schema."""
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _connect_target(cli_dsn: str | None) -> str | Dict[str, Any]:
    if cli_dsn:
        return cli_dsn

    dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    env_values = {k: os.getenv(k) for k in required}
    missing = [k for k, v in env_values.items() if not v]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            f"Missing DB settings: {missing_str}. Set --dsn or environment variables."
        )

    return {
        "host": env_values["PGHOST"],
        "port": env_values["PGPORT"],
        "dbname": env_values["PGDATABASE"],
        "user": env_values["PGUSER"],
        "password": env_values["PGPASSWORD"],
        "sslmode": os.getenv("PGSSLMODE", "prefer"),
    }


def _entity_name(table_name: str) -> str:
    return table_name.upper()


def _format_type(data_type: str, udt_name: str) -> str:
    dt = (data_type or "").lower()
    udt = (udt_name or "").lower()
    if dt == "array":
        return f"{udt.lstrip('_')}[]"
    if dt == "timestamp with time zone":
        return "timestamptz"
    if dt == "timestamp without time zone":
        return "timestamp"
    return dt.replace(" ", "_")


def _fetch_tables(cur: Any, schema: str) -> List[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """,
        (schema,),
    )
    return [row["table_name"] for row in cur.fetchall()]


def _fetch_columns(cur: Any, schema: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT
            c.table_name,
            c.column_name,
            c.data_type,
            c.udt_name,
            c.ordinal_position
        FROM information_schema.columns c
        WHERE c.table_schema = %s
        ORDER BY c.table_name, c.ordinal_position;
        """,
        (schema,),
    )
    return cur.fetchall()


def _fetch_pk_columns(cur: Any, schema: str) -> set[Tuple[str, str]]:
    cur.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
          AND tc.constraint_type = 'PRIMARY KEY';
        """,
        (schema,),
    )
    return {(row["table_name"], row["column_name"]) for row in cur.fetchall()}


def _fetch_fk_columns(cur: Any, schema: str) -> set[Tuple[str, str]]:
    cur.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
          AND tc.constraint_type = 'FOREIGN KEY';
        """,
        (schema,),
    )
    return {(row["table_name"], row["column_name"]) for row in cur.fetchall()}


def _fetch_fk_relationships(cur: Any, schema: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT
            tc.constraint_name,
            kcu.table_name AS child_table,
            kcu.column_name AS child_column,
            ccu.table_name AS parent_table,
            ccu.column_name AS parent_column,
            kcu.ordinal_position
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema = ccu.table_schema
        WHERE tc.table_schema = %s
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.constraint_name, kcu.ordinal_position;
        """,
        (schema,),
    )
    return cur.fetchall()


def _group_columns_by_table(columns: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for col in columns:
        grouped[col["table_name"]].append(col)
    return grouped


def _group_fk_relationships(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        c_name = row["constraint_name"]
        if c_name not in grouped:
            grouped[c_name] = {
                "constraint_name": c_name,
                "child_table": row["child_table"],
                "parent_table": row["parent_table"],
                "pairs": [],
            }
        grouped[c_name]["pairs"].append((row["parent_column"], row["child_column"]))
    return list(grouped.values())


def _split_top_level_commas(text: str) -> List[str]:
    """Split SQL definition blocks by commas, ignoring nested parentheses."""
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for ch in text:
        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            buf.append(ch)
            continue
        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            buf.append(ch)
            continue

        if not in_single_quote and not in_double_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == "," and depth == 0:
                piece = "".join(buf).strip()
                if piece:
                    parts.append(piece)
                buf = []
                continue

        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_column_type(rest: str) -> str:
    """Extract column SQL type from the remainder of a column definition."""
    keywords = {
        "PRIMARY",
        "REFERENCES",
        "NOT",
        "NULL",
        "DEFAULT",
        "CHECK",
        "UNIQUE",
        "CONSTRAINT",
        "COLLATE",
        "GENERATED",
    }
    tokens = rest.split()
    out: List[str] = []
    for token in tokens:
        upper = token.upper()
        if upper in keywords:
            break
        out.append(token)
    return " ".join(out).strip().strip(",")


def _parse_column_names(csv_value: str) -> List[str]:
    return [c.strip().strip('"') for c in csv_value.split(",") if c.strip()]


def _parse_sql_schema(
    sql_text: str,
) -> tuple[List[str], List[Dict[str, Any]], set[Tuple[str, str]], set[Tuple[str, str]], List[Dict[str, Any]]]:
    """Parse CREATE TABLE statements from SQL and extract ER metadata."""
    create_pattern = re.compile(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([A-Za-z_][\w]*)\s*\((.*?)\);",
        flags=re.IGNORECASE | re.DOTALL,
    )

    tables: List[str] = []
    columns: List[Dict[str, Any]] = []
    pk_cols: set[Tuple[str, str]] = set()
    fk_cols: set[Tuple[str, str]] = set()
    fk_rows: List[Dict[str, Any]] = []

    for match in create_pattern.finditer(sql_text):
        table_name = match.group(1)
        body = match.group(2)
        tables.append(table_name)
        items = _split_top_level_commas(body)

        for idx, raw_item in enumerate(items, start=1):
            item = " ".join(raw_item.split())
            upper_item = item.upper()

            # Table-level constraints
            if upper_item.startswith("CONSTRAINT ") or upper_item.startswith("PRIMARY KEY") or upper_item.startswith("FOREIGN KEY"):
                pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", item, flags=re.IGNORECASE)
                if pk_match:
                    for col in _parse_column_names(pk_match.group(1)):
                        pk_cols.add((table_name, col))

                fk_match = re.search(
                    r"(?:CONSTRAINT\s+([A-Za-z_][\w]*)\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*"
                    r"REFERENCES\s+([A-Za-z_][\w]*)\s*\(([^)]+)\)",
                    item,
                    flags=re.IGNORECASE,
                )
                if fk_match:
                    constraint_name = fk_match.group(1) or f"{table_name}_fk_{len(fk_rows) + 1}"
                    child_cols = _parse_column_names(fk_match.group(2))
                    parent_table = fk_match.group(3)
                    parent_cols = _parse_column_names(fk_match.group(4))

                    for child_col, parent_col in zip(child_cols, parent_cols):
                        fk_cols.add((table_name, child_col))
                        fk_rows.append(
                            {
                                "constraint_name": constraint_name,
                                "child_table": table_name,
                                "child_column": child_col,
                                "parent_table": parent_table,
                                "parent_column": parent_col,
                                "ordinal_position": 1,
                            }
                        )
                continue

            # Column definitions
            col_match = re.match(r'^"?(?P<col>[A-Za-z_][\w]*)"?\s+(?P<rest>.+)$', item)
            if not col_match:
                continue

            col_name = col_match.group("col")
            rest = col_match.group("rest")
            col_type = _parse_column_type(rest) or "text"
            columns.append(
                {
                    "table_name": table_name,
                    "column_name": col_name,
                    "data_type": col_type,
                    "udt_name": "",
                    "ordinal_position": idx,
                }
            )

            if re.search(r"\bPRIMARY\s+KEY\b", rest, flags=re.IGNORECASE):
                pk_cols.add((table_name, col_name))

            fk_match = re.search(
                r"REFERENCES\s+([A-Za-z_][\w]*)\s*\(([^)]+)\)",
                rest,
                flags=re.IGNORECASE,
            )
            if fk_match:
                parent_table = fk_match.group(1)
                parent_col = _parse_column_names(fk_match.group(2))[0]
                fk_cols.add((table_name, col_name))
                fk_rows.append(
                    {
                        "constraint_name": f"{table_name}_{col_name}_fk",
                        "child_table": table_name,
                        "child_column": col_name,
                        "parent_table": parent_table,
                        "parent_column": parent_col,
                        "ordinal_position": 1,
                    }
                )

    return tables, columns, pk_cols, fk_cols, fk_rows


def _render_mermaid(
    tables: List[str],
    columns_by_table: Dict[str, List[Dict[str, Any]]],
    pk_cols: set[Tuple[str, str]],
    fk_cols: set[Tuple[str, str]],
    fk_relationships: List[Dict[str, Any]],
) -> str:
    lines: List[str] = ["erDiagram"]

    for table_name in tables:
        entity = _entity_name(table_name)
        lines.append(f"  {entity} {{")
        for col in columns_by_table.get(table_name, []):
            data_type = _format_type(col.get("data_type", ""), col.get("udt_name", ""))
            col_name = col.get("column_name", "")
            tags: List[str] = []
            key = (table_name, col_name)
            if key in pk_cols:
                tags.append("PK")
            if key in fk_cols:
                tags.append("FK")
            suffix = f" {' '.join(tags)}" if tags else ""
            lines.append(f"    {data_type} {col_name}{suffix}")
        lines.append("  }")

    for rel in fk_relationships:
        parent = _entity_name(rel["parent_table"])
        child = _entity_name(rel["child_table"])
        pairs = ", ".join(f"{p}->{c}" for p, c in rel["pairs"])
        lines.append(f'  {parent} ||--o{{ {child} : "{pairs}"')

    lines.append("")
    return "\n".join(lines)


def _write_markdown_wrapper(markdown_path: Path, mermaid_code: str) -> None:
    content = (
        "# PostgreSQL ER Diagram\n\n"
        "```mermaid\n"
        f"{mermaid_code.rstrip()}\n"
        "```\n"
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=None, help="Postgres DSN (optional).")
    parser.add_argument("--schema", default="public", help="Schema to introspect.")
    parser.add_argument(
        "--sql-file",
        default="",
        help="Offline mode: parse CREATE TABLE statements from this SQL file instead of a live DB.",
    )
    parser.add_argument(
        "--output",
        default="risk-map/diagrams/postgres-er.mermaid",
        help="Output Mermaid file path.",
    )
    parser.add_argument(
        "--markdown-output",
        default="risk-map/diagrams/postgres-er.md",
        help="Optional markdown wrapper output path. Use empty string to disable.",
    )
    args = parser.parse_args()
    if args.sql_file:
        sql_path = Path(args.sql_file)
        if not sql_path.exists():
            raise RuntimeError(f"SQL file not found: {sql_path}")
        sql_text = sql_path.read_text(encoding="utf-8")
        tables, columns, pk_cols, fk_cols, fk_rows = _parse_sql_schema(sql_text)
        if not tables:
            raise RuntimeError(f"No CREATE TABLE statements found in {sql_path}")
    else:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for online mode. Install dependencies with "
                "`pip install -r requirements.txt`, or use --sql-file for offline mode."
            ) from exc

        target = _connect_target(args.dsn)
        connect_kwargs: Dict[str, Any] = {"row_factory": dict_row}

        if isinstance(target, str):
            conn = psycopg.connect(target, **connect_kwargs)
        else:
            conn = psycopg.connect(**target, **connect_kwargs)

        try:
            with conn.cursor() as cur:
                tables = _fetch_tables(cur, args.schema)
                if not tables:
                    raise RuntimeError(f"No tables found in schema '{args.schema}'.")
                columns = _fetch_columns(cur, args.schema)
                pk_cols = _fetch_pk_columns(cur, args.schema)
                fk_cols = _fetch_fk_columns(cur, args.schema)
                fk_rows = _fetch_fk_relationships(cur, args.schema)
        finally:
            conn.close()

    mermaid = _render_mermaid(
        tables=tables,
        columns_by_table=_group_columns_by_table(columns),
        pk_cols=pk_cols,
        fk_cols=fk_cols,
        fk_relationships=_group_fk_relationships(fk_rows),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mermaid, encoding="utf-8")
    print(f"Wrote Mermaid ER diagram: {output_path}")

    markdown_output = (args.markdown_output or "").strip()
    if markdown_output:
        _write_markdown_wrapper(Path(markdown_output), mermaid)
        print(f"Wrote markdown wrapper: {markdown_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
