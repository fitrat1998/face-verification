from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
import json
import re
import secrets

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
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def resize_if_large(img, max_width=640):
    h, w = img.shape[:2]
    if w > max_width:
        scale = max_width / w
        img = cv2.resize(img, (max_width, int(h * scale)))
    return img

def find_faces(gray):
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
    if len(faces) == 0:
        faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(20, 20))
    if len(faces) == 0:
        faces = face_cascade.detectMultiScale(gray, 1.02, 2, minSize=(15, 15))
    return faces

def extract_face(img):
    img = resize_if_large(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = find_faces(gray)
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

def compute_lbp(gray):
    center = gray[1:-1, 1:-1].astype(np.float32)
    lbp = np.zeros_like(center)
    neighbors = [
        gray[0:-2, 0:-2], gray[0:-2, 1:-1], gray[0:-2, 2:],
        gray[1:-1, 2:],   gray[2:,   2:],   gray[2:,   1:-1],
        gray[2:,   0:-2], gray[1:-1, 0:-2]
    ]
    for i, nb in enumerate(neighbors):
        lbp += ((nb.astype(np.float32) >= center) * (2**i))
    lbp_flat = cv2.resize(lbp, (32, 16)).flatten()
    return lbp_flat / 255.0

def get_face_descriptor(face_gray):
    equalized = cv2.equalizeHist(face_gray)
    pixel_desc = equalized.flatten().astype(np.float32) / 255.0
    lbp = compute_lbp(equalized)
    gx = cv2.Sobel(equalized, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(equalized, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mag_small = cv2.resize(mag, (32, 32)).flatten()
    mag_norm = mag_small / (mag_small.max() + 1e-6)
    return np.concatenate([pixel_desc[:2048], lbp[:512], mag_norm])

def augment_face(face_gray):
    variants = [face_gray]
    h, w = face_gray.shape
    for angle in [-15, -10, -5, 5, 10, 15]:
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        rotated = cv2.warpAffine(face_gray, M, (w, h))
        variants.append(rotated)
    for gamma in [0.6, 0.8, 1.2, 1.5]:
        table = np.array([((i / 255.0) ** (1.0/gamma)) * 255 for i in range(256)], dtype=np.uint8)
        variants.append(cv2.LUT(face_gray, table))
    variants.append(cv2.flip(face_gray, 1))
    for scale in [0.85, 0.92, 1.08, 1.15]:
        scaled = cv2.resize(face_gray, None, fx=scale, fy=scale)
        scaled = cv2.resize(scaled, (128, 128))
        variants.append(scaled)
    # Blur (noaniq kamera)
    variants.append(cv2.GaussianBlur(face_gray, (3, 3), 0))
    return variants

def compare_faces(desc1, desc2):
    if desc1 is None or desc2 is None:
        return 0.0
    d1 = np.array(desc1, dtype=np.float32)
    d2 = np.array(desc2, dtype=np.float32)
    if len(d1) != len(d2):
        return 0.0
    dot = np.dot(d1, d2)
    norm = np.linalg.norm(d1) * np.linalg.norm(d2)
    if norm == 0:
        return 0.0
    return float(dot / norm)

def best_score_against_user(descriptor, user_data):
    descriptors = user_data.get('descriptors', [])
    if not descriptors:
        old_desc = user_data.get('descriptor')
        if old_desc:
            descriptors = [old_desc]
    best = 0.0
    for stored_desc in descriptors:
        score = compare_faces(descriptor, stored_desc)
        if score > best:
            best = score
    return best

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
        return jsonify({'success': False, 'message': "Ism 2-30 ta harf bo'lishi kerak"}), 400

    img = decode_image(image_data)
    if img is None:
        return jsonify({'success': False, 'message': 'Rasm yuklashda xato'}), 400

    face_img, face_gray = extract_face(img)
    if face_img is None:
        return jsonify({'success': False, 'message': "Yuz topilmadi! Kameraga to'g'ri qarang"}), 400

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'message': "Bu ism allaqachon ro'yxatdan o'tgan"}), 400

    variants = augment_face(face_gray)
    descriptors = []
    for v in variants:
        desc = get_face_descriptor(v)
        if desc is not None:
            descriptors.append(desc.tolist())

    face_path = os.path.join(KNOWN_FACES_DIR, f'{username}.jpg')
    cv2.imwrite(face_path, face_img)

    users[username] = {
        'descriptors': descriptors,
        'face_path': face_path
    }
    save_users(users)

    return jsonify({
        'success': True,
        'message': f"{username} muvaffaqiyatli ro'yxatdan o'tdi! ({len(descriptors)} variant saqlandi)"
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
        return jsonify({'success': False, 'message': "Yuz topilmadi! Kameraga to'g'ri qarang"}), 400

    login_variants = augment_face(face_gray)
    login_descriptors = [get_face_descriptor(v) for v in login_variants]
    login_descriptors = [d for d in login_descriptors if d is not None]

    users = load_users()
    if not users:
        return jsonify({'success': False, 'message': "Hech kim ro'yxatdan o'tmagan"}), 400

    THRESHOLD = 0.90
    best_match = None
    best_score = 0.0

    for username, user_data in users.items():
        for login_desc in login_descriptors:
            score = best_score_against_user(login_desc, user_data)
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
            'message': f"Yuz tanilmadi (moslik: {round(best_score*100,1)}%)",
            'confidence': round(best_score * 100, 1)
        })

@app.route('/api/detect', methods=['POST'])
def detect():
    data = request.json
    image_data = data.get('image', '')
    img = decode_image(image_data)
    if img is None:
        return jsonify({'detected': False})
    img = resize_if_large(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = find_faces(gray)
    return jsonify({'detected': len(faces) > 0, 'count': len(faces)})

@app.route('/api/users', methods=['GET'])
def get_users():
    users = load_users()
    return jsonify({'users': list(users.keys()), 'count': len(users)})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("Face Auth server starting on http://0.0.0.0:5050")
    app.run(debug=False, port=5050, host='0.0.0.0')