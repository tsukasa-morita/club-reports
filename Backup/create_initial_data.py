# create_initial_data_safe.py
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
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
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
SERVICE_ACCOUNT_FILE = './credentials/marketreportproject.json'
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
    # 株価指数
    'Nikkei': '日本（日経平均）',
    'SP500': 'アメリカ（S＆P500）',
    'DAX': 'ドイツ（DAX）',
    'Shanghai': '中国（上海総合）',
    'Bovespa': 'ブラジル（ボベスパ）',
    'Sensex': 'インド（SENSEX）',
    # 業種（TOPIX17）
    'Food': '食品',
    'Energy': 'エネルギー資源',
    'Construction': '建設・資材',
    'Materials': '素材・化学',
    'Pharma': '医薬品',
    'Auto': '自動車・輸送機',
    'Steel': '鉄鋼・非鉄',
    'Machinery': '機械',
    'Electronics': '電機・精密',
    'ITServices': '情報通信・サービス',
    'ElectricGas': '電力・ガス',
    'Transport': '運輸・物流',
    'Trading': '商社・卸売',
    'Retail': '小売',
    'Banks': '銀行',
    'FinanceExBanks': '金融（除く銀行）',
    'RealEstate': '不動産',
    # 為替
    'USDJPY': 'ドル円',
    'EURJPY': 'ユーロ円',
    # 金利
    'JGB10Y': '日本10年債',
    'US10Y': '米国10年債',
    # コモディティ
    'Gold': '金',
    'CrudeOil': '原油',
    # 暗号資産
    'BTC': 'ビットコイン',
    'ETH': 'イーサリアム',
    # その他
    'VIX': 'VIX（恐怖指数）'
}

# ===== Ticker マップ =====
ticker_map = {
    'Nikkei': '^N225',
    'SP500': '^GSPC',
    'DAX': '^GDAXI',
    'Shanghai': '000001.SS',
    'Bovespa': '^BVSP',
    'Sensex': '^BSESN',
    'Food': '1617.T',
    'Energy': '1618.T',
    'Construction': '1619.T',
    'Materials': '1620.T',
    'Pharma': '1621.T',
    'Auto': '1622.T',
    'Steel': '1623.T',
    'Machinery': '1624.T',
    'Electronics': '1625.T',
    'ITServices': '1626.T',
    'ElectricGas': '1627.T',
    'Transport': '1628.T',
    'Trading': '1629.T',
    'Retail': '1630.T',
    'Banks': '1631.T',
    'FinanceExBanks': '1632.T',
    'RealEstate': '1633.T',
    'USDJPY': 'JPY=X',
    'EURJPY': 'EURJPY=X',
    'US10Y': '^TNX',
    'JGB10Y': None,  # FRED
    'Gold': 'GC=F',
    'CrudeOil': 'CL=F',
    'BTC': 'BTC-USD',
    'ETH': 'ETH-USD',
    'VIX': '^VIX'
}

# ===== カラム定義 =====
ohlcv = ['日付', '始値', '高値', '安値', '終値', '出来高']
ohlc = ['日付', '始値', '高値', '安値', '終値']
single = ['日付', '値']

columns_map = {}
for key in assets_map:
    if key in ['USDJPY', 'EURJPY']:
        columns_map[key] = ohlc
    elif key in ['VIX', 'US10Y', 'JGB10Y']:
        columns_map[key] = single
    else:
        columns_map[key] = ohlcv

# ===== 日本10年債 =====
def get_jgb10y():
    data = fred.get_series('IRLTLT01JPM156N')
    df = data.to_frame(name='Close')
    df.reset_index(inplace=True)
    df.columns = ['Date', 'Close']
    return df

# ===== データ取得・書き込み =====
def create_initial_data(key, sheet_name):
    print(f"初期データ取得: {sheet_name}")

    # シート取得
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows="5000", cols="20")
        sheet.append_row(columns_map[key])
        time.sleep(1)

    # データ取得
    if key == 'JGB10Y':
        df = get_jgb10y()
    else:
        ticker = ticker_map[key]
        start = (datetime.today() - timedelta(days=3650)).strftime('%Y-%m-%d')
        df = yf.download(ticker, start=start, interval="1d")
        if df.empty:
            print("データなし")
            return
        df.reset_index(inplace=True)
        if key in ['USDJPY', 'EURJPY']:
            df = df[['Date', 'Open', 'High', 'Low', 'Close']]
        elif key in ['VIX', 'US10Y']:
            df = df[['Date', 'Close']]
        else:
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

    # 整形
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df = df.replace({np.nan: None})
    df = df.sort_values('Date', ascending=False)

    # list化
    rows = []
    for r in df.values.tolist():
        row = ["" if v is None else float(v) if isinstance(v, (np.integer, np.floating)) else v for v in r]
        rows.append(row)

    # ヘッダー
    header = columns_map[key]
    sheet.clear()
    sheet.append_row(header)
    time.sleep(1)

    # 50行ずつ分割して書き込み
    chunk_size = 50
    for i in range(0, len(rows), chunk_size):
        sheet.append_rows(rows[i:i+chunk_size])
        time.sleep(1)

    print(f"{len(rows)}件 完了")

# ===== メイン =====
def main():
    for key, sheet_name in assets_map.items():
        create_initial_data(key, sheet_name)

if __name__ == "__main__":
    main()