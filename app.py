from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # セッション用の秘密鍵
upload_folder_env = os.environ.get('UPLOAD_FOLDER')
if upload_folder_env:
    upload_folder = os.path.abspath(upload_folder_env)
else:
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')

app.config['UPLOAD_FOLDER'] = upload_folder

# アップロードフォルダが存在しない場合は作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 管理者認証用デコレータ
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_photos(sort_by: str = 'name'):
    """写真のリストを取得"""
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        return []
    upload_dir = app.config['UPLOAD_FOLDER']
    photos = [f for f in os.listdir(upload_dir)
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    if sort_by == 'upload':
        upload_folder = app.config['UPLOAD_FOLDER']
        photos.sort(key=lambda filename: os.path.getmtime(os.path.join(upload_folder, filename)))
    else:
        photos.sort()
    return photos


def get_photo_details(sort_by: str = 'name'):
    """写真の詳細情報（ファイル名、URL、タイムスタンプ）を取得"""
    filenames = get_photos(sort_by=sort_by)
    details = []
    for name in filenames:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], name)
        uploaded_at = None
        if os.path.exists(filepath):
            uploaded_at = datetime.fromtimestamp(os.path.getmtime(filepath))
        details.append({
            'filename': name,
            'url': url_for('serve_upload', filename=name),
            'uploaded_at': uploaded_at.isoformat() if uploaded_at else None
        })
    return details

@app.route('/')
def index():
    photos = get_photos(sort_by='upload')
    return render_template('upload.html', photos=photos)

@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'ファイルがありません'}), 400
    
    photo = request.files['photo']
    
    if photo.filename == '':
        return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
    filename = secure_filename(photo.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    photo.save(filepath)
    
    # 写真のURLを生成
    photo_url = url_for('serve_upload', filename=filename)
    
    return jsonify({
        'success': True,
        'filename': filename,
        'photo_url': photo_url
    })

@app.route('/api/photos')
def api_photos():
    """写真のリストをJSONで返すAPI"""
    photos = get_photos(sort_by='upload')
    photo_urls = [url_for('serve_upload', filename=photo) for photo in photos]
    recent_photos = photos[-10:]
    top_photos = photos[-30:-10] if len(photos) > 10 else photos[:-10]
    recent_photo_urls = [url_for('serve_upload', filename=photo) for photo in recent_photos]
    top_photo_urls = [url_for('serve_upload', filename=photo) for photo in top_photos]
    return jsonify({
        'photos': photos,
        'photo_urls': photo_urls,
        'recent_photos': recent_photos,
        'recent_photo_urls': recent_photo_urls,
        'top_photos': top_photos,
        'top_photo_urls': top_photo_urls
    })

# 管理者ログインページ
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # 固定のユーザー名とパスワードを使用（実際の運用ではデータベース等を使用）
        if username == 'admin' and password == 'password':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('ユーザー名またはパスワードが正しくありません', 'error')
            return render_template('admin_login.html')
    return render_template('admin_login.html')

# 管理者ログアウト
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# 管理者ダッシュボード
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    photos = get_photos()
    # 写真をIDとファイル名のペアに変換
    photos_data = [(i+1, photo) for i, photo in enumerate(photos)]
    # ランキングデータは空（データベースがないため）
    rankings = []
    return render_template('admin_dashboard.html', photos=photos_data, rankings=rankings)

# 管理者用スライドショールート
@app.route('/admin/slideshow')
@admin_required
def admin_slideshow():
    photos = get_photos(sort_by='upload')
    recent_photos = photos[-10:]
    top_photos = photos[-30:-10] if len(photos) > 10 else photos[:-10]
    photo_urls = [url_for('serve_upload', filename=photo) for photo in photos]
    recent_photo_urls = [url_for('serve_upload', filename=photo) for photo in recent_photos]
    top_photo_urls = [url_for('serve_upload', filename=photo) for photo in top_photos]
    return render_template(
        'admin_slideshow.html',
        photos=photos,
        photos_top=top_photos,
        photos_recent=recent_photos,
        photo_urls=photo_urls,
        recent_photo_urls=recent_photo_urls,
        top_photo_urls=top_photo_urls
    )


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """アップロードされた写真を配信する"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ランキング作成（現時点ではデータベースがないため、実装は簡易版）
@app.route('/admin/ranking/create', methods=['POST'])
@admin_required
def create_ranking():
    flash('ランキング機能は現在データベースが必要です。今後実装予定です。', 'info')
    return redirect(url_for('admin_dashboard'))

# 写真削除
@app.route('/admin/delete/<int:photo_id>', methods=['POST'])
@admin_required
def delete_photo(photo_id):
    photos = get_photos()
    if 0 < photo_id <= len(photos):
        filename = photos[photo_id - 1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            flash('写真を削除しました', 'success')
        else:
            flash('ファイルが見つかりませんでした', 'error')
    else:
        flash('無効な写真IDです', 'error')
    return redirect(url_for('admin_dashboard'))

# ランキング一覧表示
@app.route('/rankings')
def show_rankings():
    # ランキングデータが存在する場合はここで取得
    # 現在は空のリストを返す（データベースがないため）
    rankings_data = []
    return render_template('rankings.html', rankings=rankings_data)

# 個別のランキング表示
@app.route('/rankings/<int:group_id>')
def show_ranking(group_id):
    # ランキングデータが存在する場合はここで取得
    # 現在はダミーデータを返す
    ranking_data = {
        'id': group_id,
        'name': f'ランキング {group_id}',
        'photos': []
    }
    return render_template('ranking.html', ranking=ranking_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0') 