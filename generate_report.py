# generate_report.py
# スプレッドシートから実データを取得してmarket_report.htmlを自動生成する
# ※ Claude APIなし・ルールベースで文章生成

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import signal
import sys

# ===== 設定 =====
BASE_DIR = '/Users/xj_tsukasa_xj/curiation/05_code/investment_lab/report-automation'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials', 'marketreportproject.json')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'market_report_template.html')
OUTPUT_FILE = os.path.join(BASE_DIR, 'market_report.html')

# ===== Google Sheets 認証 =====
# oauth2client/gspreadのHTTP呼び出しにtimeout指定が無く、Google側が応答しないと
# 無期限にハングする不具合があったため、signal.alarmで強制タイムアウトを設ける
class AuthTimeoutError(Exception):
    pass

def _auth_timeout_handler(signum, frame):
    raise AuthTimeoutError("Google Sheets認証がタイムアウトしました（30秒）")

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
try:
    signal.signal(signal.SIGALRM, _auth_timeout_handler)
    signal.alarm(30)
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open('MarketData')
    signal.alarm(0)
except Exception as e:
    signal.alarm(0)
    print(f"Google Sheets認証失敗: {e}")
    sys.exit(1)

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
        data = data[data.index <= pd.Timestamp.today()]
        return data.sort_index()
    except Exception as e:
        print(f"エラー: {sheet_name}", e)
        return None

def get_latest(data, col='終値'):
    if data is None or col not in data.columns:
        return None
    return data[col].dropna().iloc[-1]

def get_latest_date(data, col='終値'):
    if data is None or col not in data.columns:
        return None
    series = data[col].dropna()
    if series.empty:
        return None
    d = series.index[-1]
    return f"{d.month}/{d.day}"

def get_week_change(data, col='終値'):
    if data is None or col not in data.columns:
        return None
    series = data[col].dropna()
    if len(series) < 2:
        return None
    recent = series[series.index >= series.index[-1] - pd.Timedelta(days=7)]
    if len(recent) < 2:
        return None
    change = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0] * 100
    return change

def get_weekly_series(data, col='終値', weeks=13):
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

def get_daily_series(data, col='終値', days=10):
    if data is None or col not in data.columns:
        return [], []
    recent = data[[col]].dropna().tail(days)
    labels = [d.strftime('%-m/%-d') for d in recent.index]
    values = [round(v, 2) for v in recent[col].tolist()]
    return labels, values

def fmt_value(val, prefix='', suffix='', decimals=0):
    if val is None:
        return '-'
    if decimals == 0:
        return f"{prefix}{int(val):,}{suffix}"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_change(change, suffix='%'):
    if change is None:
        return '-', 'up'
    sign = '+' if change >= 0 else ''
    cls = 'up' if change >= 0 else 'down'
    return f"前週末比 {sign}{change:.1f}{suffix}", cls

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
nikkei_val  = get_latest(nikkei)
sp500_val   = get_latest(sp500)
usdjpy_val  = get_latest(usdjpy)
eurjpy_val  = get_latest(eurjpy)
jgb_val     = get_latest(jgb, col='値')
us10y_val   = get_latest(us10y, col='値')
gold_val    = get_latest(gold)
# 日経・JGBは情報源側の公開ラグで最新日を持ってないことがあるため、実際に何日時点の値かを明示する
nikkei_asof = get_latest_date(nikkei)
jgb_asof    = get_latest_date(jgb, col='値')
oil_val     = get_latest(oil)
btc_val     = get_latest(btc)
eth_val     = get_latest(eth)
vix_val     = get_latest(vix, col='値')
fng_val     = get_latest(fng, col='値')

if fng is not None:
    try:
        sheet_fng = spreadsheet.worksheet('恐怖強欲指数')
        fng_records = sheet_fng.get_all_records()
        # レーティング列は文字列なのでget_sheet_data側の数値変換にかからない。
        # シート上の行順（挿入方向）に依存しないよう、日付文字列で最新行を判定する
        latest_fng_record = max(fng_records, key=lambda r: r['日付']) if fng_records else None
        fng_rating = latest_fng_record['レーティング'] if latest_fng_record else 'N/A'
    except:
        fng_rating = 'N/A'
else:
    fng_rating = 'N/A'

nikkei_chg  = get_week_change(nikkei)
sp500_chg   = get_week_change(sp500)
usdjpy_chg  = get_week_change(usdjpy)
eurjpy_chg  = get_week_change(eurjpy)
jgb_chg     = get_week_change(jgb, col='値')
us10y_chg   = get_week_change(us10y, col='値')
fng_chg     = get_week_change(fng, col='値')
gold_chg    = get_week_change(gold)
oil_chg     = get_week_change(oil)
btc_chg     = get_week_change(btc)
eth_chg     = get_week_change(eth)
vix_chg     = get_week_change(vix, col='値')

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
fng_str,     fng_cls     = fmt_change(fng_chg)

# ===== ルールベースで文章生成（API不要）=====
print("ルールベースで文章生成中...")

def _sign(chg):
    """変化率の符号付き文字列"""
    if chg is None:
        return '横ばい'
    sign = '+' if chg >= 0 else ''
    return f"{sign}{chg:.1f}%"

def _dir(chg):
    """上昇・下落・横ばいの判定"""
    if chg is None:
        return '横ばい'
    if chg >= 1.0:
        return '上昇'
    elif chg <= -1.0:
        return '下落'
    else:
        return '横ばい'

def _strength(chg):
    """変化の強さ"""
    if chg is None:
        return ''
    abs_chg = abs(chg)
    if abs_chg >= 3.0:
        return '大きく'
    elif abs_chg >= 1.0:
        return ''
    else:
        return '小幅に'

# --- テーマ生成 ---
def generate_theme():
    n_dir = _dir(nikkei_chg)
    s_dir = _dir(sp500_chg)
    v_level = vix_val or 20

    if v_level >= 30:
        return "市場に嵐？緊張高まる1週間"
    elif v_level >= 25:
        return "警戒感漂う市場の1週間"
    elif n_dir == '上昇' and s_dir == '上昇':
        return "日米株がそろって上昇した1週間"
    elif n_dir == '下落' and s_dir == '下落':
        return "日米株がそろって下落した1週間"
    elif n_dir == '上昇' and s_dir == '下落':
        return "日本株が踏ん張った1週間"
    elif n_dir == '下落' and s_dir == '上昇':
        return "米国株が堅調も日本株は軟調"
    else:
        return "方向感を探る1週間"

# --- まとめ生成 ---
def generate_summary():
    n_str = _sign(nikkei_chg)
    s_str = _sign(sp500_chg)
    u_str = _sign(usdjpy_chg)
    g_str = _sign(gold_chg)
    v_level = vix_val or 20
    fng_level = fng_val or 50

    # 株式の状況
    n_sent = f"日経平均は{_strength(nikkei_chg)}{_dir(nikkei_chg)}し（{n_str}）"
    s_sent = f"アメリカのS&P500も{_strength(sp500_chg)}{_dir(sp500_chg)}しました（{s_str}）。"

    # 為替の状況
    if usdjpy_chg is not None:
        if usdjpy_chg >= 1.0:
            u_sent = f"円安が進み、1ドル{fmt_value(usdjpy_val, decimals=1)}円台となりました。"
        elif usdjpy_chg <= -1.0:
            u_sent = f"円高が進み、1ドル{fmt_value(usdjpy_val, decimals=1)}円台となりました。"
        else:
            u_sent = f"為替は{fmt_value(usdjpy_val, decimals=1)}円台で安定していました。"
    else:
        u_sent = ""

    # 市場心理
    if v_level >= 30:
        v_sent = f"VIX（恐怖指数）は{fmt_value(vix_val, decimals=1)}と高水準で、投資家の不安が高まっています。"
    elif v_level >= 20:
        v_sent = f"VIX（恐怖指数）は{fmt_value(vix_val, decimals=1)}とやや警戒水準です。"
    else:
        v_sent = f"VIX（恐怖指数）は{fmt_value(vix_val, decimals=1)}と落ち着いた水準です。"

    # 金の動き
    if gold_chg is not None and abs(gold_chg) >= 1.0:
        g_sent = f"安全資産の金は{_strength(gold_chg)}{_dir(gold_chg)}（{g_str}）しました。"
    else:
        g_sent = ""

    parts = [n_sent, s_sent, u_sent, v_sent, g_sent]
    return ''.join([p for p in parts if p])

# --- ニュースカード生成 ---
def generate_news():
    news = []

    # 株式カード（日経平均）
    if nikkei_chg is not None:
        nikkei_body = (
            f"今週の日経平均は{fmt_value(nikkei_val)}円で取引を終えました。"
            f"週間では{_strength(nikkei_chg)}{_dir(nikkei_chg)}し、変化率は{_sign(nikkei_chg)}でした。"
            f"アメリカのS&P500は{_sign(sp500_chg)}と{'同様に' if (nikkei_chg or 0) * (sp500_chg or 0) > 0 else '対照的に'}{_dir(sp500_chg)}しました。"
        )
        news.append({
            "tag": "株式",
            "tag_color": "blue" if (nikkei_chg or 0) >= 0 else "red",
            "headline": f"日経平均、今週は{_strength(nikkei_chg)}{_dir(nikkei_chg)}（{_sign(nikkei_chg)}）",
            "body": nikkei_body
        })

    # 為替カード
    if usdjpy_chg is not None:
        if usdjpy_chg >= 1.0:
            fx_headline = f"円安進行、1ドル{fmt_value(usdjpy_val, decimals=1)}円台へ"
            fx_body = f"ドル円は今週{_sign(usdjpy_chg)}と円安が進みました。輸出企業には追い風ですが、輸入品の値段が上がりやすくなります。ユーロ円は{fmt_value(eurjpy_val, decimals=1)}円（{_sign(eurjpy_chg)}）でした。"
        elif usdjpy_chg <= -1.0:
            fx_headline = f"円高進行、1ドル{fmt_value(usdjpy_val, decimals=1)}円台へ"
            fx_body = f"ドル円は今週{_sign(usdjpy_chg)}と円高が進みました。海外旅行や輸入品には追い風ですが、輸出企業には逆風となります。ユーロ円は{fmt_value(eurjpy_val, decimals=1)}円（{_sign(eurjpy_chg)}）でした。"
        else:
            fx_headline = f"為替は安定、ドル円{fmt_value(usdjpy_val, decimals=1)}円台"
            fx_body = f"ドル円は{fmt_value(usdjpy_val, decimals=1)}円台（{_sign(usdjpy_chg)}）と小幅な動きにとどまりました。ユーロ円は{fmt_value(eurjpy_val, decimals=1)}円（{_sign(eurjpy_chg)}）でした。"
        news.append({
            "tag": "為替",
            "tag_color": "amber",
            "headline": fx_headline,
            "body": fx_body
        })

    # コモディティ・暗号資産カード
    if gold_chg is not None or oil_chg is not None:
        commodity_body = (
            f"金は{fmt_value(gold_val, prefix='$')}（{_sign(gold_chg)}）、"
            f"原油は{fmt_value(oil_val, prefix='$', decimals=1)}（{_sign(oil_chg)}）でした。"
        )
        if btc_chg is not None:
            commodity_body += f"ビットコインは{fmt_value(btc_val, prefix='$')}（{_sign(btc_chg)}）と仮想通貨市場も{'活況' if (btc_chg or 0) >= 0 else '軟調'}でした。"
        news.append({
            "tag": "コモディティ",
            "tag_color": "amber" if (gold_chg or 0) >= 0 else "red",
            "headline": f"金は{_dir(gold_chg)}、原油は{_dir(oil_chg)}",
            "body": commodity_body
        })

    return news

# --- 来週のポイント生成 ---
def generate_points():
    points = []
    v_level = vix_val or 20
    us10y_level = us10y_val or 4.0

    # VIXに応じたポイント
    if v_level >= 25:
        points.append(f"VIXが{fmt_value(vix_val, decimals=1)}と高水準。市場の波乱に注意が必要です")
    else:
        points.append(f"VIXは{fmt_value(vix_val, decimals=1)}と落ち着いた水準。引き続き主要指標の動きを確認しましょう")

    # 金利に応じたポイント
    if us10y_level >= 4.5:
        points.append(f"米国10年債利回りは{fmt_value(us10y_val, suffix='%', decimals=2)}と高水準。株式市場への影響に注目")
    else:
        points.append(f"米国10年債利回り（{fmt_value(us10y_val, suffix='%', decimals=2)}）の動向を引き続き注視")

    # 為替に応じたポイント
    if usdjpy_chg is not None and abs(usdjpy_chg) >= 1.0:
        points.append(f"ドル円の動き（現在{fmt_value(usdjpy_val, decimals=1)}円）が続くか注目です")
    else:
        points.append("来週も日米の経済指標の発表に注目しましょう")

    return points

# --- 文章データ組み立て ---
ai_data = {
    "theme":   generate_theme(),
    "summary": generate_summary(),
    "news":    generate_news(),
    "points":  generate_points()
}

# ===== テンプレート読み込み =====
print("HTMLテンプレート読み込み中...")
with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    html = f.read()

# ===== 数値の差し替え =====
html = html.replace('{{DATE_RANGE}}', date_range)

html = html.replace('{{NIKKEI_VAL}}',  fmt_value(nikkei_val))
html = html.replace('{{NIKKEI_CHG}}',  nikkei_str)
html = html.replace('{{NIKKEI_CLS}}',  nikkei_cls)
html = html.replace('{{NIKKEI_ASOF}}', nikkei_asof or '-')
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
html = html.replace('{{JGB_ASOF}}',    jgb_asof or '-')
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
html = html.replace('{{FNG_CHG}}',     fng_str)
html = html.replace('{{FNG_CLS}}',     fng_cls)
html = html.replace('{{VIX_CHG}}',     vix_str)
html = html.replace('{{VIX_CLS}}',     vix_cls)

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

# ===== 文章の差し替え =====
html = html.replace("{{THEME}}", ai_data["theme"])
html = html.replace("{{SUMMARY}}", ai_data["summary"])

news_html = ""
for news in ai_data["news"]:
    news_html += f"""
    <div class="news-card">
      <div class="news-tag {news['tag_color']}">{news['tag']}</div>
      <div class="news-headline">{news['headline']}</div>
      <div class="news-body">{news['body']}</div>
    </div>"""
html = html.replace("{{NEWS_CARDS}}", news_html)

points_html = ""
for point in ai_data["points"]:
    points_html += f"<li>{point}</li>"
html = html.replace("{{POINTS}}", points_html)

# ===== 出力 =====
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"完了！→ {OUTPUT_FILE}")
print(f"テーマ：{ai_data['theme']}")
print(f"まとめ：{ai_data['summary'][:50]}...")

# ===== TODO: API再導入時はここを復活させる =====
# import anthropic, json
# client_ai = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
# ... （元のコード）