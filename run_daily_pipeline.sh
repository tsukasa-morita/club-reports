#!/bin/bash
# マーケットレポートの自動パイプライン
# update_daily.py（データ取得）は毎日実行、
# generate_report.py（HTML生成・先週分の週次レポート）→ upload_github.py（公開）は土曜のみ実行
# 前段が失敗したら後段は実行しない

cd /Users/xj_tsukasa_xj/CURIATION/05_code/investment_lab/report-automation
/opt/miniconda3/bin/python3 update_daily.py || exit 1

# date +%u: 月=1 ... 土=6 日=7
if [ "$(date +%u)" = "6" ]; then
  /opt/miniconda3/bin/python3 generate_report.py \
    && /opt/miniconda3/bin/python3 upload_github.py
fi
