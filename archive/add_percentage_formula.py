import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

SERVICE_ACCOUNT_FILE = './credentials/marketreportproject.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

ohlc_sheets = ['日本（日経平均）', 'アメリカ（S＆P500）', 'ドイツ（DAX）', '中国（上海総合）', 
               'ブラジル（ボベスパ）', 'インド（SENSEX）', '食品', 'エネルギー資源', '建設・資材', 
               '素材・化学', '医薬品', '自動車・輸送機', '鉄鋼・非鉄', '機械', '電機・精密',
               '情報通信・サービス', '電力・ガス', '運輸・物流', '商社・卸売', '小売', '銀行', 
               '金融（除く銀行）', '不動産', 'ドル円', 'ユーロ円', '金', '原油', 'ビットコイン', 'イーサリアム']

for sheet_name in ohlc_sheets:
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        print(f"処理中: {sheet_name}")
        
        # D2セルに関数を入れる
        formula = '=IF(C2="", "", C2/B3)'
        sheet.update_cell(2, 4, formula)
        time.sleep(0.5)
        
        # D2をコピーして全行に貼り付け
        last_row = len(sheet.get_all_values())
        sheet.copy_range(f'D2:D2', f'D2:D{last_row}')
        time.sleep(1)
        
        # D列の書式設定：%表示、小数点第2位まで
        sheet.format("D2:D10000", {
            "horizontalAlignment": "RIGHT",
            "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
        })
        
        print(f"完了: {sheet_name}")
        time.sleep(1)
        
    except Exception as e:
        print(f"エラー: {sheet_name} - {e}")

print("\n全シート完了！")
