from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # セッション用の秘密鍵
app.config['UPLOAD_FOLDER'] = 'static/uploads'

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

def get_photos():
    """写真のリストを取得"""
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        return []
    photos = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    photos.sort()
    return photos

@app.route('/')
def index():
    photos = get_photos()
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
    photo_url = url_for('static', filename=f'uploads/{filename}')
    
    return jsonify({
        'success': True,
        'filename': filename,
        'photo_url': photo_url
    })

@app.route('/slideshow')
def slideshow():
    photos = get_photos()
    return render_template('slideshow.html', photos=photos)

@app.route('/api/photos')
def api_photos():
    """写真のリストをJSONで返すAPI"""
    photos = get_photos()
    photo_urls = [url_for('static', filename=f'uploads/{photo}') for photo in photos]
    return jsonify({'photos': photos, 'photo_urls': photo_urls})

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
    photos = get_photos()
    return render_template('admin_slideshow.html', photos=photos)

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