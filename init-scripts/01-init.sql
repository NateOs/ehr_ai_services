
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

-- Create facilities table
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    external_id VARCHAR(255) UNIQUE
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    facility_id UUID REFERENCES facilities(id),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vector_dbs table
CREATE TABLE IF NOT EXISTS vector_dbs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    facility_id UUID REFERENCES facilities(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create collections table
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vector_db_id UUID REFERENCES vector_dbs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create patient_identifiers table (MOVED BEFORE documents)
CREATE TABLE IF NOT EXISTS patient_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_code VARCHAR(255) NOT NULL UNIQUE,
    external_id VARCHAR(255),
    facility_id UUID REFERENCES facilities(id),
    age_range VARCHAR(50),
    gender VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drop and recreate the documents table with correct schema
DROP TABLE IF EXISTS documents CASCADE;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    patient_code VARCHAR(255),
    facility_id UUID NOT NULL REFERENCES facilities(id),
    collection_id UUID REFERENCES collections(id),
    patient_identifier_id UUID REFERENCES patient_identifiers(id),
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    document_metadata JSONB,
    content TEXT,
    embedding VECTOR(1536),
    document_category VARCHAR(100) DEFAULT 'clinical',
    sensitivity_level VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_patient_identifiers_patient_code ON patient_identifiers(patient_code);
CREATE INDEX IF NOT EXISTS idx_patient_identifiers_facility_id ON patient_identifiers(facility_id);
CREATE INDEX IF NOT EXISTS idx_documents_patient_identifier_id ON documents(patient_identifier_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_facility_id ON documents(facility_id);
CREATE INDEX IF NOT EXISTS idx_documents_patient_code ON documents(patient_code);
CREATE INDEX IF NOT EXISTS idx_facilities_name ON facilities(name);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_collections_vector_db_id ON collections(vector_db_id);
