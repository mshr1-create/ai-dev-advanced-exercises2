#!/bin/bash
# ニュース更新スクリプト (macOS/Linux)
# このスクリプトは all_topics.json を最新のニュース情報で更新します

echo "最新のニュース情報を取得中..."
echo

python3 rss.py

if [ $? -eq 0 ]; then
    echo
    echo "ニュース更新が完了しました。"
    echo "ブラウザをリロード(F5)して、最新情報を確認してください。"
else
    echo
    echo "エラーが発生しました。.env ファイルと API キーを確認してください。"
fi
