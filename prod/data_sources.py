#!/usr/bin/env python
"""Pluggable fetchers for various data sources."""
import os, re, io, datetime, zipfile, requests, pandas as pd
from typing import Tuple
from bs4 import BeautifulSoup

class BaseFetcher:
    name: str = "base"
    def fetch(self) -> Tuple[str, pd.DataFrame]:
        raise NotImplementedError

class nhs_fetcher(BaseFetcher):
    name = "nhs"
    CSV_PAT = re.compile(r"Full-CSV-data-file-[A-Za-z]{3}\d{2}\.zip", re.I)

    # ---------- helpers --------------------------------------------------
    def _page_links(self, url:str) -> list[str]:
        try:
            html = requests.get(url, timeout=20, headers={"User-Agent":"Mozilla"}).text
            soup = BeautifulSoup(html, "html.parser")
            return [a.get("href") for a in soup.select("a[href]") if a.get("href")] or []
        except Exception:
            return []

    def _guess_urls(self, months:int=24) -> list[str]:
        base = "https://www.england.nhs.uk/statistics/wp-content/uploads"
        today = datetime.date.today().replace(day=1)
        urls=[]
        for back in range(months):
            data_month = today - datetime.timedelta(days=back*30)
            mon = data_month.strftime("%b%y")  # e.g. Mar25
            fname = f"Full-CSV-data-file-{mon}.zip"
            pub = data_month + datetime.timedelta(days=61)  # ≈ +2 months
            folder = f"{pub.year}/{pub.strftime('%m')}"
            urls.append(f"{base}/{folder}/{fname}")
        return urls

    # ---------- discovery logic -----------------------------------------
    def _discover(self) -> list[str]:
        root = "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/"
        pages=[root]
        y=datetime.date.today().year
        for yr in range(y, y-5, -1):
            pages.append(f"{root}rtt-data-{yr}-{str(yr+1)[-2:]}/")

        # 1) requests html
        links=[]
        for p in pages:
            links += self._page_links(p)
        cand=[l for l in links if l and self.CSV_PAT.search(l)]
        if cand:
            return sorted(set(cand), reverse=True)

        # 2) playwright fallback
        try:
            from playwright.sync_api import sync_playwright
            for p in pages:
                with sync_playwright() as pw:
                    page = pw.chromium.launch(headless=True).new_page()
                    page.goto(p, wait_until="networkidle")
                    html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                cand += [a.get("href") for a in soup.select("a[href]") if a.get("href") and self.CSV_PAT.search(a.get("href"))]
            if cand:
                return sorted(set(cand), reverse=True)
        except ImportError:
            pass

        # 3) guess pattern
        for u in self._guess_urls():
            try:
                if requests.head(u, timeout=10).status_code == 200:
                    return [u]
            except Exception:
                continue
        return []

    # ---------- public API ----------------------------------------------
    def _load_zip_csv(self, buf:bytes) -> pd.DataFrame:
        with zipfile.ZipFile(io.BytesIO(buf)) as zf:
            names=[n for n in zf.namelist() if n.lower().endswith('.csv') and 'provider' in n.lower()]
            target = names[0] if names else zf.namelist()[0]
            with zf.open(target) as f:
                return pd.read_csv(f)

    def fetch(self) -> Tuple[str, pd.DataFrame]:
        url = os.getenv("NHS_CSV_URL")
        if not url:
            found = self._discover()
            if not found:
                raise RuntimeError("Provider CSV link not found – set NHS_CSV_URL manually.")
            url = found[0]
        buf = requests.get(url, timeout=120).content
        df = self._load_zip_csv(buf) if url.lower().endswith('.zip') else pd.read_csv(io.BytesIO(buf))
        return url, df
