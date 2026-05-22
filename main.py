from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db")
THRESHOLD = 0.82

os.makedirs(DB_PATH, exist_ok=True)

print(f"✅ DB_PATH: {DB_PATH}")
print(f"✅ Bazadagi rasmlar: {os.listdir(DB_PATH)}")

app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


def clear_cache():
    for pattern in ["*.pkl", "representations_*.pkl"]:
        for f in glob.glob(os.path.join(DB_PATH, pattern)):
            try:
                os.remove(f)
            except:
                pass


def preprocess_image(img_path: str) -> str:
    try:
        img = cv2.imread(img_path)
        if img is None:
            return img_path

        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        elif max(h, w) < 160:
            scale = 320 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        kernel = np.array([[0, -0.5, 0],
                           [-0.5, 3, -0.5],
                           [0, -0.5, 0]])
        img = cv2.filter2D(img, -1, kernel)

        processed_path = os.path.join(BASE_DIR, "temp_processed.jpg")
        cv2.imwrite(processed_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return processed_path

    except Exception as e:
        print(f"[PREPROCESS] Xato: {e}")
        return img_path


def find_best_match(results):
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

    return best_match, best_dist


@app.post("/verify")
async def verify_face(file: UploadFile = File(...)):
    temp_file = os.path.join(BASE_DIR, "temp_capture.jpg")
    processed_file = None

    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        processed_file = preprocess_image(temp_file)
        clear_cache()

        results = DeepFace.find(
            img_path=processed_file,
            db_path=DB_PATH,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            detector_backend='skip',
            silent=True
        )

        best_match, best_dist = find_best_match(results)
        print(f"[DEBUG] Masofa: {best_dist:.4f} | Threshold: {THRESHOLD}")

        if best_match is not None and best_dist < THRESHOLD:
            full_path = best_match['identity']
            name = os.path.basename(full_path).split('.')[0]
            confidence = round((1 - best_dist / THRESHOLD) * 100, 1)
            return {
                "status": "success",
                "user": name,
                "confidence": f"{confidence}%",
                "distance": round(best_dist, 4)
            }

        return {
            "status": "error",
            "message": "Yuz tanilmadi",
            "distance": round(best_dist, 4) if best_dist != float('inf') else None
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "error", "message": str(e)}

    finally:
        for f in [temp_file, processed_file]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass


@app.get("/db/list")
async def list_db():
    files = [f for f in os.listdir(DB_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    names = [os.path.splitext(f)[0] for f in files]
    return {"users": names, "count": len(names)}


@app.post("/db/add")
async def add_to_db(name: str, file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        save_path = os.path.join(DB_PATH, f"{name}{ext}")
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        clear_cache()
        return {"status": "success", "message": f"{name} bazaga qo'shildi"}
    except Exception as e:
        return {"status": "error", "message": str(e)}