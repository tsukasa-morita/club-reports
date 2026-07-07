#!/bin/bash
# ===== run_create.command =====
echo "===== MarketData 初期作成 開始 ====="
date "+日時: %Y年 %m月 %d日 %a %H時%M分%S秒 %Z"

# 作業ディレクトリに移動
cd /Users/xj_tsukasa_xj/Desktop/market_report || exit

# Python 仮想環境があれば activate
# source ~/miniconda3/bin/activate myenv

# スプレッドシートのシート作成
python3 ./create_sheets.py

# 初期データ投入（過去10年分）
python3 ./create_initial_data.py

echo "===== 完了 ====="
echo "Enterキーで終了"
read