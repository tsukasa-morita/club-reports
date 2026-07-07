# update_daily_full.py - ログ出力機能付き
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from fredapi import Fred
import pandas as pd
import numpy as np
import time
import os
from pathlib import Path

# ===== ログ出力クラス =====
class Logger:
    def __init__(self, base_dir):
        self.logs_dir = os.path.join(base_dir, 'logs')
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        self.start_time = datetime.now()
        self.log_file = os.path.join(self.logs_dir, f"update_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log")
        
    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def summary(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        summary_msg = f"\n実行時間: {elapsed:.1f}秒\nログファイル: {self.log_file}\n"
        print(summary_msg)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(summary_msg)

# ===== .env 読み込み（KEY=VALUE 形式のみ対応の最小実装） =====
def _load_env():
    env_path = Path(__file__).resolve().parent / '.env'
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

# ===== 絶対パス設定 =====
BASE_DIR = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'marketreportproject.json')
logger = Logger(BASE_DIR)

# ===== 今日すでに実行済みかチェック =====
LAST_RUN_FILE = os.path.join(BASE_DIR, 'last_run.txt')
_today = datetime.now().strftime('%Y-%m-%d')
_now = datetime.now()

logger.log(f"===== MarketData 日次更新開始 =====")
logger.log(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if _now.hour < 9:
    logger.log(f"実行時刻が09:00未満のためスキップ")
    logger.summary()
    exit(0)

if os.path.exists(LAST_RUN_FILE):
    with open(LAST_RUN_FILE, 'r') as f:
        if f.read().strip() == _today:
            logger.log(f"本日（{_today}）はすでに実行済みのためスキップします。")
            logger.summary()
            exit(0)

with open(LAST_RUN_FILE, 'w') as f:
    f.write(_today)

# ===== Google Sheets 認証 =====
try:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open('MarketData')
    logger.log("Google Sheets認証成功")
except Exception as e:
    logger.log(f"Google Sheets認証失敗: {e}")
    logger.summary()
    exit(1)

# ===== FRED API =====
fred = Fred(api_key=os.environ['FRED_API_KEY'])

# ===== 資産マップ =====
assets_map = {
    'Nikkei': '日本（日経平均）', 'SP500': 'アメリカ（S＆P500）', 'DAX': 'ドイツ（DAX）', 'Shanghai': '中国（上海総合）',
    'Bovespa': 'ブラジル（ボベスパ）', 'Sensex': 'インド（SENSEX）',
    'Food': '食品', 'Energy': 'エネルギー資源', 'Construction': '建設・資材', 'Materials': '素材・化学', 'Pharma': '医薬品',
    'Auto': '自動車・輸送機', 'Steel': '鉄鋼・非鉄', 'Machinery': '機械', 'Electronics': '電機・精密',
    'ITServices': '情報通信・サービス', 'ElectricGas': '電力・ガス', 'Transport': '運輸・物流', 'Trading': '商社・卸売',
    'Retail': '小売', 'Banks': '銀行', 'FinanceExBanks': '金融（除く銀行）', 'RealEstate': '不動産',
    'USDJPY': 'ドル円', 'EURJPY': 'ユーロ円', 'JGB10Y': '日本10年債', 'US10Y': '米国10年債',
    'Gold': '金', 'CrudeOil': '原油', 'BTC': 'ビットコイン', 'ETH': 'イーサリアム', 'VIX': 'VIX（恐怖指数）',
    'AdvanceDecline': '騰落レシオ', 'MarginRatio': '信用倍率'
}

ticker_map = {
    'Nikkei': '^N225', 'SP500': '^GSPC', 'DAX': '^GDAXI', 'Shanghai': '000001.SS', 'Bovespa': '^BVSP', 'Sensex': '^BSESN',
    'Food': '1617.T', 'Energy': '1618.T', 'Construction': '1619.T', 'Materials': '1620.T', 'Pharma': '1621.T',
    'Auto': '1622.T', 'Steel': '1623.T', 'Machinery': '1624.T', 'Electronics': '1625.T', 'ITServices': '1626.T',
    'ElectricGas': '1627.T', 'Transport': '1628.T', 'Trading': '1629.T', 'Retail': '1630.T', 'Banks': '1631.T',
    'FinanceExBanks': '1632.T', 'RealEstate': '1633.T',
    'USDJPY': 'JPY=X', 'EURJPY': 'EURJPY=X', 'US10Y': '^TNX', 'JGB10Y': '', 'Gold': 'GC=F', 'CrudeOil': 'CL=F',
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'VIX': '^VIX', 'AdvanceDecline': None, 'MarginRatio': None
}

# ===== 日本10年債取得（財務省CSV）=====
def get_jgb10y():
    import requests, io
    url = 'https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv'
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    content = res.content.decode('shift-jis', errors='ignore')
    df = pd.read_csv(io.StringIO(content), skiprows=1)
    df = df.dropna(subset=['基準日'])
    df = df[df['基準日'].str.match(r'R\d+\.\d+\.\d+')]
    df['Date'] = pd.to_datetime(df['基準日'].str.replace(r'R(\d+)\.(\d+)\.(\d+)', 
        lambda m: f"{2018 + int(m.group(1))}-{m.group(2)}-{m.group(3)}", regex=True))
    df = df[['Date', '10年']].rename(columns={'10年': 'Close'})
    return df

# ===== データ取得・追記 =====
def update_daily(key, sheet_name):
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        logger.log(f"❌ {sheet_name} が存在しません")
        return

    if ticker_map.get(key) is None and key != "JGB10Y":
        logger.log(f"⏭️  {sheet_name}: 手動入力が必要なデータのためスキップ")
        return
    
    try:
        if key == "JGB10Y":
            df = get_jgb10y()
        else:
            ticker = ticker_map[key]
            start = (datetime.today() - timedelta(days=10)).strftime('%Y-%m-%d')
            df = yf.download(ticker, start=start, interval="1d", progress=False)
            if df.empty:
                logger.log(f"⏭️  {sheet_name}: データなし")
                return
            df.reset_index(inplace=True)
            if key in ['USDJPY', 'EURJPY']:
                df = df[['Date', 'Open', 'High', 'Low', 'Close']]
            elif key in ['VIX', 'US10Y', 'JGB10Y', 'AdvanceDecline', 'MarginRatio']:
                df = df[['Date', 'Close']]
            else:
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.replace({np.nan: None})
        df = df.sort_values('Date', ascending=True)

        rows = []
        for r in df.values.tolist():
            row = ["" if v is None else float(v) if isinstance(v, (np.integer, np.floating)) else v for v in r]
            rows.append(row)

        existing_dates = sheet.col_values(1)
        new_rows = [r for r in rows if r[0] not in existing_dates]
        new_rows.reverse()  # 新しい日付が上に来るように逆順に

        if new_rows:
            sheet.insert_rows(new_rows, row=2)
            logger.log(f"✅ {sheet_name}: {len(new_rows)}件 追記完了")
        else:
            logger.log(f"⏭️  {sheet_name}: 新しいデータなし")

    except Exception as e:
        logger.log(f"❌ {sheet_name}: {str(e)}")

# ===== Fear & Greed Index取得 =====
def get_fear_and_greed():
    import requests
    today = datetime.today().strftime('%Y-%m-%d')
    month_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    url = f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{month_ago}/{today}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://edition.cnn.com/',
        'Origin': 'https://edition.cnn.com'
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            score = data['fear_and_greed']['score']
            rating = data['fear_and_greed']['rating']
            date = datetime.today().strftime('%Y-%m-%d')
            return [date, round(score, 2), rating]
    except Exception as e:
        logger.log(f"❌ Fear & Greed取得エラー: {e}")
    return None

# ===== メイン =====
def main():
    for key, sheet_name in assets_map.items():
        update_daily(key, sheet_name)
        time.sleep(1)
    
    fg_data = get_fear_and_greed()
    if fg_data:
        try:
            sheet = spreadsheet.worksheet('恐怖強欲指数')
            existing_dates = sheet.col_values(1)
            if fg_data[0] not in existing_dates:
                sheet.insert_rows([fg_data], row=2)
                logger.log(f"✅ 恐怖強欲指数: 1件 追記完了 ({fg_data[1]} - {fg_data[2]})")
            else:
                logger.log(f"⏭️  恐怖強欲指数: 新しいデータなし")
        except Exception as e:
            logger.log(f"❌ 恐怖強欲指数エラー: {e}")
    
    logger.log(f"===== 完了 =====")
    logger.summary()

if __name__ == "__main__":
    main()
