from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from deepface import DeepFace
import os, shutil, glob

app = FastAPI()

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        })
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

DB_PATH = "db"

def clear_cache():
    for f in glob.glob(os.path.join(DB_PATH, "*.pkl")):
        try: os.remove(f)
        except: pass

@app.post("/verify")
async def verify_face(file: UploadFile = File(...)):
    temp_file = "temp_capture.jpg"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        clear_cache()
        results = DeepFace.find(
            img_path=temp_file, db_path=DB_PATH,
            model_name="Facenet512", distance_metric="cosine",
            enforce_detection=False, refresh_database=True,
            detector_backend="opencv", silent=True
        )
        if isinstance(results, list) and len(results) > 0 and not results[0].empty:
            match = results[0].iloc[0]
            cols = match.index.tolist()
            dist_col = next((c for c in cols if "cosine" in c.lower() or "distance" in c.lower()), None)
            if dist_col:
                dist = float(match[dist_col])
                print(f"[DEBUG] Masofa: {dist}")
                if dist < 0.82:
                    name = os.path.basename(match["identity"]).split(".")[0]
                    return JSONResponse({"status": "success", "user": name,
                                        "confidence": f"{round((1-dist)*100,2)}%",
                                        "distance": round(dist, 4)})
        return JSONResponse({"status": "error", "message": "Yuz mos kelmadi!"})
    except Exception as e:
        print(f"Xato: {e}")
        return JSONResponse({"status": "error", "message": str(e)})