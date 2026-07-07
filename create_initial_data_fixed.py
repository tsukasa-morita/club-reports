# create_initial_data.py - 新しい列構成対応版
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from fredapi import Fred
import pandas as pd
import numpy as np
import time
import os

# ===== .env 読み込み（KEY=VALUE 形式のみ対応の最小実装） =====
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())

_load_env()

# ===== 認証 =====
BASE_DIR = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'marketreportproject.json')
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

# ===== FRED =====
fred = Fred(api_key=os.environ['FRED_API_KEY'])

# ===== 資産マップ =====
assets_map = {
    'Nikkei': '日本（日経平均）', 'SP500': 'アメリカ（S＆P500）', 'DAX': 'ドイツ（DAX）', 
    'Shanghai': '中国（上海総合）', 'Bovespa': 'ブラジル（ボベスパ）', 'Sensex': 'インド（SENSEX）',
    'Food': '食品', 'Energy': 'エネルギー資源', 'Construction': '建設・資材', 'Materials': '素材・化学', 
    'Pharma': '医薬品', 'Auto': '自動車・輸送機', 'Steel': '鉄鋼・非鉄', 'Machinery': '機械', 
    'Electronics': '電機・精密', 'ITServices': '情報通信・サービス', 'ElectricGas': '電力・ガス', 
    'Transport': '運輸・物流', 'Trading': '商社・卸売', 'Retail': '小売', 'Banks': '銀行', 
    'FinanceExBanks': '金融（除く銀行）', 'RealEstate': '不動産',
    'USDJPY': 'ドル円', 'EURJPY': 'ユーロ円', 'JGB10Y': '日本10年債', 'US10Y': '米国10年債',
    'Gold': '金', 'CrudeOil': '原油', 'BTC': 'ビットコイン', 'ETH': 'イーサリアム', 'VIX': 'VIX（恐怖指数）'
}

ticker_map = {
    'Nikkei': '^N225', 'SP500': '^GSPC', 'DAX': '^GDAXI', 'Shanghai': '000001.SS', 'Bovespa': '^BVSP', 'Sensex': '^BSESN',
    'Food': '1617.T', 'Energy': '1618.T', 'Construction': '1619.T', 'Materials': '1620.T', 'Pharma': '1621.T',
    'Auto': '1622.T', 'Steel': '1623.T', 'Machinery': '1624.T', 'Electronics': '1625.T', 'ITServices': '1626.T',
    'ElectricGas': '1627.T', 'Transport': '1628.T', 'Trading': '1629.T', 'Retail': '1630.T', 'Banks': '1631.T',
    'FinanceExBanks': '1632.T', 'RealEstate': '1633.T',
    'USDJPY': 'JPY=X', 'EURJPY': 'EURJPY=X', 'US10Y': '^TNX', 'JGB10Y': None,
    'Gold': 'GC=F', 'CrudeOil': 'CL=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'VIX': '^VIX'
}

# ===== データ種別 =====
OHLC_ASSETS = [
    'Nikkei', 'SP500', 'DAX', 'Shanghai', 'Bovespa', 'Sensex',
    'Food', 'Energy', 'Construction', 'Materials', 'Pharma', 'Auto', 'Steel', 'Machinery', 'Electronics',
    'ITServices', 'ElectricGas', 'Transport', 'Trading', 'Retail', 'Banks', 'FinanceExBanks', 'RealEstate',
    'USDJPY', 'EURJPY', 'Gold', 'CrudeOil', 'BTC', 'ETH'
]
SINGLE_VALUE_ASSETS = ['JGB10Y', 'US10Y', 'VIX']

# ===== 日本10年債 =====
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

# ===== OHLC系初期データ作成 =====
def create_ohlc_data(key, sheet_name):
    print(f"📊 {sheet_name} 初期データ作成中...")
    
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.clear()
    except:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=5000, cols=10)
    
    # ヘッダー設定
    header = ['日付', '終値', '前日比', '前日比（%）', '始値', '高値', '安値']
    sheet.update('A1:G1', [header])
    time.sleep(1)
    
    # データ取得（10年分）
    ticker = ticker_map[key]
    start = (datetime.today() - timedelta(days=3650)).strftime('%Y-%m-%d')
    df = yf.download(ticker, start=start, interval="1d", progress=False)
    
    if df.empty:
        print(f"  ⏭️ データなし")
        return
    
    df.reset_index(inplace=True)
    df = df[['Date', 'Open', 'High', 'Low', 'Close']]
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df.replace({np.nan: None})
    df = df.sort_values('Date', ascending=True)  # 古い順
    
    # 前日比計算しながら行作成
    rows = []
    prev_close = None
    
    for r in df.values.tolist():
        date_val = r[0]
        open_val = float(r[1]) if r[1] is not None else None
        high_val = float(r[2]) if r[2] is not None else None
        low_val = float(r[3]) if r[3] is not None else None
        close_val = float(r[4]) if r[4] is not None else None
        
        # 前日比計算
        change = None
        change_pct = None
        if close_val is not None and prev_close is not None:
            change = round(close_val - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)
        
        # 行作成: ['日付', '終値', '前日比', '前日比（%）', '始値', '高値', '安値']
        row = [
            date_val,
            round(close_val, 2) if close_val is not None else "",
            change if change is not None else "",
            change_pct if change_pct is not None else "",
            round(open_val, 2) if open_val is not None else "",
            round(high_val, 2) if high_val is not None else "",
            round(low_val, 2) if low_val is not None else ""
        ]
        rows.append(row)
        
        if close_val is not None:
            prev_close = close_val
    
    # 新しい順に並び替え
    rows.reverse()
    
    # 100行ずつ書き込み
    chunk_size = 100
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        sheet.append_rows(chunk)
        print(f"  ✅ {i+len(chunk)}/{len(rows)}件")
        time.sleep(2)
    
    print(f"  🎉 完了: {len(rows)}件")

# ===== 単一値系初期データ作成 =====
def create_single_value_data(key, sheet_name):
    print(f"📊 {sheet_name} 初期データ作成中...")
    
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.clear()
    except:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=5000, cols=10)
    
    # ヘッダー設定
    header = ['日付', '値']
    sheet.update('A1:B1', [header])
    time.sleep(1)
    
    # データ取得
    if key == 'JGB10Y':
        df = get_jgb10y()
    else:
        ticker = ticker_map[key]
        start = (datetime.today() - timedelta(days=3650)).strftime('%Y-%m-%d')
        df = yf.download(ticker, start=start, interval="1d", progress=False)
        if df.empty:
            print(f"  ⏭️ データなし")
            return
        df.reset_index(inplace=True)
        df = df[['Date', 'Close']]
    
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df.replace({np.nan: None})
    df = df.sort_values('Date', ascending=True)  # 古い順
    
    # 行作成
    rows = []
    for r in df.values.tolist():
        date_val = r[0]
        value = float(r[1]) if r[1] is not None else None
        row = [
            date_val,
            round(value, 2) if value is not None else ""
        ]
        rows.append(row)
    
    # 新しい順に並び替え
    rows.reverse()
    
    # 100行ずつ書き込み
    chunk_size = 100
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        sheet.append_rows(chunk)
        print(f"  ✅ {i+len(chunk)}/{len(rows)}件")
        time.sleep(2)
    
    print(f"  🎉 完了: {len(rows)}件")

# ===== メイン =====
def main():
    print("=" * 60)
    print("初期データ作成開始（10年分）")
    print("=" * 60)
    
    # OHLC系
    for key in OHLC_ASSETS:
        sheet_name = assets_map[key]
        create_ohlc_data(key, sheet_name)
    
    # 単一値系
    for key in SINGLE_VALUE_ASSETS:
        sheet_name = assets_map[key]
        create_single_value_data(key, sheet_name)
    
    print("=" * 60)
    print("🎉 全データ作成完了！")
    print("=" * 60)

if __name__ == "__main__":
    main()
