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
    def _page_links(self, url: str) -> list[str]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            html = requests.get(url, timeout=30, headers=headers).text
            soup = BeautifulSoup(html, "html.parser")
            return [a.get("href") for a in soup.select("a[href]") if a.get("href")] or []
        except Exception:
            return []

    def _extract_download_links(self, html: str) -> list[str]:
        """Extract direct download links from page HTML"""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        # Method 1: Look for direct zip file links
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            text = a.get_text().strip().lower()
            if href and (href.endswith(".zip") or "csv" in text.lower()):
                if "full" in text and "csv" in text:
                    links.append(href)
        
        # Method 2: Look for download buttons/links with specific patterns
        download_patterns = [
            r"Full CSV data file \w+\d+",
            r"full-csv-data-file-\w+\d+",
            r"Download.*CSV.*file"
        ]
        
        for pattern in download_patterns:
            for element in soup.find_all(string=re.compile(pattern, re.I)):
                parent = element.parent
                while parent and parent.name != "a":
                    parent = parent.parent
                if parent and parent.get("href"):
                    links.append(parent.get("href"))
        
        return list(set(links))

    def _smart_url_construction(self) -> list[str]:
        """Intelligent URL construction based on current date and known patterns"""
        base_patterns = [
            "https://www.england.nhs.uk/statistics/wp-content/uploads/{year}/{month:02d}/Full-CSV-data-file-{mon_year}.zip",
            "https://www.england.nhs.uk/statistics/wp-content/uploads/{year}/{month:02d}/full-csv-data-file-{mon_year}.zip",
            "https://digital.nhs.uk/media/{id}/Full-CSV-data-file-{mon_year}.zip"
        ]
        
        urls = []
        today = datetime.date.today()
        
        # Try last 12 months with various publication delay assumptions
        for months_back in range(0, 12):
            data_date = today.replace(day=1) - datetime.timedelta(days=months_back * 30)
            
            # NHS usually publishes 2-3 months after data period
            for pub_delay in [60, 75, 90, 105]:  # 2-3.5 months
                pub_date = data_date + datetime.timedelta(days=pub_delay)
                mon_year = data_date.strftime("%b%y")  # Mar25
                
                for pattern in base_patterns:
                    try:
                        url = pattern.format(
                            year=pub_date.year,
                            month=pub_date.month,
                            mon_year=mon_year
                        )
                        urls.append(url)
                    except:
                        continue
        
        return urls

    def _playwright_enhanced_discovery(self) -> list[str]:
        """Enhanced Playwright discovery with better error handling and retry logic"""
        try:
            from playwright.sync_api import sync_playwright
            
            pages_to_check = [
                "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2024-25/",
                "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2023-24/",
                "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/"
            ]
            
            found_urls = []
            
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                for page_url in pages_to_check:
                    try:
                        page = context.new_page()
                        page.goto(page_url, wait_until="networkidle", timeout=30000)
                        
                        # Wait for any dynamic content
                        page.wait_for_timeout(2000)
                        
                        # Extract all links
                        links = page.evaluate("""
                            () => {
                                const links = [];
                                document.querySelectorAll('a[href]').forEach(link => {
                                    const text = link.textContent.toLowerCase();
                                    const href = link.href;
                                    if ((text.includes('full') && text.includes('csv')) || 
                                        href.includes('full-csv-data-file') ||
                                        href.endsWith('.zip')) {
                                        links.push(href);
                                    }
                                });
                                return links;
                            }
                        """)
                        
                        found_urls.extend(links)
                        page.close()
                        
                    except Exception as e:
                        print(f"Playwright error for {page_url}: {e}")
                        continue
                
                browser.close()
            
            # Filter and sort by likely relevance
            csv_links = [url for url in found_urls if self.CSV_PAT.search(url)]
            return sorted(set(csv_links), reverse=True)
            
        except ImportError:
            print("Playwright not available, skipping browser-based discovery")
            return []
        except Exception as e:
            print(f"Playwright discovery failed: {e}")
            return []

    def _validate_and_rank_urls(self, urls: list[str]) -> list[str]:
        """Validate URLs and rank them by freshness and reliability"""
        valid_urls = []
        
        for url in urls:
            try:
                response = requests.head(url, timeout=15, allow_redirects=True)
                if response.status_code == 200:
                    # Extract date from URL for ranking
                    date_match = re.search(r"([A-Za-z]{3})(\d{2})", url)
                    if date_match:
                        mon_str, year_str = date_match.groups()
                        try:
                            # Convert to comparable format
                            month_num = datetime.datetime.strptime(mon_str, "%b").month
                            year_full = 2000 + int(year_str)
                            date_score = year_full * 100 + month_num
                            valid_urls.append((url, date_score))
                        except:
                            valid_urls.append((url, 0))
                    else:
                        valid_urls.append((url, 0))
            except Exception:
                continue
        
        # Sort by date score (newest first)
        valid_urls.sort(key=lambda x: x[1], reverse=True)
        return [url for url, _ in valid_urls]

    # ---------- enhanced discovery logic ---------------------------------
    def _discover(self) -> list[str]:
        """Enhanced multi-strategy discovery with fallbacks and validation"""
        print("🔍 Starting NHS data discovery...")
        all_candidates = []
        
        # Strategy 1: Enhanced HTML parsing
        print("📄 Strategy 1: Enhanced HTML parsing...")
        root_pages = [
            "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/",
            "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2024-25/",
            "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2023-24/"
        ]
        
        for page_url in root_pages:
            try:
                html = requests.get(page_url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }).text
                links = self._extract_download_links(html)
                all_candidates.extend(links)
                print(f"  Found {len(links)} candidates from {page_url}")
            except Exception as e:
                print(f"  Failed to parse {page_url}: {e}")
        
        # Strategy 2: Playwright enhanced discovery
        print("🎭 Strategy 2: Playwright enhanced discovery...")
        playwright_links = self._playwright_enhanced_discovery()
        all_candidates.extend(playwright_links)
        print(f"  Found {len(playwright_links)} candidates via Playwright")
        
        # Strategy 3: Smart URL construction
        print("🧠 Strategy 3: Smart URL construction...")
        smart_urls = self._smart_url_construction()
        all_candidates.extend(smart_urls)
        print(f"  Generated {len(smart_urls)} candidate URLs")
        
        # Remove duplicates and convert relative URLs to absolute
        unique_candidates = []
        for url in set(all_candidates):
            if url.startswith("/"):
                url = "https://www.england.nhs.uk" + url
            elif not url.startswith("http"):
                url = "https://www.england.nhs.uk/" + url.lstrip("/")
            unique_candidates.append(url)
        
        print(f"🔗 Total unique candidates: {len(unique_candidates)}")
        
        # Strategy 4: Validate and rank URLs
        print("✅ Strategy 4: Validating and ranking URLs...")
        valid_urls = self._validate_and_rank_urls(unique_candidates)
        
        print(f"🎯 Found {len(valid_urls)} valid URLs")
        for i, url in enumerate(valid_urls[:5]):  # Show top 5
            print(f"  {i+1}. {url}")
        
        return valid_urls

    # ---------- public API ----------------------------------------------
    def _load_zip_csv(self, buf:bytes) -> pd.DataFrame:
        with zipfile.ZipFile(io.BytesIO(buf)) as zf:
            # Look for any CSV file, preferring ones with 'provider' or 'extract' in name
            csv_files = [n for n in zf.namelist() if n.lower().endswith('.csv')]
            if not csv_files:
                raise RuntimeError("No CSV files found in ZIP archive")
            
            # Priority order: provider -> extract -> any CSV
            target = None
            for priority_keyword in ['provider', 'extract', 'rtt']:
                for name in csv_files:
                    if priority_keyword in name.lower():
                        target = name
                        break
                if target:
                    break
            
            if not target:
                target = csv_files[0]  # Use first CSV file
            
            print(f"🗂️ Using CSV file: {target}")
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
