\
    #!/usr/bin/env python
    """NHS RTT provider-level ETL → Postgres (native)."""
    import os, re, io, time, requests, pandas as pd, psycopg

    CSV_PAT = re.compile(r"https://[^\"']+/(?P<y>\d{4})/(?P<m>\d{2})/[^\"']+RTT-Provider\.csv", re.I)
    HOME    = "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/"

    # ---------- 1. discover CSV link ---------------------------------
    def _static_links() -> list[str]:
        r = requests.get(HOME, timeout=15); r.raise_for_status()
        return CSV_PAT.findall(r.text) or []

    def _dynamic_links() -> list[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return []
        with sync_playwright() as pw:
            page = pw.chromium.launch(headless=True).new_page()
            page.goto(HOME, wait_until="domcontentloaded")
            links = [a.get_attribute("href") for a in page.query_selector_all("a[href$='RTT-Provider.csv']")]
        return [l for l in links if l]

    def latest_url() -> str:
        if os.getenv("NHS_CSV_URL"):
            return os.getenv("NHS_CSV_URL")
        links = sorted({*_static_links(), *_dynamic_links()}, reverse=True)
        if not links:
            raise RuntimeError("Provider CSV link not found – set NHS_CSV_URL manually.")
        return links[0]

    # ---------- 2. load into Postgres --------------------------------
    def load(url: str) -> None:
        buf = requests.get(url, timeout=60).content
        df  = pd.read_csv(io.BytesIO(buf))
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        df["period"] = pd.to_datetime(df["period"], dayfirst=True).dt.date

        with psycopg.connect(os.getenv("PG_CONN"), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TEMP TABLE _tmp AS TABLE rtt_provider_raw WITH NO DATA;")
            df.to_sql("_tmp", con=conn, index=False, if_exists="append", method="multi")
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO rtt_provider_raw SELECT * FROM _tmp
                    ON CONFLICT DO NOTHING;
                """)
        print(f"✅ loaded {len(df):,} rows from {url}")

    # ---------- 3. entry ---------------------------------------------
    def once(): load(latest_url())

    def loop():
        while True:
            try: once()
            except Exception as e: print("‼", e)
            time.sleep(3600)

    if __name__ == "__main__":
        (loop if "--loop" in os.sys.argv else once)()
