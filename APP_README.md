# CoSAI Risk Map Streamlit Application

A Streamlit-based interactive web application for the Coalition for Secure AI Risk Map, providing a 3-step assessment workflow.

## Features

1. **🔍 Assessment Page** - Interactive questionnaire to assess your AI security posture
2. **🛡️ Control Mapping** - View recommended security controls based on identified risks
3. **📊 Risk Analysis** - Detailed analysis of risks and mitigation strategies

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have the YAML data files in `risk-map/yaml/`:
   - `risks.yaml`
   - `controls.yaml`
   - `self-assessment.yaml`
   - `personas.yaml`

## Running the Application

Start the Streamlit app:
```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

1. **Start Assessment**: Navigate to the Assessment page and select your role(s) (Model Creator, Model Consumer, or both)
2. **Answer Questions**: Answer the assessment questions based on your organization's AI implementation
3. **View Controls**: Review the recommended security controls that address your identified risks
4. **Analyze Risks**: Explore detailed information about each risk and how controls can mitigate them

## Application Structure

```
app/
├── __init__.py
├── data_loader.py          # YAML data loading and processing
└── pages/
    ├── __init__.py
    ├── assessment.py       # Assessment questionnaire page
    ├── control_mapping.py  # Control mapping page
    └── risk_analysis.py    # Risk analysis page
streamlit_app.py            # Main application entry point
```

## Data Flow

1. User selects personas and answers questions
2. System calculates relevant risks based on answers
3. System maps risks to applicable controls
4. User can view detailed risk and control information

## PostgreSQL Persistence (Optional)

This app can persist AI Inventory and Self-Assessment records to PostgreSQL and load them back by ID.

1. Initialize tables:
```bash
psql "$DATABASE_URL" -f scripts/sql/init_postgresql.sql
```

2. Set one of:
```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```
or
```bash
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=cosai
export PGUSER=postgres
export PGPASSWORD=postgres
export PGSSLMODE=prefer
```

3. Run the app:
```bash
streamlit run streamlit_app.py
```

4. Generate ER diagram (online from live DB schema):
```bash
python scripts/generate_er_diagram.py --schema public
```

5. Generate ER diagram (offline from SQL file, no DB needed):
```bash
python scripts/generate_er_diagram.py --sql-file scripts/sql/init_postgresql.sql
```

## Notes

- If DB settings are not configured, data remains in Streamlit session state only.
- The application dynamically filters questions based on selected personas.
- Risk relevance is calculated based on answer values matching the `relevance` criteria in the self-assessment YAML.
