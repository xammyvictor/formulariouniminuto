import os
import requests
from collections import Counter
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

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

        return {
            "success": True,
            "message": "Respuesta guardada correctamente",
            "received_at": data["timestamp_utc"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al procesar la encuesta.")

@app.get("/api/stats")
def get_stats():
    try:
        res = requests.get(GOOGLE_SHEETS_WEBHOOK_URL, allow_redirects=True, timeout=15)
        raw_data = res.json() if res.status_code == 200 else []
        
        total = len(raw_data)
        if total == 0:
            return {
                "total_respuestas": 0,
                "urgencia_promedio": "0.0",
                "perfil_predominante": "Sin datos",
                "area_mas_demandada": "Sin datos",
                "municipios": {},
                "perfiles": {},
                "modalidades": {},
                "areas": {},
                "ultimas_respuestas": []
            }
            
        municipios = Counter([
            str(r.get("Municipio Residencia") or r.get("p1_residencia") or "").strip() 
            for r in raw_data if (r.get("Municipio Residencia") or r.get("p1_residencia"))
        ])
        
        perfiles = Counter([
            str(r.get("Perfil / Perspectiva") or r.get("p3_perfil") or "").strip() 
            for r in raw_data if (r.get("Perfil / Perspectiva") or r.get("p3_perfil"))
        ])
        
        modalidades = Counter([
            str(r.get("Modalidad Preferida") or r.get("p11_modalidad") or "").strip() 
            for r in raw_data if (r.get("Modalidad Preferida") or r.get("p11_modalidad"))
        ])
        
        areas_list = []
        for r in raw_data:
            val = r.get("Áreas de Interés") or r.get("p10_areas") or ""
            if isinstance(val, str) and val.strip():
                areas_list.extend([a.strip() for a in val.split(",") if a.strip()])
            elif isinstance(val, list):
                areas_list.extend(val)
        areas = Counter(areas_list)
        
        urgencias = []
        for r in raw_data:
            val_u = r.get("Urgencia Talento (1-5)") or r.get("p26_urgencia_talento")
            if val_u is not None and str(val_u).strip() != "":
                try:
                    u = float(str(val_u).strip())
                    if u > 0:
                        urgencias.append(u)
                except (ValueError, TypeError):
                    pass
                
        urgencia_prom = round(sum(urgencias) / len(urgencias), 1) if len(urgencias) > 0 else 0.0

        return {
            "total_respuestas": total,
            "urgencia_promedio": f"{urgencia_prom}",
            "perfil_predominante": perfiles.most_common(1)[0][0] if perfiles else "Sin datos",
            "area_mas_demandada": areas.most_common(1)[0][0] if areas else "Sin datos",
            "municipios": dict(municipios),
            "perfiles": dict(perfiles),
            "modalidades": dict(modalidades),
            "areas": dict(areas.most_common(10)),
            "ultimas_respuestas": raw_data[-10:]
        }
    except Exception as e:
        print(f"[ERROR STATS]: {str(e)}")
        return {
            "total_respuestas": 0,
            "urgencia_promedio": "0.0",
            "perfil_predominante": "Sin datos",
            "area_mas_demandada": "Sin datos",
            "municipios": {},
            "perfiles": {},
            "modalidades": {},
            "areas": {},
            "ultimas_respuestas": []
        }
