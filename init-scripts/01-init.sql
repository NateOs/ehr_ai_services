-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the data_embeddings table (used by LlamaIndex)
CREATE TABLE IF NOT EXISTS data_embeddings (
    id SERIAL PRIMARY KEY,
    text TEXT,
    metadata_ JSON,
    node_id VARCHAR,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS data_embeddings_embedding_idx ON data_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);