-- EU AI Act Article 12: automatic logging of all AI decisions
CREATE TABLE ai_decision_audit_log (
    id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,

    -- What happened
    decision_type   TEXT NOT NULL,
    -- Values: 'search_ranking', 'match_explanation', 'salary_prediction',
    --         'skill_extraction', 'dedup_decision', 'profile_match'

    -- Who/what made the decision
    model_provider  TEXT NOT NULL,         -- 'gemini', 'openai', 'xgboost', 'rule_based', 'cross_encoder'
    model_version   TEXT NOT NULL,         -- 'gemini-embedding-001', 'gpt-4o-mini', 'ms-marco-MiniLM-L-6-v2'

    -- Input (hashed for privacy — never store raw PII)
    input_hash      TEXT NOT NULL,         -- SHA-256 of input text
    input_summary   TEXT,                  -- Non-PII summary: "query: Python developer, location: London"

    -- Output
    output_summary  TEXT NOT NULL,         -- "returned 20 results, top: Senior Python Dev at TechCo"
    confidence      FLOAT,                -- Model confidence score (0–1)

    -- Context
    user_id         UUID,                  -- NULL for anonymous searches
    job_id          BIGINT,                -- Related job if applicable
    session_id      TEXT,                  -- Browser session for grouping

    -- Performance
    latency_ms      INT,                   -- Processing time
    token_count     INT,                   -- LLM tokens used (NULL for non-LLM)
    cost_usd        NUMERIC(8,6),          -- Estimated cost

    -- Human oversight (Article 14)
    requires_review BOOLEAN DEFAULT FALSE, -- Flag for manual review
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     TEXT,
    review_outcome  TEXT                   -- 'approved', 'corrected', 'rejected'
);

-- Indexes for compliance queries
CREATE INDEX idx_audit_created ON ai_decision_audit_log(created_at DESC);
CREATE INDEX idx_audit_type ON ai_decision_audit_log(decision_type);
CREATE INDEX idx_audit_user ON ai_decision_audit_log(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_review ON ai_decision_audit_log(requires_review) WHERE requires_review = TRUE;

-- RLS: service_role writes, no public reads
ALTER TABLE ai_decision_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to audit log"
    ON ai_decision_audit_log FOR ALL
    USING (auth.role() = 'service_role');

-- No anon/authenticated access — audit logs are internal only
