import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

SERVICE_ACCOUNT_FILE = './credentials/marketreportproject.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

assets = ['日本（日経平均）', 'アメリカ（S＆P500）', 'ドイツ（DAX）', '中国（上海総合）', 
          'ブラジル（ボベスパ）', 'インド（SENSEX）', '食品', 'エネルギー資源', '建設・資材', 
          '素材・化学', '医薬品', '自動車・輸送機', '鉄鋼・非鉄', '機械', '電機・精密',
          '情報通信・サービス', '電力・ガス', '運輸・物流', '商社・卸売', '小売', '銀行', 
          '金融（除く銀行）', '不動産', 'ドル円', 'ユーロ円', '日本10年債', '米国10年債', 
          '金', '原油', 'ビットコイン', 'イーサリアム', 'VIX（恐怖指数）']

for sheet_name in assets:
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.format("2:10000", {
            "horizontalAlignment": "RIGHT",
            "numberFormat": {"type": "NUMBER", "pattern": "#,##0.0"}
        })
        print(f"書式変更完了: {sheet_name}")
        time.sleep(2)
    except Exception as e:
        print(f"エラー: {sheet_name} - {e}")

print("全シートの書式変更完了！")
