# generate_report.py
# スプレッドシートから実データを取得してmarket_report.htmlを自動生成する

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import os
import re

# ===== 設定 =====
BASE_DIR = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'marketreportproject.json')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'market_report_template.html')
OUTPUT_FILE = os.path.join(BASE_DIR, 'market_report.html')

# ===== Google Sheets 認証 =====
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(credentials)
spreadsheet = client.open('MarketData')

# ===== データ取得関数 =====
def get_sheet_data(sheet_name):
    """シートからデータを取得してDataFrameで返す"""
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        data = pd.DataFrame(sheet.get_all_records())
        if data.empty:
            return None
        data['日付'] = pd.to_datetime(data['日付'])
        data.set_index('日付', inplace=True)
        for col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        # 今日以降のデータを除外
        data = data[data.index <= pd.Timestamp.today()]
        return data.sort_index()
    except Exception as e:
        print(f"エラー: {sheet_name}", e)
        return None

def get_latest(data, col='終値'):
    """最新値を取得"""
    if data is None or col not in data.columns:
        return None
    return data[col].dropna().iloc[-1]

def get_week_change(data, col='終値'):
    """週間変化率を取得（先週末→今週末）"""
    if data is None or col not in data.columns:
        return None
    series = data[col].dropna()
    if len(series) < 2:
        return None
    # 直近5営業日以内の変化
    recent = series[series.index >= series.index[-1] - pd.Timedelta(days=7)]
    if len(recent) < 2:
        return None
    change = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0] * 100
    return change

def get_weekly_series(data, col='終値', weeks=13):
    """週次データを取得（直近n週）"""
    if data is None or col not in data.columns:
        return [], []
    weekly = data[[col]].groupby(pd.Grouper(freq='W')).last().dropna()
    weekly.index = data[[col]].groupby(pd.Grouper(freq='W')).apply(
        lambda x: x.index[-1] if len(x) > 0 else None
    ).dropna()
    recent = weekly.tail(weeks)
    labels = [d.strftime('%-m/%-d') for d in recent.index]
    values = [round(v, 2) for v in recent[col].tolist()]
    return labels, values

def get_daily_series(data, col='終値', days=5):
    """直近n営業日のデータを取得"""
    if data is None or col not in data.columns:
        return [], []
    recent = data[[col]].dropna().tail(days)
    labels = [d.strftime('%-m/%-d') for d in recent.index]
    values = [round(v, 2) for v in recent[col].tolist()]
    return labels, values

def fmt_value(val, prefix='', suffix='', decimals=0):
    """数値のフォーマット"""
    if val is None:
        return '-'
    if decimals == 0:
        return f"{prefix}{int(val):,}{suffix}"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_change(change, suffix='%'):
    """変化率のフォーマットとクラス名"""
    if change is None:
        return '-', 'up'
    sign = '+' if change >= 0 else ''
    cls = 'up' if change >= 0 else 'down'
    return f"週間 {sign}{change:.1f}{suffix}", cls

# ===== データ取得 =====
print("データ取得中...")

nikkei = get_sheet_data('日本（日経平均）')
sp500  = get_sheet_data('アメリカ（S＆P500）')
usdjpy = get_sheet_data('ドル円')
eurjpy = get_sheet_data('ユーロ円')
jgb    = get_sheet_data('日本10年債')
us10y  = get_sheet_data('米国10年債')
gold   = get_sheet_data('金')
oil    = get_sheet_data('原油')
btc    = get_sheet_data('ビットコイン')
eth    = get_sheet_data('イーサリアム')
vix    = get_sheet_data('VIX（恐怖指数）')
fng    = get_sheet_data('恐怖強欲指数')

# ===== 数値計算 =====
# 最新値
nikkei_val  = get_latest(nikkei)
sp500_val   = get_latest(sp500)
usdjpy_val  = get_latest(usdjpy)
eurjpy_val  = get_latest(eurjpy)
jgb_val     = get_latest(jgb, col='値')
us10y_val   = get_latest(us10y, col='値')
gold_val    = get_latest(gold)
oil_val     = get_latest(oil)
btc_val     = get_latest(btc)
eth_val     = get_latest(eth)
vix_val     = get_latest(vix, col='値')
fng_val     = get_latest(fng, col='値')
# レーティングは数値変換せずに直接取得
if fng is not None:
    try:
        sheet_fng = spreadsheet.worksheet('恐怖強欲指数')
        fng_records = sheet_fng.get_all_records()
        fng_rating = fng_records[0]['レーティング'] if fng_records else 'N/A'
    except:
        fng_rating = 'N/A'
else:
    fng_rating = 'N/A' 

# 週間変化率
nikkei_chg  = get_week_change(nikkei)
sp500_chg   = get_week_change(sp500)
usdjpy_chg  = get_week_change(usdjpy)
eurjpy_chg  = get_week_change(eurjpy)
jgb_chg     = get_week_change(jgb, col='値')
us10y_chg   = get_week_change(us10y, col='値')
gold_chg    = get_week_change(gold)
oil_chg     = get_week_change(oil)
btc_chg     = get_week_change(btc)
eth_chg     = get_week_change(eth)
vix_chg     = get_week_change(vix, col='値')

# グラフデータ（週次・3ヶ月）
n_wlbl, n_wval   = get_daily_series(nikkei)
n_mlbl, n_mval   = get_weekly_series(nikkei)
s_wlbl, s_wval   = get_daily_series(sp500)
s_mlbl, s_mval   = get_weekly_series(sp500)
u_wlbl, u_wval   = get_daily_series(usdjpy)
u_mlbl, u_mval   = get_weekly_series(usdjpy)
e_wlbl, e_wval   = get_daily_series(eurjpy)
e_mlbl, e_mval   = get_weekly_series(eurjpy)
j_mlbl, j_mval   = get_weekly_series(jgb, col='値')
us_mlbl, us_mval = get_weekly_series(us10y, col='値')
g_wlbl, g_wval   = get_daily_series(gold)
g_mlbl, g_mval   = get_weekly_series(gold)
o_wlbl, o_wval   = get_daily_series(oil)
o_mlbl, o_mval   = get_weekly_series(oil)
b_mlbl, b_mval   = get_weekly_series(btc)
eth_mlbl, eth_mval = get_weekly_series(eth)
v_mlbl, v_mval   = get_weekly_series(vix, col='値')

# ===== 日付 =====
today = datetime.today()
# 先週月曜〜今週金曜
weekday = today.weekday()
if weekday == 6:
    days_back = 6
elif weekday == 5:
    days_back = 5
else:
    days_back = weekday
last_mon = today - timedelta(days=days_back)
last_fri = last_mon + timedelta(days=4)
date_range = f"{last_mon.year}年{last_mon.month}月{last_mon.day}日（月）〜 {last_fri.month}月{last_fri.day}日（金）"

# ===== フォーマット =====
nikkei_str,  nikkei_cls  = fmt_change(nikkei_chg)
sp500_str,   sp500_cls   = fmt_change(sp500_chg)
usdjpy_str,  usdjpy_cls  = fmt_change(usdjpy_chg)
eurjpy_str,  eurjpy_cls  = fmt_change(eurjpy_chg)
jgb_str,     jgb_cls     = fmt_change(jgb_chg)
us10y_str,   us10y_cls   = fmt_change(us10y_chg)
gold_str,    gold_cls    = fmt_change(gold_chg)
oil_str,     oil_cls     = fmt_change(oil_chg)
btc_str,     btc_cls     = fmt_change(btc_chg)
eth_str,     eth_cls     = fmt_change(eth_chg)
vix_str,     vix_cls     = fmt_change(vix_chg)

# ===== テンプレート読み込み =====
print("HTMLテンプレート読み込み中...")
with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    html = f.read()

# ===== 数値の差し替え =====

# 日付
html = html.replace('{{DATE_RANGE}}', date_range)

# 数値カード
html = html.replace('{{NIKKEI_VAL}}',  fmt_value(nikkei_val))
html = html.replace('{{NIKKEI_CHG}}',  nikkei_str)
html = html.replace('{{NIKKEI_CLS}}',  nikkei_cls)
html = html.replace('{{SP500_VAL}}',   fmt_value(sp500_val))
html = html.replace('{{SP500_CHG}}',   sp500_str)
html = html.replace('{{SP500_CLS}}',   sp500_cls)
html = html.replace('{{USDJPY_VAL}}',  fmt_value(usdjpy_val, suffix='円', decimals=1))
html = html.replace('{{USDJPY_CHG}}',  usdjpy_str)
html = html.replace('{{USDJPY_CLS}}',  usdjpy_cls)
html = html.replace('{{EURJPY_VAL}}',  fmt_value(eurjpy_val, suffix='円', decimals=1))
html = html.replace('{{EURJPY_CHG}}',  eurjpy_str)
html = html.replace('{{EURJPY_CLS}}',  eurjpy_cls)
html = html.replace('{{JGB_VAL}}',     fmt_value(jgb_val, suffix='%', decimals=2))
html = html.replace('{{JGB_CHG}}',     jgb_str)
html = html.replace('{{JGB_CLS}}',     jgb_cls)
html = html.replace('{{US10Y_VAL}}',   fmt_value(us10y_val, suffix='%', decimals=2))
html = html.replace('{{US10Y_CHG}}',   us10y_str)
html = html.replace('{{US10Y_CLS}}',   us10y_cls)
html = html.replace('{{GOLD_VAL}}',    fmt_value(gold_val, prefix='$', decimals=0))
html = html.replace('{{GOLD_CHG}}',    gold_str)
html = html.replace('{{GOLD_CLS}}',    gold_cls)
html = html.replace('{{OIL_VAL}}',     fmt_value(oil_val, prefix='$', decimals=1))
html = html.replace('{{OIL_CHG}}',     oil_str)
html = html.replace('{{OIL_CLS}}',     oil_cls)
html = html.replace('{{BTC_VAL}}',     fmt_value(btc_val, prefix='$', decimals=0))
html = html.replace('{{BTC_CHG}}',     btc_str)
html = html.replace('{{BTC_CLS}}',     btc_cls)
html = html.replace('{{ETH_VAL}}',     fmt_value(eth_val, prefix='$', decimals=0))
html = html.replace('{{ETH_CHG}}',     eth_str)
html = html.replace('{{ETH_CLS}}',     eth_cls)
html = html.replace('{{VIX_VAL}}',     fmt_value(vix_val, decimals=1))
html = html.replace('{{FNG_VAL}}',     fmt_value(fng_val, decimals=1))
html = html.replace('{{FNG_RATING}}',  str(fng_rating) if fng_rating else '-')
html = html.replace('{{VIX_CHG}}',     vix_str)
html = html.replace('{{VIX_CLS}}',     vix_cls)

# グラフデータ
html = html.replace('{{C1W_LBL}}',  str(n_wlbl))
html = html.replace('{{C1W_VAL}}',  str(n_wval))
html = html.replace('{{C1M_LBL}}',  str(n_mlbl))
html = html.replace('{{C1M_VAL}}',  str(n_mval))
html = html.replace('{{C2W_LBL}}',  str(s_wlbl))
html = html.replace('{{C2W_VAL}}',  str(s_wval))
html = html.replace('{{C2M_LBL}}',  str(s_mlbl))
html = html.replace('{{C2M_VAL}}',  str(s_mval))
html = html.replace('{{C3W_LBL}}',  str(u_wlbl))
html = html.replace('{{C3W_VAL}}',  str(u_wval))
html = html.replace('{{C3M_LBL}}',  str(u_mlbl))
html = html.replace('{{C3M_VAL}}',  str(u_mval))
html = html.replace('{{C4W_LBL}}',  str(e_wlbl))
html = html.replace('{{C4W_VAL}}',  str(e_wval))
html = html.replace('{{C4M_LBL}}',  str(e_mlbl))
html = html.replace('{{C4M_VAL}}',  str(e_mval))
html = html.replace('{{C5M_LBL}}',  str(j_mlbl))
html = html.replace('{{C5M_VAL}}',  str(j_mval))
html = html.replace('{{C6M_LBL}}',  str(us_mlbl))
html = html.replace('{{C6M_VAL}}',  str(us_mval))
html = html.replace('{{C7W_LBL}}',  str(g_wlbl))
html = html.replace('{{C7W_VAL}}',  str(g_wval))
html = html.replace('{{C7M_LBL}}',  str(g_mlbl))
html = html.replace('{{C7M_VAL}}',  str(g_mval))
html = html.replace('{{C8W_LBL}}',  str(o_wlbl))
html = html.replace('{{C8W_VAL}}',  str(o_wval))
html = html.replace('{{C8M_LBL}}',  str(o_mlbl))
html = html.replace('{{C8M_VAL}}',  str(o_mval))
html = html.replace('{{C9M_LBL}}',  str(b_mlbl))
html = html.replace('{{C9M_VAL}}',  str(b_mval))
html = html.replace('{{C10M_LBL}}', str(eth_mlbl))
html = html.replace('{{C10M_VAL}}', str(eth_mval))
html = html.replace('{{C11M_LBL}}', str(v_mlbl))
html = html.replace('{{C11M_VAL}}', str(v_mval))

# ===== Claude APIで文章生成 =====
print("Claude APIで文章生成中...")
import anthropic, json

client_ai = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

from datetime import datetime as _dt
_today = _dt.today().strftime("%Y年%m月%d日")
_weekstart = (_dt.today() - __import__("datetime").timedelta(days=6)).strftime("%Y年%m月%d日")

ai_prompt = f"""あなたは経済・投資教育の専門家です。小学生から大人まで読める週次マーケットレポートを作成してください。

必ず{_today}時点の最新情報のみを使用してください。
{_today}時点での最新ニュースをweb検索してください。検索クエリには必ず{_today}という日付を含めてください。
{_weekstart}より前の古いニュースは絶対に使用しないでください。
検索結果の日付を必ず確認し、{_weekstart}〜{_today}の範囲内のニュースのみ使用してください。
その上で、以下の数値データと組み合わせて、背景を踏まえた文章を作成してください。

今週の主要指標：
- 日経平均：{nikkei}円
- S&P500：{sp500}
- ドル円：{usdjpy}円
- 金：${gold}
- 原油：${oil}
- ビットコイン：${btc}
- 日本10年債利回り：{jgb}%
- VIX（恐怖指数）：{vix}

以下をJSON形式のみで返してください。他の文章は不要です。
{{
  "theme": "今週のテーマ（20文字以内・実際のニュースを反映した内容）",
  "summary": "今週のまとめ（200文字程度・実際に起きたことを小学生にもわかる言葉で）",
  "news": [
    {{"tag": "タグ", "tag_color": "blue", "headline": "見出し", "body": "本文100文字程度"}},
    {{"tag": "タグ", "tag_color": "red", "headline": "見出し", "body": "本文"}},
    {{"tag": "タグ", "tag_color": "amber", "headline": "見出し", "body": "本文"}}
  ],
  "points": ["来週のポイント1", "来週のポイント2", "来週のポイント3"]
}}"""

ai_message = client_ai.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    messages=[{"role": "user", "content": ai_prompt}]
)

ai_text = ""
for block in ai_message.content:
    if block.type == "text":
        ai_text = block.text

ai_text_clean = ai_text.strip()
if '```json' in ai_text_clean:
    ai_text_clean = ai_text_clean.split('```json')[1].split('```')[0].strip()
elif '```' in ai_text_clean:
    ai_text_clean = ai_text_clean.split('```')[1].split('```')[0].strip()

ai_data = json.loads(ai_text_clean)

html = html.replace("{{THEME}}", ai_data.get("theme", ""))
html = html.replace("{{SUMMARY}}", ai_data.get("summary", ""))

news_html = ""
for news in ai_data.get("news", []):
    news_html += f"""
    <div class="news-card">
      <div class="news-tag {news.get("tag_color", "")}">{news.get("tag", "")}</div>
      <div class="news-headline">{news.get("headline", "")}</div>
      <div class="news-body">{news.get("body", "")}</div>
    </div>"""
html = html.replace("{{NEWS_CARDS}}", news_html)

points_html = ""
for point in ai_data.get("points", []):
    points_html += f"<li>{point}</li>"
html = html.replace("{{POINTS}}", points_html)

# ===== 出力 =====
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"完了！→ {OUTPUT_FILE}")
