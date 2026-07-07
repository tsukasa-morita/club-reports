import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib.pyplot as plt
import os
from matplotlib import rcParams

# ===== 日本語フォント設定 =====
rcParams['font.family'] = 'Hiragino Sans'
rcParams['axes.unicode_minus'] = False

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

# ===== チャート出力フォルダ =====
os.makedirs("charts", exist_ok=True)

# ===== 対象マップ（カテゴリーで整理） =====
# type: 'ohlcv'=株式・コモディティ, 'ohlc'=為替, 'single'=金利・VIX
assets_map = {
    # 株価
    'A01_Nikkei':       ('日本（日経平均）',    'ohlcv'),
    'A02_SP500':        ('アメリカ（S＆P500）', 'ohlcv'),
    'A03_DAX':          ('ドイツ（DAX）',       'ohlcv'),
    'A04_Shanghai':     ('中国（上海総合）',     'ohlcv'),
    'A05_Bovespa':      ('ブラジル（ボベスパ）', 'ohlcv'),
    'A06_Sensex':       ('インド（SENSEX）',     'ohlcv'),
    # 業種
    'B01_Food':         ('食品',               'ohlcv'),
    'B02_Energy':       ('エネルギー資源',       'ohlcv'),
    'B03_Construction': ('建設・資材',           'ohlcv'),
    'B04_Materials':    ('素材・化学',           'ohlcv'),
    'B05_Pharma':       ('医薬品',              'ohlcv'),
    'B06_Auto':         ('自動車・輸送機',        'ohlcv'),
    'B07_Steel':        ('鉄鋼・非鉄',          'ohlcv'),
    'B08_Machinery':    ('機械',               'ohlcv'),
    'B09_Electronics':  ('電機・精密',           'ohlcv'),
    'B10_ITServices':   ('情報通信・サービス',    'ohlcv'),
    'B11_ElectricGas':  ('電力・ガス',           'ohlcv'),
    'B12_Transport':    ('運輸・物流',           'ohlcv'),
    'B13_Trading':      ('商社・卸売',           'ohlcv'),
    'B14_Retail':       ('小売',               'ohlcv'),
    'B15_Banks':        ('銀行',               'ohlcv'),
    'B16_FinanceExBanks':('金融（除く銀行）',    'ohlcv'),
    'B17_RealEstate':   ('不動産',              'ohlcv'),
    # 為替
    'C01_USDJPY':       ('ドル円',              'ohlc'),
    'C02_EURJPY':       ('ユーロ円',             'ohlc'),
    # 債券（単一値）
    'D01_JGB10Y':       ('日本10年債',           'single'),
    'D02_US10Y':        ('米国10年債',           'single'),
    # コモディティ
    'E01_Gold':         ('金',                 'ohlcv'),
    'E02_CrudeOil':     ('原油',               'ohlcv'),
    # 仮想通貨
    'F01_BTC':          ('ビットコイン',          'ohlcv'),
    'F02_ETH':          ('イーサリアム',          'ohlcv'),
}

# ===== チャート作成 =====
for key, (sheet_name, data_type) in assets_map.items():
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = pd.DataFrame(sheet.get_all_records())

        if data.empty:
            print(f"データなし: {sheet_name}")
            continue

        # 日付をdatetimeに変換
        data['日付'] = pd.to_datetime(data['日付'])
        data.set_index('日付', inplace=True)

        # 数値列を強制的にfloat変換（文字列対策）
        for col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')

        # 今日以降のデータを除外
        data = data[data.index <= pd.Timestamp.today()]

        # 週次データを実際の日付で抽出（毎週最終取引日を使用）
        if data_type == 'single':
            weekly = data[['値']].groupby(pd.Grouper(freq='W')).last().dropna()
            weekly.index = data[['値']].groupby(pd.Grouper(freq='W')).apply(lambda x: x.index[-1] if len(x) > 0 else None).dropna()
            close_col = '値'
        else:
            weekly = data[['終値']].groupby(pd.Grouper(freq='W')).last().dropna()
            weekly.index = data[['終値']].groupby(pd.Grouper(freq='W')).apply(lambda x: x.index[-1] if len(x) > 0 else None).dropna()
            close_col = '終値'

        # 直近6ヶ月分
        recent = weekly[weekly.index >= (weekly.index.max() - pd.DateOffset(months=6))]
        if recent.empty:
            print(f"直近6ヶ月のデータなし: {sheet_name}")
            continue

        # X軸ラベルを4週ごと
        x_labels = recent.index[::-1][::4][::-1]

        # 最大値取得
        max_close = recent[close_col].max()
        max_date = recent[close_col].idxmax()

        # チャート描画
        plt.figure(figsize=(12, 6))
        plt.plot(recent.index, recent[close_col], marker='o', linestyle='-')
        plt.title(f"{sheet_name}（直近6ヶ月）")
        plt.xlabel("日付")
        plt.ylabel("終値" if close_col == '終値' else "値")
        plt.grid(True)
        plt.xticks(x_labels, [d.strftime('%Y-%m-%d') for d in x_labels], rotation=45)
        plt.text(max_date, max_close, f'{max_close:.2f}', ha='center', va='bottom', fontsize=10)
        plt.tight_layout()

        # 保存
        filename = f"charts/{key}_recent6months.png"
        plt.savefig(filename)
        plt.close()
        print(f"作成完了: {filename}")

    except Exception as e:
        print(f"エラー: {sheet_name}", e)