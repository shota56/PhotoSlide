from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import os
import json
import uuid


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

DATA_DIR = os.path.join(app.root_path, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

RESULT_CONFIG_FILE = os.path.join(DATA_DIR, 'result_config.json')

DEFAULT_CATEGORIES = [
    {"id": "category_1", "name": "新郎賞"},
    {"id": "category_2", "name": "新婦賞"},
    {"id": "category_3", "name": "総合賞"},
]


def load_result_config():
    if os.path.exists(RESULT_CONFIG_FILE):
        try:
            with open(RESULT_CONFIG_FILE, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    categories_by_id = {
        cat['id']: cat for cat in data.get('categories', [])
        if isinstance(cat, dict) and 'id' in cat
    }

    normalized_categories = []
    for default in DEFAULT_CATEGORIES:
        existing = categories_by_id.get(default['id'], {})
        name = existing.get('name') or default['name']
        photo = existing.get('photo') or None
        normalized_categories.append({
            'id': default['id'],
            'name': name,
            'photo': photo
        })

    order = data.get('order') or [cat['id'] for cat in DEFAULT_CATEGORIES]
    valid_ids = {cat['id'] for cat in normalized_categories}
    order = [cat_id for cat_id in order if cat_id in valid_ids]
    for cat in normalized_categories:
        if cat['id'] not in order:
            order.append(cat['id'])

    return {
        'categories': normalized_categories,
        'order': order
    }


def save_result_config(config):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESULT_CONFIG_FILE, 'w', encoding='utf-8') as fp:
        json.dump(config, fp, ensure_ascii=False, indent=2)


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
        photos.sort(key=lambda filename: os.path.getmtime(os.path.join(upload_folder, filename)), reverse=True)
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
    # 最新10投稿が2レーン目、11枚目~30枚目が1レーン目
    recent_photos = photos[:10]  # 最新10枚
    top_photos = photos[10:30] if len(photos) > 10 else []  # 11枚目~30枚目
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
    photos = get_photos(sort_by='upload')
    if not getattr(app, '_photo_uuid_map', None):
        app._photo_uuid_map = {}
    photos_data = []
    for filename in photos:
        photo_uuid = app._photo_uuid_map.get(filename)
        if not photo_uuid:
            photo_uuid = uuid.uuid4().hex
            app._photo_uuid_map[filename] = photo_uuid
        photos_data.append({
            'id': photo_uuid,
            'filename': filename,
            'url': url_for('serve_upload', filename=filename)
        })
    result_config = load_result_config()
    order_map = {cat_id: idx + 1 for idx, cat_id in enumerate(result_config['order'])}
    return render_template(
        'admin_dashboard.html',
        photos=photos_data,
        result_config=result_config,
        result_order_map=order_map
    )

# 管理者用スライドショールート
@app.route('/admin/slideshow')
@admin_required
def admin_slideshow():
    photos = get_photos(sort_by='upload')
    # 最新10投稿が2レーン目、11枚目~30枚目が1レーン目
    recent_photos = photos[:10]  # 最新10枚
    top_photos = photos[10:30] if len(photos) > 10 else []  # 11枚目~30枚目
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
@app.route('/admin/delete/<path:photo_identifier>', methods=['POST'])
@admin_required
def delete_photo(photo_identifier):
    filename = None
    photos = get_photos()
    if photo_identifier in photos:
        filename = photo_identifier
    else:
        stored_map = getattr(app, '_photo_uuid_map', {})
        for candidate, uuid_value in stored_map.items():
            if uuid_value == photo_identifier:
                filename = candidate
                break

    if filename and filename in photos:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            if getattr(app, '_photo_uuid_map', None):
                app._photo_uuid_map.pop(filename, None)
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


@app.route('/admin/result-config', methods=['POST'])
@admin_required
def update_result_config():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({'success': False, 'error': '無効なリクエストです'}), 400

    categories_payload = payload.get('categories')
    order_payload = payload.get('order') or []

    if not isinstance(categories_payload, list) or len(categories_payload) != len(DEFAULT_CATEGORIES):
        return jsonify({'success': False, 'error': 'カテゴリ情報が正しくありません'}), 400

    categories_map = {item.get('id'): item for item in categories_payload if isinstance(item, dict) and item.get('id')}

    normalized_categories = []
    for default in DEFAULT_CATEGORIES:
        incoming = categories_map.get(default['id'], {})
        name = (incoming.get('name') or default['name']).strip()
        photo = incoming.get('photo') or None
        normalized_categories.append({
            'id': default['id'],
            'name': name if name else default['name'],
            'photo': photo
        })

    desired_order = []
    for cat_id in order_payload:
        if isinstance(cat_id, str) and cat_id in {cat['id'] for cat in normalized_categories} and cat_id not in desired_order:
            desired_order.append(cat_id)
    for cat in normalized_categories:
        if cat['id'] not in desired_order:
            desired_order.append(cat['id'])

    save_result_config({'categories': normalized_categories, 'order': desired_order})
    return jsonify({'success': True})


@app.route('/result')
def result_page():
    config = load_result_config()
    categories_by_id = {cat['id']: cat for cat in config['categories']}
    ordered_categories = []
    for cat_id in config['order']:
        cat = categories_by_id.get(cat_id)
        if not cat:
            continue
        category_data = {
            'id': cat['id'],
            'name': cat['name'],
            'photo': cat.get('photo'),
            'photo_url': url_for('serve_upload', filename=cat['photo']) if cat.get('photo') else None
        }
        ordered_categories.append(category_data)

    return render_template('result.html', categories=ordered_categories)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0') 