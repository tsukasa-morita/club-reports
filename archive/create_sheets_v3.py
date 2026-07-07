import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# ===== 認証 =====
SERVICE_ACCOUNT_FILE = './credentials/marketreportproject.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

# ===== 資産マップ =====
assets_map = {
    'Nikkei': '日本（日経平均）',
    'SP500': 'アメリカ（S＆P500）',
    'DAX': 'ドイツ（DAX）',
    'Shanghai': '中国（上海総合）',
    'Bovespa': 'ブラジル（ボベスパ）',
    'Sensex': 'インド（SENSEX）',
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
    'USDJPY': 'ドル円',
    'EURJPY': 'ユーロ円',
    'JGB10Y': '日本10年債',
    'US10Y': '米国10年債',
    'Gold': '金',
    'CrudeOil': '原油',
    'BTC': 'ビットコイン',
    'ETH': 'イーサリアム',
    'VIX': 'VIX（恐怖指数）',
    'AdvanceDecline': '騰落レシオ',
    'MarginRatio': '信用倍率'
}

# ===== 新しいカラム定義 =====
ohlc_with_change = ['日付', '終値', '前日比', '始値', '高値', '安値']
single = ['日付', '値']

columns_map = {}
for key in assets_map:
    if key in ['USDJPY', 'EURJPY', 'Nikkei', 'SP500', 'DAX', 'Shanghai', 'Bovespa', 'Sensex',
               'Food', 'Energy', 'Construction', 'Materials', 'Pharma', 'Auto', 'Steel', 
               'Machinery', 'Electronics', 'ITServices', 'ElectricGas', 'Transport', 'Trading',
               'Retail', 'Banks', 'FinanceExBanks', 'RealEstate', 'Gold', 'CrudeOil', 'BTC', 'ETH']:
        columns_map[key] = ohlc_with_change
    else:
        columns_map[key] = single

# ===== 既存シートを全削除 =====
print("既存シートを削除中...")
worksheets = spreadsheet.worksheets()
for ws in worksheets:
    if ws.title in assets_map.values():
        try:
            spreadsheet.del_worksheet(ws)
            print(f"削除: {ws.title}")
            time.sleep(0.5)
        except Exception as e:
            print(f"削除失敗: {ws.title}", e)

# ===== 新しいシートを作成 =====
print("\n新しいシートを作成中...")
for key, sheet_name in assets_map.items():
    sheet = spreadsheet.add_worksheet(title=sheet_name, rows="5000", cols="10")
    sheet.append_row(columns_map[key])
    sheet.format("1:1", {
        "horizontalAlignment": "CENTER",
        "textFormat": {"bold": True}
    })
    print(f"作成完了: {sheet_name}")
    time.sleep(3)

print("\nシート構成の更新完了！")
