from flask import Flask, request, render_template, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# アップロードフォルダが存在しない場合は作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_photos():
    """写真のリストを取得"""
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        return []
    photos = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    photos.sort()
    return photos

@app.route('/')
def upload_xge():
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

# 管理者用スライドショールートの追加
@app.route('/admin/slideshow')
def admin_slideshow():
    photos = get_photos()
    return render_template('admin_slideshow.html', photos=photos)

if __name__ == '__main__':
    # デバッグモードを有効にする場合は、以下のコメントを外してください
    # app.run(debug=True)
    app.run() 