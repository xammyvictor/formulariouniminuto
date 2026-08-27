from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import os
import requests

app = FastAPI(
    title="API Encuesta Regional UNIMINUTO",
    version="3.0.0",
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

# Puedes colocar la URL de tu Google Apps Script directamente aquí o como Variable de Entorno en Vercel
GOOGLE_SHEETS_WEBHOOK_URL = os.environ.get(
    "GOOGLE_SHEETS_WEBHOOK_URL", 
    "TU_URL_DE_APPS_SCRIPT_AQUI" # Reemplaza este texto con tu URL terminada en /exec
)

RESPUESTAS_LOCALES = []

@app.get("/api")
def health_check():
    return {
        "status": "online",
        "service": "UNIMINUTO Regional Survey Backend",
        "server_time": datetime.utcnow().isoformat(),
        "google_sheets_connected": GOOGLE_SHEETS_WEBHOOK_URL != "TU_URL_DE_APPS_SCRIPT_AQUI"
    }

@app.post("/api/submit")
async def receive_survey(request: Request):
    try:
        data = await request.json()
        
        if not data.get("p3_perfil"):
            raise HTTPException(status_code=400, detail="El campo de perfil (p3_perfil) es obligatorio.")
        
        # Enriquecer datos con identificadores y fecha
        data["id"] = f"RESP-{int(datetime.utcnow().timestamp())}"
        data["timestamp_utc"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        data["client_ip"] = request.client.host if request.client else "unknown"

        # Guardar en memoria de respaldo
        RESPUESTAS_LOCALES.append(data)

        # Enviar de forma PERMANENTE a Google Sheets
        sheets_synced = False
        target_url = GOOGLE_SHEETS_WEBHOOK_URL
        
        # Si el usuario pasó una URL en la petición, tiene prioridad de respaldo
        if data.get("custom_sheets_url") and data.get("custom_sheets_url") != "":
            target_url = data.get("custom_sheets_url")

        if target_url and target_url != "TU_URL_DE_APPS_SCRIPT_AQUI":
            try:
                # Enviamos el payload como JSON
                sheets_response = requests.post(
                    target_url, 
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=8
                )
                sheets_synced = (sheets_response.status_code in [200, 302])
            except Exception as sheet_err:
                print(f"[GOOGLE SHEETS ERROR]: {sheet_err}")

        return {
            "success": True,
            "message": "Encuesta procesada y guardada",
            "received_at": data["timestamp_utc"],
            "google_sheets_synced": sheets_synced,
            "id": data["id"]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error general: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al guardar los datos.")

@app.get("/api/stats")
def get_dashboard_stats():
    registros = []

    # Intentar obtener los datos reales directamente desde Google Sheets (doGet)
    if GOOGLE_SHEETS_WEBHOOK_URL and GOOGLE_SHEETS_WEBHOOK_URL != "TU_URL_DE_APPS_SCRIPT_AQUI":
        try:
            res = requests.get(GOOGLE_SHEETS_WEBHOOK_URL, timeout=6)
            if res.status_code == 200:
                sheet_data = res.json()
                if isinstance(sheet_data, list):
                    registros = sheet_data
        except Exception as e:
            print(f"[STATS FETCH ERROR de Google Sheets]: {e}")

    # Si no hay datos de Sheets aún, usar el respaldo local
    if not registros:
        registros = RESPUESTAS_LOCALES

    total = len(registros)
    por_municipio = {}
    por_perfil = {}
    por_modalidad = {}
    por_area_formacion = {}
    brechas_talento = {}
    niveles_urgencia = []

    for r in registros:
        # Municipio
        muni = r.get("p1_residencia") or r.get("Municipio_Residencia") or "Sin especificar"
        por_municipio[muni] = por_municipio.get(muni, 0) + 1
        
        # Perfil
        perf = r.get("p3_perfil") or r.get("Perfil_P3") or "Otro"
        por_perfil[perf] = por_perfil.get(perf, 0) + 1
        
        # Modalidad
        mod = r.get("p11_modalidad") or r.get("Modalidad")
        if mod:
            por_modalidad[mod] = por_modalidad.get(mod, 0) + 1
        
        # Áreas de interés
        areas = r.get("p10_areas") or r.get("Areas_Interes") or []
        if isinstance(areas, str):
            areas = [a.strip() for a in areas.split(",") if a.strip()]
        for a in areas:
            por_area_formacion[a] = por_area_formacion.get(a, 0) + 1

        # Brechas de talento
        brechas = r.get("p23_areas_dificultad") or []
        if isinstance(brechas, str):
            brechas = [b.strip() for b in brechas.split(",") if b.strip()]
        for b in brechas:
            brechas_talento[b] = brechas_talento.get(b, 0) + 1

        # Urgencia
        urg = r.get("p26_urgencia_talento") or r.get("Urgencia_Talento")
        if urg:
            try:
                niveles_urgencia.append(int(urg))
            except ValueError:
                pass

    promedio_urgencia = round(sum(niveles_urgencia) / len(niveles_urgencia), 1) if niveles_urgencia else 4.0

    return {
        "total_respuestas": total,
        "promedio_urgencia": promedio_urgencia,
        "por_municipio": por_municipio if por_municipio else {"Guadalajara de Buga": 1, "Tuluá": 1},
        "por_perfil": por_perfil if por_perfil else {"Estudiante": 1, "Empresario": 1},
        "por_modalidad": por_modalidad if por_modalidad else {"Híbrida": 1, "Presencial": 1},
        "top_areas_formacion": dict(sorted(por_area_formacion.items(), key=lambda x: x[1], reverse=True)[:8]) if por_area_formacion else {"Inteligencia Artificial": 1, "Agroindustria": 1},
        "top_brechas_talento": dict(sorted(brechas_talento.items(), key=lambda x: x[1], reverse=True)[:8]) if brechas_talento else {"Inteligencia Artificial": 1, "Logística": 1},
        "ultimas_respuestas": registros[-15:]
    }
