import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os

BASE_DIR = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'marketreportproject.json')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

OHLC_SHEETS = [
    '日本（日経平均）', 'アメリカ（S＆P500）', 'ドイツ（DAX）', '中国（上海総合）', 'ブラジル（ボベスパ）', 'インド（SENSEX）',
    '食品', 'エネルギー資源', '建設・資材', '素材・化学', '医薬品', '自動車・輸送機', '鉄鋼・非鉄', '機械', '電機・精密',
    '情報通信・サービス', '電力・ガス', '運輸・物流', '商社・卸売', '小売', '銀行', '金融（除く銀行）', '不動産',
    'ドル円', 'ユーロ円', '金', '原油', 'ビットコイン', 'イーサリアム'
]

for sheet_name in OHLC_SHEETS:
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        col_d = sheet.col_values(4)
        
        if len(col_d) <= 1:
            print(f"⏭️  {sheet_name}: データなし")
            continue
        
        updates = []
        for i, val in enumerate(col_d[1:], start=2):
            if val and val != '':
                try:
                    num_val = float(val)
                    new_val = round(num_val / 100, 4)
                    updates.append({'range': f'D{i}', 'values': [[new_val]]})
                except:
                    pass
        
        if updates:
            sheet.batch_update(updates)
            print(f"✅ {sheet_name}: {len(updates)}件 数値修正完了")
        
        sheet.format('D:D', {
            'numberFormat': {
                'type': 'PERCENT',
                'pattern': '0.00%'
            }
        })
        print(f"✅ {sheet_name}: D列を％表示に設定")
        
        time.sleep(1)
        
    except Exception as e:
        print(f"❌ {sheet_name}: {e}")

print("🎉 完了！")
