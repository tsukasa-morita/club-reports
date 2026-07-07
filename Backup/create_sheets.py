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

# ===== スプレッドシート =====
spreadsheet = client.open('MarketData')

# ===== 資産マップ =====
assets_map = {
    # 株式指数
    'Nikkei': '日本（日経平均）',
    'SP500': 'アメリカ（S＆P500）',
    'DAX': 'ドイツ（DAX）',
    'Shanghai': '中国（上海総合）',
    'Bovespa': 'ブラジル（ボベスパ）',
    'Sensex': 'インド（SENSEX）',
    # TOPIX17
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
    'VIX': 'VIX（恐怖指数）',
    'AdvanceDecline': '騰落レシオ',
    'MarginRatio': '信用倍率'
}

# ===== カラム定義 =====
ohlcv = ['日付', '始値', '高値', '安値', '終値', '出来高']
ohlc = ['日付', '始値', '高値', '安値', '終値']
single = ['日付', '値']

columns_map = {}
for key in assets_map:
    if key in ['USDJPY', 'EURJPY']:
        columns_map[key] = ohlc
    elif key in ['VIX', 'AdvanceDecline', 'MarginRatio', 'JGB10Y', 'US10Y']:
        columns_map[key] = single
    else:
        columns_map[key] = ohlcv

# ===== 既存シート =====
existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

# ===== シート作成 =====
for key, sheet_name in assets_map.items():
    if sheet_name not in existing_sheets:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        sheet.append_row(columns_map[key])
        time.sleep(1)

# ===== 不要シート削除（英語＋SP100） =====
delete_targets = list(assets_map.keys()) + ['SP100']
worksheets = spreadsheet.worksheets()
for ws in worksheets:
    if ws.title in delete_targets:
        try:
            spreadsheet.del_worksheet(ws)
            time.sleep(1)
            print(f"削除: {ws.title}")
        except Exception as e:
            print(f"削除失敗: {ws.title}", e)

# ===== 並び順 =====
order = [
    '日本（日経平均）', 'アメリカ（S＆P500）', 'ドイツ（DAX）', '中国（上海総合）', 'ブラジル（ボベスパ）', 'インド（SENSEX）',
    '食品', 'エネルギー資源', '建設・資材', '素材・化学', '医薬品', '自動車・輸送機', '鉄鋼・非鉄', '機械', '電機・精密',
    '情報通信・サービス', '電力・ガス', '運輸・物流', '商社・卸売', '小売', '銀行', '金融（除く銀行）', '不動産',
    'ドル円', 'ユーロ円', '日本10年債', '米国10年債', '金', '原油', 'ビットコイン', 'イーサリアム', 'VIX（恐怖指数）',
    '騰落レシオ', '信用倍率'
]

# ===== 並び替え =====
try:
    worksheets = spreadsheet.worksheets()
    ordered_sheets = []
    for name in order:
        for ws in worksheets:
            if ws.title == name:
                ordered_sheets.append(ws)
    sheet1 = [ws for ws in worksheets if ws.title in ["Sheet1", "シート1"]]
    spreadsheet.reorder_worksheets(ordered_sheets + sheet1)
except Exception as e:
    print("並び替えスキップ:", e)

# ===== 完了 =====
print("完全版シート構成 完了！")
print("URL:", spreadsheet.url)