-- PostgreSQL init script for persisted AI inventory and self-assessment data.

BEGIN;

CREATE TABLE IF NOT EXISTS ai_inventory_submissions (
    use_case_id TEXT PRIMARY KEY,
    use_case_name TEXT,
    business_unit TEXT,
    model_creator TEXT,
    model_usage TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    repeat_blocks JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS self_assessment_submissions (
    assessment_id TEXT PRIMARY KEY,
    ai_inventory_use_case_id TEXT
        REFERENCES ai_inventory_submissions (use_case_id)
        ON DELETE SET NULL,
    selected_personas TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    selected_use_cases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    answers JSONB NOT NULL DEFAULT '{}'::jsonb,
    vayu_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    relevant_risks TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    recommended_controls TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_inventory_payload_gin
    ON ai_inventory_submissions
    USING GIN (payload);

CREATE INDEX IF NOT EXISTS idx_ai_inventory_repeat_blocks_gin
    ON ai_inventory_submissions
    USING GIN (repeat_blocks);

CREATE INDEX IF NOT EXISTS idx_self_assessment_answers_gin
    ON self_assessment_submissions
    USING GIN (answers);

CREATE INDEX IF NOT EXISTS idx_self_assessment_inventory_fk
    ON self_assessment_submissions (ai_inventory_use_case_id);

CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ai_inventory_submissions_updated_at ON ai_inventory_submissions;
CREATE TRIGGER trg_ai_inventory_submissions_updated_at
    BEFORE UPDATE ON ai_inventory_submissions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_timestamp();

DROP TRIGGER IF EXISTS trg_self_assessment_submissions_updated_at ON self_assessment_submissions;
CREATE TRIGGER trg_self_assessment_submissions_updated_at
    BEFORE UPDATE ON self_assessment_submissions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_timestamp();

COMMIT;
