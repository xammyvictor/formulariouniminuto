import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# URL de conexión con tu Google Sheets
GOOGLE_SHEETS_WEBHOOK_URL = os.environ.get(
    "GOOGLE_SHEETS_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbwv4r18zK1cN3zx4BXzP6s6xEt83Xe-NnFpjCoqlZci-v4v3rWN1m-AQ_YzPMz25d4X9g/exec"
)

app = FastAPI(
    title="API Encuesta Regional UNIMINUTO",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def health_check():
    return {
        "status": "online",
        "service": "UNIMINUTO Regional Survey Backend",
        "server_time": datetime.utcnow().isoformat()
    }

@app.post("/api/submit")
async def receive_survey(request: Request):
    try:
        data = await request.json()
        
        if not data.get("p3_perfil"):
            raise HTTPException(status_code=400, detail="El perfil es obligatorio.")
        
        data["timestamp_utc"] = datetime.utcnow().isoformat()
        data["client_ip"] = request.client.host if request.client else "unknown"

        # Envío directo y almacenamiento en Google Sheets
        if GOOGLE_SHEETS_WEBHOOK_URL and "script.google.com" in GOOGLE_SHEETS_WEBHOOK_URL:
            try:
                sheet_res = requests.post(
                    GOOGLE_SHEETS_WEBHOOK_URL,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=True,
                    timeout=15
                )
                print(f"[GOOGLE SHEETS] Respuesta: {sheet_res.status_code}")
            except Exception as e_sheet:
                print(f"[ERROR SHEETS]: {str(e_sheet)}")

        return {
            "success": True,
            "message": "Respuesta guardada correctamente",
            "received_at": data["timestamp_utc"]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error procesando: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar la encuesta.")
