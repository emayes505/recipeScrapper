CREATE TABLE IF NOT EXISTS recipe_imports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    submitted_url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    error_message TEXT,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_recipe_imports_id ON recipe_imports (id);