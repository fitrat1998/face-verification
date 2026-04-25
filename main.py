from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
import os
import shutil
import uvicorn
import glob

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "db"

def clear_cache():
    """DeepFace yaratgan kesh fayllarni tozalash (xatolikni oldini oladi)"""
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

        # Facenet512 va Cosine kombinatsiyasi uchun 0.70-0.80 - bu "yumshoq" rejim
        results = DeepFace.find(
            img_path=temp_file,
            db_path=DB_PATH,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            silent=True
        )

        # DeepFace.find natijasi list qaytaradi, shuning uchun results[0] ni tekshiramiz
        if isinstance(results, list) and len(results) > 0 and not results[0].empty:
            match = results[0].iloc[0]
            dist = float(match['Facenet512_cosine'])

            print(f"\n[DEBUG] Aniqlangan masofa: {dist}")

            # 0.75 - veb-kamera uchun eng optimal chegara
            if dist < 0.75:
                # 'identity' ustunidan fayl nomini olish
                identity_path = match['identity']
                name = os.path.basename(identity_path).split('.')[0]
                confidence = round((1 - dist) * 100, 2)
                return {"status": "success", "user": name, "confidence": f"{confidence}%"}

            return {"status": "error", "message": f"Mos kelmadi (Dist: {round(dist, 2)})"}

        return {"status": "error", "message": "Yuz bazadan topilmadi"}

    except Exception as e:
        print(f"[XATO] {str(e)}")
        return {"status": "error", "message": f"Server xatosi: {str(e)}"}