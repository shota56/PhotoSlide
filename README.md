# PhotoSlide - 写真アップロードアプリケーション

## セットアップ

### 1. 仮想環境のアクティベート

```bash
cd /Users/shotanishikawa/Desktop/PhotoSlide
source venv/bin/activate
```

### 2. 依存関係のインストール（必要な場合）

```bash
pip install -r requirements.txt
```

### 3. アプリケーションの起動

**推奨方法（仮想環境を自動でアクティベート）:**
```bash
./run.sh
```

**手動で仮想環境をアクティベートする場合:**
```bash
# 仮想環境をアクティベート
source venv/bin/activate

# アプリケーションを起動
python app.py
```

**注意:** `Python3 app.py`を直接実行すると、仮想環境が使われずにFlaskが見つからないエラーが発生する可能性があります。

### 4. ブラウザでアクセス

http://localhost:5000 にアクセスしてください。

## 機能

- 写真のアップロード（リロードなし）
- アップロードした写真のスライドショー表示
- リアルタイムでの写真更新（ポーリング）

## 注意事項

- 仮想環境をアクティベートしてからアプリケーションを起動してください
- 写真は `static/uploads/` フォルダに保存されます
- Render の Persistent Disk を利用する場合は、ディスクのマウント先を環境変数 `UPLOAD_FOLDER` として指定してください（例: `/var/uploads`）。アプリはそのパスを自動的に作成し、`/uploads/<ファイル名>` で配信します。
