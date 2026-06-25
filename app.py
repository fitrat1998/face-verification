"""
Moodle uchun Face Recognition API servisi (TEST/DEMO versiyasi)
================================================================
Bu versiya OpenCV (Haar Cascade + LBPH) asosida ishlaydi - `dlib`
kompilyatsiya talab qilmaydi, shuning uchun tez o'rnatiladi va
test qilish uchun ideal.

DIQQAT: LBPH dlib/face_recognition kutubxonasiga nisbatan ANCHA
KAMROQ ANIQ. Bu versiya faqat:
  1) Arxitekturani sinab ko'rish (Moodle <-> API <-> login oqimi)
  2) Demo/prototip sifatida ko'rsatish
uchun mos. Productionga chiqishdan oldin pastdagi "PRODUCTIONGA
O'TISH" bo'limini o'qing.

O'rnatish (test uchun yengil):
    pip install flask flask-cors opencv-contrib-python pillow numpy

Ishga tushirish:
    python app.py
    (default: http://0.0.0.0:5001)
"""

import base64
import io
import os

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)  # Test paytida brauzerdan to'g'ridan-to'g'ri so'rov yuborish uchun


@app.route("/")
def serve_test_page():
    """http://localhost:5001/ ochilganda test_webcam.html ko'rsatiladi."""
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "test_webcam.html")

# Foydalanuvchilarning yuz rasmlari saqlanadigan papka
FACES_DIR = "face_data"
os.makedirs(FACES_DIR, exist_ok=True)

# OpenCV'ning tayyor yuz aniqlash modeli (Haar Cascade)
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# LBPH solishtirish uchun "ishonch masofasi" chegarasi.
# Past qiymat = qattiqroq, lekin kamroq distance kerak bo'lishi mumkin.
# Test orqali o'zingiz uchun mos qiymatni topasiz (odatda 50-80 oralig'i).
LBPH_CONFIDENCE_THRESHOLD = 70


def _decode_base64_image(base64_string):
    """Base64 stringni OpenCV grayscale numpy arrayga o'giradi"""
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    rgb_array = np.array(img)
    gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
    return gray


def _detect_face(gray_image):
    """Rasmda yuzni topib, standart o'lchamga keltiradi (LBPH uchun shart)"""
    faces = FACE_CASCADE.detectMultiScale(
        gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    return faces


def _crop_and_resize_face(gray_image, face_box, size=(200, 200)):
    x, y, w, h = face_box
    face_crop = gray_image[y:y + h, x:x + w]
    return cv2.resize(face_crop, size)


def _user_dir(user_id):
    path = os.path.join(FACES_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


def _model_path(user_id):
    return os.path.join(_user_dir(user_id), "model.yml")


@app.route("/register", methods=["POST"])
def register_face():
    """
    Foydalanuvchi yuzini ro'yxatdan o'tkazish.
    Body: { "user_id": "123", "image": "data:image/jpeg;base64,..." }

    Eslatma: aniqlikni oshirish uchun bir nechta rasm jamlab,
    keyin /train chaqirish tavsiya etiladi (pastda).
    """
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    image_b64 = data.get("image")

    if not user_id or not image_b64:
        return jsonify({"success": False, "error": "user_id va image majburiy"}), 400

    try:
        gray = _decode_base64_image(image_b64)
    except Exception as e:
        return jsonify({"success": False, "error": f"Rasmni o'qishda xato: {e}"}), 400

    faces = _detect_face(gray)
    if len(faces) == 0:
        return jsonify({"success": False, "error": "Yuz topilmadi. Yorug'roq joyda, kameraga to'g'ri qarab urinib ko'ring."}), 400
    if len(faces) > 1:
        return jsonify({"success": False, "error": "Bir nechta yuz aniqlandi. Kadrda faqat bitta odam bo'lsin."}), 400

    face_img = _crop_and_resize_face(gray, faces[0])

    # Shu foydalanuvchining barcha namuna rasmlarini saqlaymiz.
    user_dir = _user_dir(user_id)
    existing = [f for f in os.listdir(user_dir) if f.startswith("sample_")]
    sample_path = os.path.join(user_dir, f"sample_{len(existing)}.png")
    cv2.imwrite(sample_path, face_img)

    # Mavjud namunalar asosida modelni (qayta) o'qitamiz.
    samples = []
    labels = []
    for fname in os.listdir(user_dir):
        if fname.startswith("sample_"):
            img = cv2.imread(os.path.join(user_dir, fname), cv2.IMREAD_GRAYSCALE)
            samples.append(img)
            labels.append(0)  # bitta foydalanuvchi uchun bitta model, label doim 0

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(samples, np.array(labels))
    recognizer.save(_model_path(user_id))

    return jsonify({
        "success": True,
        "message": f"Yuz saqlandi ({len(samples)}-namuna). Yaxshi natija uchun kamida 5 ta turli burchakdan rasm yuborish tavsiya etiladi.",
        "samples_count": len(samples),
    })


@app.route("/verify", methods=["POST"])
def verify_face():
    """
    Login paytida yuzni tekshirish.
    Body: { "user_id": "123", "image": "data:image/jpeg;base64,..." }
    Javob: { "success": true, "match": true/false, "confidence": 0.92 }
    """
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    image_b64 = data.get("image")

    if not user_id or not image_b64:
        return jsonify({"success": False, "error": "user_id va image majburiy"}), 400

    model_path = _model_path(user_id)
    if not os.path.exists(model_path):
        return jsonify({"success": False, "error": "Bu foydalanuvchi uchun ro'yxatdan o'tgan yuz topilmadi"}), 404

    try:
        gray = _decode_base64_image(image_b64)
    except Exception as e:
        return jsonify({"success": False, "error": f"Rasmni o'qishda xato: {e}"}), 400

    faces = _detect_face(gray)
    if len(faces) == 0:
        return jsonify({"success": False, "error": "Yuz topilmadi"}), 400

    face_img = _crop_and_resize_face(gray, faces[0])

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(model_path)
    label, lbph_distance = recognizer.predict(face_img)

    is_match = lbph_distance <= LBPH_CONFIDENCE_THRESHOLD
    # LBPH'da distance past = o'xshashroq. Buni 0-1 "ishonch"ga o'giramiz.
    confidence = round(max(0.0, 1 - (lbph_distance / 100)), 4)

    return jsonify({
        "success": True,
        "match": bool(is_match),
        "confidence": confidence,
        "distance": round(float(lbph_distance), 2),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "engine": "opencv-lbph (test mode)"})


if __name__ == "__main__":
    # ============================================================
    # PRODUCTIONGA O'TISH:
    # LBPH yorug'lik, burchak, yosh o'zgarishiga sezgir va xato
    # qabul qilish (false accept) darajasi yuqori bo'lishi mumkin.
    # Real foydalanish uchun:
    #   1) face_recognition (dlib) yoki
    #   2) InsightFace / ArcFace (chuqur o'rganish asosida, ancha aniq)
    # kutubxonasiga o'tish tavsiya etiladi. Ular ko'proq resurs va
    # to'g'ri o'rnatish (CMake, build-essential) talab qiladi, shuning
    # uchun avval shu test versiyasida butun oqimni (Moodle -> API ->
    # login) ishga tushirib, keyin "miya"sini almashtirish to'g'riroq.
    #
    # Productionda HTTPS orqali ishlatish SHART (kamera/biometrik
    # ma'lumot ochiq HTTP orqali yuborilmasin).
    # ============================================================
    app.run(host="0.0.0.0", port=5001, debug=False)
