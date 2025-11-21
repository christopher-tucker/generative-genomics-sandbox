CREATE TABLE IF NOT EXISTS experiments (id SERIAL PRIMARY KEY, descriptor JSONB, model_version TEXT, created_at TIMESTAMP DEFAULT now());
