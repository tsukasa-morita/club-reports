import gspread
from oauth2client.service_account import ServiceAccountCredentials

SERVICE_ACCOUNT_FILE = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation/credentials/marketreportproject.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

# 全シートのデータを削除（ヘッダーは残す）
for sheet in spreadsheet.worksheets():
    print(f"クリア中: {sheet.title}")
    if sheet.row_count > 1:
        sheet.delete_rows(2, sheet.row_count)
    
print("完了！全シートのデータ（ヘッダー以外）を削除しました")
