CREATE DATABASE nhs;
\c nhs

-- Drop and recreate table to store raw NHS RTT data with dynamic structure
DROP TABLE IF EXISTS rtt_provider_raw;

CREATE TABLE rtt_provider_raw(
    -- Use JSONB to store the entire row flexibly
    raw_data               jsonb NOT NULL,
    
    -- Extract key fields for indexing and querying
    period                 text,
    provider_org_code      text,
    provider_org_name      text,
    treatment_function_code text,
    treatment_function_name text,
    rtt_part_type          text,
    
    -- Add timestamp for data tracking
    loaded_at              timestamp DEFAULT NOW(),
    
    -- Generate unique ID from key fields to prevent duplicates
    CONSTRAINT pk_rtt_provider_raw PRIMARY KEY 
        (period, provider_org_code, treatment_function_code, rtt_part_type)
);
