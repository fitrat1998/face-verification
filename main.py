from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os
import shutil
import glob
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "db"


def clear_cache():
    """Eski kesh fayllarni tozalash"""
    for f in glob.glob(os.path.join(DB_PATH, "*.pkl")):
        try:
            os.remove(f)
        except:
            pass


@app.post("/verify")
async def verify_face(file: UploadFile = File(...)):
    temp_file = "temp_capture.jpg"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        clear_cache()

        results = DeepFace.find(
            img_path=temp_file,
            db_path=DB_PATH,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            detector_backend='opencv',
            silent=True
        )

        # Natijalarni tekshirish
        if isinstance(results, list) and len(results) > 0 and not results[0].empty:
            match = results[0].iloc[0]

            # Dinamik ustun qidirish (Facenet512_cosine yoki shunchaki cosine)
            cols = match.index.tolist()
            dist_col = next((c for c in cols if 'cosine' in c.lower() or 'distance' in c.lower()), None)

            if dist_col:
                dist = float(match[dist_col])
                print(f"[DEBUG] Masofa: {dist}")  # Terminalda raqamni ko'rib olasiz

                # MUHIM: Sizda farq katta chiqayotgani uchun 0.60 ni 0.82 ga ko'tardim
                # Chunki veb-kamera va studio rasmi farqi odatda 0.75-0.80 atrofida bo'ladi
                threshold = 0.82

                if dist < threshold:
                    full_path = match['identity']
                    name = os.path.basename(full_path).split('.')[0]
                    confidence = round((1 - dist) * 100, 2)

                    return {
                        "status": "success",
                        "user": name,
                        "confidence": f"{confidence}%",
                        "distance": round(dist, 4)
                    }

        return {"status": "error", "message": "Yuz bazadagi rasmga mos kelmadi!"}

    except Exception as e:
        print(f"Xato: {e}")
        return {"status": "error", "message": f"Tahlil xatosi: {str(e)}"}