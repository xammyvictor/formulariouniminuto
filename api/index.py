import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

GOOGLE_SHEETS_WEBHOOK_URL = os.environ.get(
    "GOOGLE_SHEETS_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbwv4r18zK1cN3zx4BXzP6s6xEt83Xe-NnFpjCoqlZci-v4v3rWN1m-AQ_YzPMz25d4X9g/exec"
)

app = FastAPI(title="API Encuesta Regional UNIMINUTO", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def health_check():
    return {"status": "online", "server_time": datetime.utcnow().isoformat()}

@app.post("/api/submit")
async def receive_survey(request: Request):
    try:
        data = await request.json()
        if not data.get("p3_perfil"):
            raise HTTPException(status_code=400, detail="El perfil es obligatorio.")
        
        data["timestamp_utc"] = datetime.utcnow().isoformat()

        if GOOGLE_SHEETS_WEBHOOK_URL and "script.google.com" in GOOGLE_SHEETS_WEBHOOK_URL:
            try:
                requests.post(
                    GOOGLE_SHEETS_WEBHOOK_URL,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=True,
                    timeout=15
                )
            except Exception as e_sheet:
                print(f"[ERROR SHEETS POST]: {str(e_sheet)}")

        return {"success": True, "message": "Respuesta guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_stats():
    try:
        res = requests.get(GOOGLE_SHEETS_WEBHOOK_URL, allow_redirects=True, timeout=15)
        raw_data = res.json() if res.status_code == 200 else []
        return {"success": True, "data": raw_data}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}
