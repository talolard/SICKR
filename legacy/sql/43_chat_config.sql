-- Chat runtime configuration plane (DuckDB-backed, Django-free).

CREATE TABLE IF NOT EXISTS app.system_prompt_template_config (
    key VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    template_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (key, version)
);

CREATE TABLE IF NOT EXISTS app.prompt_variant_set_config (
    name VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    max_variants SMALLINT NOT NULL DEFAULT 5,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.prompt_variant_set_template_link (
    variant_set_name VARCHAR NOT NULL,
    template_key VARCHAR NOT NULL,
    template_version VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (variant_set_name, template_key, template_version)
);

CREATE TABLE IF NOT EXISTS app.feedback_reason_tag_config (
    scope VARCHAR NOT NULL,
    polarity VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (scope, polarity, label)
);

CREATE TABLE IF NOT EXISTS app.expansion_policy_config (
    key VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    auto_mode_enabled BOOLEAN NOT NULL DEFAULT true,
    min_confidence DOUBLE NOT NULL DEFAULT 0.70,
    min_constraint_signals INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

INSERT OR IGNORE INTO app.system_prompt_template_config (
    key,
    version,
    title,
    template_text,
    is_active,
    created_at,
    updated_at
)
VALUES
(
    'summary-default',
    'v1',
    'Balanced summary',
    'You are an IKEA shopping assistant.\n'
    'Task: return concise recommendations from candidate products.\n'
    'Rules:\n'
    '1) Use only candidate IDs and names provided.\n'
    '2) Keep summary practical and short.\n'
    '3) Mention tradeoffs where relevant.\n\n'
    'User query: {user_query}\n'
    'Candidates (ID | name):\n'
    '{candidate_lines}\n',
    true,
    now(),
    now()
),
(
    'summary-budget',
    'v1',
    'Budget-focused summary',
    'You are an IKEA assistant focused on value-for-money picks.\n'
    'Prefer likely budget-fit items and concise tradeoffs.\n\n'
    'User query: {user_query}\n'
    'Candidates (ID | name):\n'
    '{candidate_lines}\n',
    true,
    now(),
    now()
),
(
    'summary-small-space',
    'v1',
    'Small-space summary',
    'You are an IKEA assistant optimizing for compact spaces.\n'
    'Prefer compact/flexible options and placement guidance.\n\n'
    'User query: {user_query}\n'
    'Candidates (ID | name):\n'
    '{candidate_lines}\n',
    true,
    now(),
    now()
);

INSERT OR IGNORE INTO app.prompt_variant_set_config (
    name,
    title,
    description,
    is_active,
    max_variants,
    created_at,
    updated_at
)
VALUES
(
    'default-compare-set',
    'Default Prompt Comparison Set',
    'Balanced, budget, and small-space recommendation variants.',
    true,
    3,
    now(),
    now()
);

INSERT OR IGNORE INTO app.prompt_variant_set_template_link (
    variant_set_name,
    template_key,
    template_version,
    created_at
)
VALUES
('default-compare-set', 'summary-default', 'v1', now()),
('default-compare-set', 'summary-budget', 'v1', now()),
('default-compare-set', 'summary-small-space', 'v1', now());

INSERT OR IGNORE INTO app.expansion_policy_config (
    key,
    title,
    is_active,
    auto_mode_enabled,
    min_confidence,
    min_constraint_signals,
    notes,
    updated_at
)
VALUES
(
    'default',
    'Default expansion policy',
    true,
    true,
    0.70,
    1,
    'Default auto mode confidence thresholds for chat runtime.',
    now()
);
