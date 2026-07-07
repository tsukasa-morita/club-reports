import subprocess, os, glob, shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.expanduser("~/club-reports")

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO_DIR)
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
    else:
        print(result.stdout)
    return result.returncode

today = datetime.today()
date_str = today.strftime('%Y%m%d')
date_jp = today.strftime('%Y年%m月%d日')

print("GitHubにアップロード中...")

# report-automationで生成したレポートをclub-reposにコピー
src = os.path.join(BASE_DIR, "market_report.html")
dst = os.path.join(REPO_DIR, "market_report.html")
shutil.copy2(src, dst)

os.chdir(REPO_DIR)

# 日付付きアーカイブを保存
run(f"cp market_report.html {date_str}.html")

# 既存のアーカイブ一覧を取得
archives = sorted(glob.glob(os.path.join(REPO_DIR, '[0-9]'*8 + '.html')), reverse=True)
archives = [os.path.basename(f) for f in archives]

# アーカイブリンクのHTML生成
archive_links = ''
for f in archives:
    d = f.replace('.html', '')
    year, month, day = d[:4], d[4:6], d[6:8]
    label = f"{year}年{month}月{day}日"
    archive_links += f'<li><a href="/{f}">{label}のレポート</a></li>\n'

# index.htmlを最新レポート＋アーカイブ一覧で生成
with open(os.path.join(REPO_DIR, 'market_report.html'), 'r') as f:
    content = f.read()

archive_section = f'''
<div style="max-width:760px;margin:0 auto;padding:1rem 1.5rem 2rem;font-family:'Noto Sans JP',sans-serif;">
  <hr style="margin:2rem 0;border:0.5px solid rgba(0,0,0,0.1);">
  <div style="font-size:14px;font-weight:700;margin-bottom:1rem;color:#1a1a18;">📁 過去のレポート</div>
  <ul style="list-style:none;padding:0;">
    {archive_links}
  </ul>
</div>
'''

# </body>の直前にアーカイブセクションを挿入
index_content = content.replace('</body>', archive_section + '</body>')

with open(os.path.join(REPO_DIR, 'index.html'), 'w') as f:
    f.write(index_content)

# GitHubにプッシュ
run(f"git add {date_str}.html index.html")
run(f'git commit -m "週次レポート更新 {date_jp}"')
run("git push origin main")

print(f"完了！→ https://invest-club.curiation.jp")
