from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os
import shutil
import glob
import cv2
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "db"

# ✅ Har xil qurilma uchun moslashtirilgan threshold
# Telefon/past kamera uchun yuqori threshold kerak
THRESHOLD = 0.82  # 0.68 (yaxshi kamera) → 0.82 (telefon/past kamera)


def clear_cache():
    """Kesh fayllarni tozalash"""
    for pattern in ["*.pkl", "representations_*.pkl"]:
        for f in glob.glob(os.path.join(DB_PATH, pattern)):
            try:
                os.remove(f)
            except:
                pass


def preprocess_image(img_path: str) -> str:
    """
    Rasm sifatini yaxshilash:
    - Yorqinlikni normallashtirish (CLAHE)
    - Sharpness oshirish
    - Hajmni standartlashtirish
    Telefon/past kameradan kelgan rasmlar uchun muhim!
    """
    try:
        img = cv2.imread(img_path)
        if img is None:
            return img_path

        # 1. Hajmni optimallashtirish (juda katta yoki kichik bo'lsa)
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        elif max(h, w) < 160:
            scale = 320 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        # 2. CLAHE — yoritilish farqini kamaytirish (telefon uchun eng muhim)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 3. Sharpness — bulaniq telefon rasmlar uchun
        kernel = np.array([[0, -0.5, 0],
                            [-0.5, 3, -0.5],
                            [0, -0.5, 0]])
        img = cv2.filter2D(img, -1, kernel)

        # 4. Qayta saqlash (yuqori sifat)
        processed_path = img_path.replace(".jpg", "_processed.jpg")
        cv2.imwrite(processed_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return processed_path

    except Exception as e:
        print(f"[PREPROCESS] Xato: {e}")
        return img_path  # Xato bo'lsa original rasmni ishlatish


def find_best_match(results):
    """Barcha natijalardan eng yaxshi moslikni topish"""
    best_dist = float('inf')
    best_match = None

    for df in results:
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            cols = row.index.tolist()
            dist_col = next((c for c in cols if 'cosine' in c.lower() or 'distance' in c.lower()), None)
            if dist_col:
                dist = float(row[dist_col])
                if dist < best_dist:
                    best_dist = dist
                    best_match = row
                    best_match_dist_col = dist_col

    return best_match, best_dist


@app.post("/verify")
async def verify_face(file: UploadFile = File(...)):
    temp_file = "temp_capture.jpg"
    processed_file = None

    try:
        # Faylni saqlash
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Preprocessing — telefon/past kamera uchun
        processed_file = preprocess_image(temp_file)
        print(f"[DEBUG] Tahlil qilinayotgan rasm: {processed_file}")

        # Keshni tozalash
        clear_cache()

        # DeepFace tahlili
        results = DeepFace.find(
            img_path=processed_file,
            db_path=DB_PATH,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            detector_backend='opencv',
            silent=True
        )

        # Eng yaxshi moslikni topish
        best_match, best_dist = find_best_match(results)

        print(f"[DEBUG] Eng yaxshi masofa: {best_dist:.4f} (threshold: {THRESHOLD})")

        if best_match is not None and best_dist < THRESHOLD:
            full_path = best_match['identity']
            name = os.path.basename(full_path).split('.')[0]
            confidence = round((1 - best_dist / THRESHOLD) * 100, 1)

            return {
                "status": "success",
                "user": name,
                "confidence": f"{confidence}%",
                "distance": round(best_dist, 4),
                "threshold": THRESHOLD
            }

        # Muvaffaqiyatsiz — debug ma'lumotlari bilan
        return {
            "status": "error",
            "message": "Yuz bazadagi rasmga mos kelmadi!",
            "debug": {
                "best_distance": round(best_dist, 4) if best_dist != float('inf') else None,
                "threshold": THRESHOLD,
                "tip": "distance threshold dan katta" if best_dist != float('inf') else "Hech qanday yuz topilmadi"
            }
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return {
            "status": "error",
            "message": f"Tahlil xatosi: {str(e)}"
        }

    finally:
        # Vaqtinchalik fayllarni o'chirish
        for f in [temp_file, processed_file]:
            if f and os.path.exists(f) and f != temp_file:
                try:
                    os.remove(f)
                except:
                    pass
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


@app.get("/debug/threshold")
async def get_threshold():
    """Joriy threshold ni ko'rish"""
    return {"threshold": THRESHOLD, "model": "Facenet512", "metric": "cosine"}


@app.post("/debug/distance")
async def check_distance(file: UploadFile = File(...)):
    """
    Faqat debug uchun — rasmning barcha masofalarini qaytaradi.
    Threshold ni sozlash uchun ishlatish.
    """
    temp_file = "temp_debug.jpg"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        processed = preprocess_image(temp_file)
        clear_cache()

        results = DeepFace.find(
            img_path=processed,
            db_path=DB_PATH,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            detector_backend='opencv',
            silent=True
        )

        all_distances = []
        for df in results:
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    cols = row.index.tolist()
                    dist_col = next((c for c in cols if 'cosine' in c.lower() or 'distance' in c.lower()), None)
                    if dist_col:
                        all_distances.append({
                            "name": os.path.basename(row['identity']).split('.')[0],
                            "distance": round(float(row[dist_col]), 4)
                        })

        all_distances.sort(key=lambda x: x['distance'])

        return {
            "results": all_distances[:10],
            "current_threshold": THRESHOLD,
            "recommendation": f"Eng yaqin: {all_distances[0]['distance'] if all_distances else 'topilmadi'}"
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        for f in [temp_file, temp_file.replace(".jpg", "_processed.jpg")]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass