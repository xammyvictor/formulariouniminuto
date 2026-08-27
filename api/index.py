import os
import requests
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Credenciales de Administrador
ADMIN_USER = "Victor_lozano"
ADMIN_PASS = "753951"
AUTH_TOKEN = "uniminuto_secure_token_v753951"

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

# Endpoint público para guardar encuestas
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

# Endpoint de Login para el Dashboard
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    user = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if user == ADMIN_USER and password == ADMIN_PASS:
        return {"success": True, "token": AUTH_TOKEN, "user": ADMIN_USER}
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

# Endpoint protegido para el Dashboard (requiere token de autenticación)
@app.get("/api/stats")
def get_stats(authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=403, detail="Acceso no autorizado.")

    try:
        res = requests.get(GOOGLE_SHEETS_WEBHOOK_URL, allow_redirects=True, timeout=15)
        raw_data = res.json() if res.status_code == 200 else []
        return {"success": True, "data": raw_data}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}
