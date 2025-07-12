#!/usr/bin/env python
"""Generic ETL runner – pluggable data sources → Postgres."""
import os, time, importlib, pandas as pd, psycopg
import json

def _load_config():
    """Load environment variables from config.env file if it exists."""
    config_file = "config.env"
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✓ Loaded config from {config_file}")
    else:
        print(f"⚠ No {config_file} found, using environment variables")

# Load config on import
_load_config()

def _get_fetcher():
    """Instantiate fetcher based on DATA_SOURCE env (default: nhs)."""
    name = os.getenv("DATA_SOURCE", "nhs")
    mod = importlib.import_module("data_sources")
    try:
        return getattr(mod, f"{name}_fetcher")()
    except AttributeError:
        raise RuntimeError(f"Unknown DATA_SOURCE: {name}")

def _normalize_column_name(name: str) -> str:
    """Convert column name to snake_case"""
    return name.lower().strip().replace(" ", "_").replace("(", "").replace(")", "")

def _load(df: pd.DataFrame):
    # Clean column names for easier access
    df.columns = [_normalize_column_name(col) for col in df.columns]
    
    rows_inserted = 0
    
    with psycopg.connect(os.getenv("PG_CONN"), autocommit=True) as conn:
        with conn.cursor() as cur:
            # Process each row
            for _, row in df.iterrows():
                try:
                    # Convert row to JSON for storage
                    raw_data = row.to_dict()
                    
                    # Extract key fields for indexing
                    period = str(raw_data.get('period', ''))
                    provider_org_code = str(raw_data.get('provider_org_code', ''))
                    provider_org_name = str(raw_data.get('provider_org_name', ''))
                    treatment_function_code = str(raw_data.get('treatment_function_code', ''))
                    treatment_function_name = str(raw_data.get('treatment_function_name', ''))
                    rtt_part_type = str(raw_data.get('rtt_part_type', ''))
                    
                    # Skip rows with missing key data
                    if not all([period, provider_org_code, treatment_function_code, rtt_part_type]):
                        continue
                    
                    # Clean None/NaN values in JSON
                    clean_data = {}
                    for k, v in raw_data.items():
                        if pd.isna(v) or str(v).lower() in ['nan', 'none', '']:
                            clean_data[k] = None
                        else:
                            clean_data[k] = str(v)
                    
                    # Insert into database
                    cur.execute("""
                        INSERT INTO rtt_provider_raw 
                        (raw_data, period, provider_org_code, provider_org_name, 
                         treatment_function_code, treatment_function_name, rtt_part_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (period, provider_org_code, treatment_function_code, rtt_part_type) 
                        DO UPDATE SET 
                            raw_data = EXCLUDED.raw_data,
                            provider_org_name = EXCLUDED.provider_org_name,
                            treatment_function_name = EXCLUDED.treatment_function_name,
                            loaded_at = NOW()
                    """, [
                        json.dumps(clean_data),
                        period,
                        provider_org_code,
                        provider_org_name,
                        treatment_function_code,
                        treatment_function_name,
                        rtt_part_type
                    ])
                    
                    rows_inserted += 1
                    
                except Exception as e:
                    print(f"Warning: Failed to insert row: {e}")
                    continue
            
    print(f"✅ loaded {rows_inserted:,} rows into rtt_provider_raw")

def once():
    fetcher = _get_fetcher()
    url, df = fetcher.fetch()
    _load(df)
    print(f"✔ source={fetcher.name} url={url}")

def loop():
    interval = int(os.getenv("POLL_INTERVAL", 3600))
    while True:
        try:
            once()
        except Exception as e:
            print("‼", e)
        time.sleep(interval)

if __name__ == "__main__":
    import sys
    (loop if "--loop" in os.sys.argv else once)()
