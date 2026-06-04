from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
import json
import re
import secrets
import urllib.request
import tempfile

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

KNOWN_FACES_DIR = "known_faces"
USERS_FILE = "users.json"
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Ko'z landmarklari
LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

ALL_POINTS = list(set([
    1, 4, 5, 195, 197, 6, 168, 8, 9,
    33, 133, 362, 263,
    61, 291, 13, 14, 17, 0,
    70, 63, 105, 66, 107,
    336, 296, 334, 293, 300,
    234, 454, 152, 10,
    338, 297, 332, 284, 251, 389, 356,
    323, 361, 288, 397, 365, 379, 378,
    400, 377, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 127, 162, 21, 54
]))

# Model yuklab olish
MODEL_PATH = os.path.join(tempfile.gettempdir(), "face_landmarker.task")
if not os.path.exists(MODEL_PATH):
    print("Downloading face_landmarker model (~30MB)...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        MODEL_PATH
    )
    print("Model downloaded!")

base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
options = mp_vision.FaceLandmarkerOptions(
    base_options=base_options,
    num_faces=1,
    min_face_detection_confidence=0.4,
    min_face_presence_confidence=0.4,
)
landmarker = mp_vision.FaceLandmarker.create_from_options(options)
print("MediaPipe FaceLandmarker ready!")

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

def get_landmarks(img):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    result = landmarker.detect(mp_image)
    if result.face_landmarks:
        return result.face_landmarks[0]
    return None

def eye_aspect_ratio(landmarks, eye_points, w, h):
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in eye_points]
    v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    h1 = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    return float((v1 + v2) / (2.0 * h1)) if h1 > 0 else 0.0

def get_face_descriptor(img):
    img = resize_if_large(img)
    h, w = img.shape[:2]
    landmarks = get_landmarks(img)
    if landmarks is None:
        return None, 0.0

    left_ear  = eye_aspect_ratio(landmarks, LEFT_EYE,  w, h)
    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE, w, h)
    ear = (left_ear + right_ear) / 2.0

    nose = landmarks[4]
    cx, cy = nose.x, nose.y
    face_width = abs(landmarks[454].x - landmarks[234].x) + 1e-6

    coords = []
    for idx in ALL_POINTS:
        lm = landmarks[idx]
        coords.append((lm.x - cx) / face_width)
        coords.append((lm.y - cy) / face_width)

    return np.array(coords, dtype=np.float32), ear

def augment_and_describe(img):
    h, w = img.shape[:2]
    variants = [img]
    for gamma in [0.75, 1.25]:
        table = np.array([((i/255.0)**(1.0/gamma))*255 for i in range(256)], dtype=np.uint8)
        variants.append(cv2.LUT(img, table))
    for angle in [-8, 8]:
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        variants.append(cv2.warpAffine(img, M, (w, h)))
    descriptors = []
    for v in variants:
        desc, _ = get_face_descriptor(v)
        if desc is not None:
            descriptors.append(desc.tolist())
    return descriptors

def compare_descriptors(d1, d2):
    d1 = np.array(d1, dtype=np.float32)
    d2 = np.array(d2, dtype=np.float32)
    if len(d1) != len(d2):
        return 0.0
    dot  = np.dot(d1, d2)
    norm = np.linalg.norm(d1) * np.linalg.norm(d2)
    return float(dot / norm) if norm > 0 else 0.0

def best_match_score(descriptor, user_data):
    best = 0.0
    for stored in user_data.get('descriptors', []):
        s = compare_descriptors(descriptor, stored)
        if s > best:
            best = s
    return best

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect', methods=['POST'])
def detect():
    img = decode_image(request.json.get('image', ''))
    if img is None:
        return jsonify({'detected': False, 'eyes': 0})
    img = resize_if_large(img)
    desc, ear = get_face_descriptor(img)
    if desc is None:
        return jsonify({'detected': False, 'eyes': 0})
    return jsonify({
        'detected': True,
        'eyes': 1 if ear > 0.18 else 0,
        'ear': round(ear, 3),
        'ready': ear > 0.18
    })

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'success': False, 'message': 'Ism kiritilmagan'}), 400
    if not re.match(r'^[a-zA-Z0-9_\u0400-\u04FF]{2,30}$', username):
        return jsonify({'success': False, 'message': "Ism 2-30 ta harf bo'lishi kerak"}), 400

    img = decode_image(data.get('image', ''))
    if img is None:
        return jsonify({'success': False, 'message': 'Rasm yuklashda xato'}), 400
    img = resize_if_large(img)

    desc, ear = get_face_descriptor(img)
    if desc is None:
        return jsonify({'success': False, 'message': "Yuz topilmadi! Kameraga to'g'ri qarang"}), 400
    if ear < 0.15:
        return jsonify({'success': False, 'message': "Ko'zlaringiz ko'rinmayapti! Yuzingizni to'liq ko'rsating"}), 400

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'message': "Bu ism allaqachon ro'yxatdan o'tgan"}), 400

    descriptors = augment_and_describe(img)
    if not descriptors:
        return jsonify({'success': False, 'message': "Yuz tahlil qilib bo'lmadi"}), 400

    face_path = os.path.join(KNOWN_FACES_DIR, f'{username}.jpg')
    cv2.imwrite(face_path, img)
    users[username] = {'descriptors': descriptors, 'face_path': face_path}
    save_users(users)

    return jsonify({'success': True, 'message': f"{username} muvaffaqiyatli ro'yxatdan o'tdi! ({len(descriptors)} variant)"})

@app.route('/api/login', methods=['POST'])
def login():
    img = decode_image(request.json.get('image', ''))
    if img is None:
        return jsonify({'success': False, 'message': 'Rasm yuklashda xato'}), 400
    img = resize_if_large(img)

    desc, ear = get_face_descriptor(img)
    if desc is None:
        return jsonify({'success': False, 'message': "Yuz topilmadi! Kameraga to'g'ri qarang"}), 400
    if ear < 0.15:
        return jsonify({'success': False, 'message': "Yuzingiz yopiq! Ko'zlaringizni ko'rsating", 'confidence': 0}), 400

    users = load_users()
    if not users:
        return jsonify({'success': False, 'message': "Hech kim ro'yxatdan o'tmagan"}), 400

    login_descs = augment_and_describe(img)
    THRESHOLD = 0.985
    best_match = None
    best_score = 0.0

    for uname, udata in users.items():
        for ld in login_descs:
            score = best_match_score(ld, udata)
            if score > best_score:
                best_score = score
                best_match = uname

    if best_score >= THRESHOLD:
        session['user'] = best_match
        return jsonify({'success': True, 'message': f'Xush kelibsiz, {best_match}!',
                        'username': best_match, 'confidence': round(best_score * 100, 1)})
    else:
        return jsonify({'success': False,
                        'message': f"Yuz tanilmadi (moslik: {round(best_score*100,1)}%)",
                        'confidence': round(best_score * 100, 1)})

@app.route('/api/users', methods=['GET'])
def get_users():
    users = load_users()
    return jsonify({'users': list(users.keys()), 'count': len(users)})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("Face Auth (MediaPipe Tasks) starting on http://0.0.0.0:5050")
    app.run(debug=False, port=5050, host='0.0.0.0')