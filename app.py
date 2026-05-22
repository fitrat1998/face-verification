from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
import json
import re
import secrets
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

KNOWN_FACES_DIR = "known_faces"
USERS_FILE = "users.json"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def decode_image(data_url):
    if ',' in data_url:
        data_url = data_url.split(',')[1]
    img_bytes = base64.b64decode(data_url)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def extract_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
    pad = 20
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img.shape[1], x + w + pad)
    y2 = min(img.shape[0], y + h + pad)
    face_img = img[y1:y2, x1:x2]
    face_gray = gray[y1:y2, x1:x2]
    return cv2.resize(face_img, (128, 128)), cv2.resize(face_gray, (128, 128))

def get_face_descriptor(face_gray):
    orb = cv2.ORB_create(nfeatures=500)
    kp, des = orb.detectAndCompute(face_gray, None)
    if des is None:
        return None
    
    lbph = cv2.face.LBPHFaceRecognizer_create()
    descriptor = cv2.resize(face_gray, (64, 64)).flatten().astype(np.float32)
    descriptor = descriptor / 255.0
    return descriptor

def compare_faces(desc1, desc2):
    if desc1 is None or desc2 is None:
        return 0.0
    d1 = np.array(desc1, dtype=np.float32)
    d2 = np.array(desc2, dtype=np.float32)
    dot = np.dot(d1, d2)
    norm = np.linalg.norm(d1) * np.linalg.norm(d2)
    if norm == 0:
        return 0.0
    similarity = dot / norm
    return float(similarity)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    image_data = data.get('image', '')
    
    if not username:
        return jsonify({'success': False, 'message': 'Ism kiritilmagan'}), 400
    
    if not re.match(r'^[a-zA-Z0-9_\u0400-\u04FF]{2,30}$', username):
        return jsonify({'success': False, 'message': 'Ism 2-30 ta harf bo\'lishi kerak'}), 400
    
    img = decode_image(image_data)
    if img is None:
        return jsonify({'success': False, 'message': 'Rasm yuklashda xato'}), 400
    
    face_img, face_gray = extract_face(img)
    if face_img is None:
        return jsonify({'success': False, 'message': 'Yuz topilmadi! Kameraga to\'g\'ri qarang'}), 400
    
    descriptor = get_face_descriptor(face_gray)
    if descriptor is None:
        return jsonify({'success': False, 'message': 'Yuz tahlil qilib bo\'lmadi'}), 400
    
    users = load_users()
    if username in users:
        return jsonify({'success': False, 'message': 'Bu ism allaqachon ro\'yxatdan o\'tgan'}), 400
    
    face_path = os.path.join(KNOWN_FACES_DIR, f'{username}.jpg')
    cv2.imwrite(face_path, face_img)
    
    users[username] = {
        'descriptor': descriptor.tolist(),
        'face_path': face_path
    }
    save_users(users)
    
    return jsonify({
        'success': True,
        'message': f'{username} muvaffaqiyatli ro\'yxatdan o\'tdi!'
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    image_data = data.get('image', '')
    
    img = decode_image(image_data)
    if img is None:
        return jsonify({'success': False, 'message': 'Rasm yuklashda xato'}), 400
    
    face_img, face_gray = extract_face(img)
    if face_img is None:
        return jsonify({'success': False, 'message': 'Yuz topilmadi! Kameraga to\'g\'ri qarang'}), 400
    
    descriptor = get_face_descriptor(face_gray)
    if descriptor is None:
        return jsonify({'success': False, 'message': 'Yuz tahlil qilib bo\'lmadi'}), 400
    
    users = load_users()
    if not users:
        return jsonify({'success': False, 'message': 'Hech kim ro\'yxatdan o\'tmagan'}), 400
    
    best_match = None
    best_score = 0.0
    THRESHOLD = 0.92
    
    for username, user_data in users.items():
        stored_desc = np.array(user_data['descriptor'], dtype=np.float32)
        score = compare_faces(descriptor, stored_desc)
        if score > best_score:
            best_score = score
            best_match = username
    
    if best_score >= THRESHOLD:
        session['user'] = best_match
        return jsonify({
            'success': True,
            'message': f'Xush kelibsiz, {best_match}!',
            'username': best_match,
            'confidence': round(best_score * 100, 1)
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Yuz tanilmadi yoki ruxsat yo\'q',
            'confidence': round(best_score * 100, 1)
        })

@app.route('/api/detect', methods=['POST'])
def detect():
    data = request.json
    image_data = data.get('image', '')
    
    img = decode_image(image_data)
    if img is None:
        return jsonify({'detected': False})
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    
    return jsonify({
        'detected': len(faces) > 0,
        'count': len(faces)
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    users = load_users()
    return jsonify({'users': list(users.keys()), 'count': len(users)})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("Face Auth server starting on http://localhost:5050")
    app.run(debug=True, port=5050, host='0.0.0.0')
