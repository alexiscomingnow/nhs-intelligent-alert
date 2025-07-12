#!/usr/bin/env python
"""Generic ETL runner – pluggable data sources → Postgres."""
import os, time, importlib, pandas as pd, psycopg

def _get_fetcher():
    """Instantiate fetcher based on DATA_SOURCE env (default: nhs)."""
    name = os.getenv("DATA_SOURCE", "nhs")
    mod = importlib.import_module("data_sources")
    try:
        return getattr(mod, f"{name}_fetcher")()
    except AttributeError:
        raise RuntimeError(f"Unknown DATA_SOURCE: {name}")

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    if "period" in df.columns:
        df["period"] = pd.to_datetime(df["period"], dayfirst=True, errors='coerce').dt.date
    return df

def _load(df: pd.DataFrame):
    df = _normalize(df)
    with psycopg.connect(os.getenv("PG_CONN"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE _tmp AS TABLE rtt_provider_raw WITH NO DATA;")
        df.to_sql("_tmp", con=conn, index=False, if_exists="append", method="multi")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rtt_provider_raw SELECT * FROM _tmp
                ON CONFLICT DO NOTHING;
            """)
    print(f"✅ loaded {len(df):,} rows into rtt_provider_raw")

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
