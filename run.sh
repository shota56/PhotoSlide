#!/bin/bash

# 仮想環境をアクティベート
source venv/bin/activate

# アプリケーションを起動
if command -v python >/dev/null 2>&1; then
  python app.py
elif command -v python3 >/dev/null 2>&1; then
  python3 app.py
else
  echo "python (or python3) が見つかりません。Pythonをインストールしてください。"
  exit 1
fi

