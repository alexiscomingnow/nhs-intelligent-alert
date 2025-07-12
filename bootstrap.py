#!/usr/bin/env python
"""
bootstrap.py – one-stop generator for the NHS RTT provider ETL (native, no Docker).

功能:
  1. 在 --path 指定的目录写入全部项目文件:
       • requirements.txt        Python 依赖
       • env.example             环境模板
       • create_db.sql           PostgreSQL DDL
       • runner.py               核心 ETL
       • start_grafana.ps1       启动脚本
       • run_etl_once.ps1        手动跑一次
       • schedule_etl.ps1        注册计划任务 (Windows)
  2. 如未加 --no-venv，则自动创建 .venv 并 pip install，
     且下载 Playwright 浏览器 (≈ 300 MB，首次时间稍久)。
  3. 打印后续操作指引。

仅需本机已安装:
  • Python 3.11+
  • PostgreSQL 16+
  • Grafana 11 (可选但推荐)
"""

from __future__ import annotations
import os, sys, argparse, textwrap, subprocess, platform, venv
import urllib.parse, shlex
import pathlib

# ---------- 1. 需写入的文件 --------------------------------------------------

FILES: dict[str, str] = {
# ───────────────────────── requirements.txt ──────────────────────────
"requirements.txt": textwrap.dedent("""\
    playwright==1.53.0
    pandas==2.2.2
    psycopg[binary]==3.1.19
    requests==2.32.3
    beautifulsoup4==4.12.3
"""),

# ───────────────────────── env.example ───────────────────────────────
"env.example": textwrap.dedent("""\
    # 复制为 .env 并根据实际修改
    PG_CONN=postgresql://postgres:postgres@localhost:5432/nhs
    # 数据源标识，默认为 nhs，可扩展为其它 fetcher 名称
    DATA_SOURCE=nhs
    # 抓取间隔（秒），--loop 模式下使用；默认 3600 (1h)
    POLL_INTERVAL=3600
    # 若自动抓取失败，可直接指定 CSV 链接（仅 NHS 数据源使用）：
    #NHS_CSV_URL=https://www.england.nhs.uk/statistics/wp-content/uploads/...
"""),

# ───────────────────────── create_db.sql ─────────────────────────────
"create_db.sql": textwrap.dedent("""\
    CREATE DATABASE nhs;
    \\c nhs
    CREATE TABLE IF NOT EXISTS rtt_provider_raw(
        provider_code          text,
        provider_name          text,
        specialty_code         text,
        specialty              text,
        period                 date,
        waiting_less_18_weeks  int,
        waiting_over_52_weeks  int,
        PRIMARY KEY(provider_code, specialty_code, period)
    );
"""),

# ───────────────────────── runner.py (核心 ETL) ──────────────────────
"runner.py": textwrap.dedent(r'''#!/usr/bin/env python
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
'''),

# ───────────────────────── start_grafana.ps1 ─────────────────────────
"start_grafana.ps1": textwrap.dedent("""\
    Start-Process -FilePath "C:\\Program Files\\GrafanaLabs\\grafana\\bin\\grafana-server.exe"
"""),

# ───────────────────────── run_etl_once.ps1 ──────────────────────────
"run_etl_once.ps1": textwrap.dedent("""\
    $here = Split-Path $MyInvocation.MyCommand.Path
    . "$here\\.venv\\Scripts\\Activate.ps1"
    python "$here\\runner.py"
"""),

# ───────────────────────── schedule_etl.ps1 ──────────────────────────
"schedule_etl.ps1": textwrap.dedent("""\
    $here     = Split-Path $MyInvocation.MyCommand.Path
    $py       = "$here\\.venv\\Scripts\\python.exe"
    $action   = New-ScheduledTaskAction -Execute $py -Argument "$here\\runner.py"
    $trigger  = New-ScheduledTaskTrigger -Daily -At 03:00
    Register-ScheduledTask -TaskName "NHS_ETL_Daily" -Action $action -Trigger $trigger `
        -Description "Daily NHS RTT provider ETL" -User $env:USERNAME -RunLevel Highest -Force
"""),

# ───────────────────────── data_sources.py ──────────────────────────
"data_sources.py": textwrap.dedent(r'''#!/usr/bin/env python
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
'''),

# ───────────────────────── config.example ──────────────────────────
"config.example": textwrap.dedent("""\
    # rename to config.env and edit values before running bootstrap
    PG_CONN=postgresql://postgres:postgres@localhost:5432/nhs
    DATA_SOURCE=nhs
    POLL_INTERVAL=3600
    #NHS_CSV_URL=https://www.england.nhs.uk/...zip
"""),
}

# ---------- 2. helpers --------------------------------------------------------

def banner(msg: str): print(f"\n\033[96m=== {msg} ===\033[0m")

def write_files(root: str):
    os.makedirs(root, exist_ok=True)
    for name, text in FILES.items():
        p = os.path.join(root, name)
        with open(p, "w", encoding="utf-8") as f: f.write(text.lstrip())
    print(f"✓ wrote {len(FILES)} files to {root}")

def create_venv(root: str):
    banner("creating virtualenv (.venv)")
    venv_dir = os.path.join(root, ".venv")
    if os.path.isdir(venv_dir):
        print("• virtualenv already exists – ensuring requirements up to date")
    else:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    pip = os.path.join(venv_dir, "Scripts" if platform.system()=="Windows" else "bin", "pip")
    # 安装 / 更新 requirements
    subprocess.check_call([pip, "install", "--upgrade", "-r", os.path.join(root, "requirements.txt")])
    # playwright 浏览器
    python = os.path.join(venv_dir, "Scripts" if platform.system()=="Windows" else "bin", "python")
    subprocess.check_call([python, "-m", "playwright", "install", "--with-deps"])
    print("✓ venv ready ->", venv_dir)

def init_db(root:str):
    dsn=os.getenv("PG_CONN")
    if not dsn:
        print("⚠️  PG_CONN not set – skip DB init"); return
    url=urllib.parse.urlparse(dsn)
    user=url.username or "postgres"
    host=url.hostname or "localhost"
    db   =(url.path or "/nhs").lstrip("/")
    psql = "psql"
    sql_file=os.path.join(root,"create_db.sql")
    print(f"⏳ initialising database {db} …")
    try:
        env=os.environ.copy(); env["PGCLIENTENCODING"]="utf8"
        subprocess.check_call([psql,"-U",user,"-h",host,"-f",sql_file], env=env)
        print("✓ database ready")
    except FileNotFoundError:
        print("‼ psql not found – please ensure PostgreSQL client in PATH")
    except subprocess.CalledProcessError as e:
        print("‼ psql execution failed",e)


def run_once(root:str):
    py=os.path.join(root,".venv","Scripts" if platform.system()=="Windows" else "bin","python")
    runner=os.path.join(root,"runner.py")
    print("⏳ running initial ETL (single pass)…")
    subprocess.call([py, runner])

def load_conf(root:str, conf_path:str|None=None):
    path = conf_path or os.path.join(root, "config.env")
    if not os.path.isfile(path):
        print(f"• config file {path} not found, using process env")
        return
    print(f"✓ loading config from {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k,v=line.split('=',1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="目标目录 (生成项目文件)")
    ap.add_argument("--no-venv", action="store_true", help="只写文件，不创建虚拟环境")
    ap.add_argument("--conf", help="自定义配置文件路径 (key=value) 格式", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    write_files(root)
    load_conf(root, args.conf)
    if not args.no_venv: create_venv(root)
    init_db(root)
    run_once(root)

    banner("NEXT STEPS")
    print(textwrap.dedent(f"""
        ✓ Ready. 如需：
          • 连续运行:  python runner.py --loop
          • 注册计划任务(Win): .\\schedule_etl.ps1
          • Grafana:            .\\start_grafana.ps1 → http://localhost:3000 (admin/admin)
    """))

# ---------- 3. entry ----------------------------------------------------------
if __name__ == "__main__":
    main()
