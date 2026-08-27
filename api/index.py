#from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import os
import requests

#app = FastAPI(
    title="API Encuesta Regional UNIMINUTO",
    version="2.0.0",
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

## Almacén de respuestas para estadísticas inmediatas en memoria
RESPUESTAS_EN_MEMORIA = [
    {
        "id": "mock-1",
        "timestamp_utc": "2026-08-25T14:30:00Z",
        "p1_residencia": "Guadalajara de Buga",
        "p2_actividad": "Guadalajara de Buga",
        "p3_perfil": "persona_estudios",
        "p4_relacion": "Empleado(a) del sector privado",
        "p6_sector": "Tecnología y servicios digitales",
        "p7_nivel_educativo": "Tecnológico",
        "p8_tipo_formacion": ["Profesional universitario", "Certificaciones profesionales"],
        "p10_areas": ["Inteligencia Artificial", "Analítica y ciencia de datos"],
        "p11_modalidad": "Híbrida",
        "p17_valor_semestre": "Entre $2.000.001 y $2.500.000",
        "p20_competencias": ["Inteligencia Artificial", "Analítica de datos", "Inglés"],
        "p26_urgencia_talento": "5",
        "p39_areas_prioritarias": ["Inteligencia Artificial y analítica", "Agroindustria y desarrollo rural"]
    },
    {
        "id": "mock-2",
        "timestamp_utc": "2026-08-26T09:15:00Z",
        "p1_residencia": "Tuluá",
        "p2_actividad": "Tuluá",
        "p3_perfil": "empresario",
        "p4_relacion": "Empresario(a) / propietario(a) de empresa",
        "p6_sector": "Agroindustria",
        "p7_nivel_educativo": "Profesional universitario",
        "p20_competencias": ["Liderazgo", "Pensamiento crítico y resolución de problemas", "Gestión de proyectos"],
        "p22_dificultad_talento": "Sí, frecuentemente",
        "p23_areas_dificultad": ["Agroindustria", "Inteligencia Artificial", "Logística y cadena de suministro"],
        "p26_urgencia_talento": "4",
        "p39_areas_prioritarias": ["Agroindustria y desarrollo rural", "Logística y cadena de suministro"]
    }
]

# Google Sheets Webhook URL (obtenida mediante Google Apps Script)
GOOGLE_SHEETS_WEBHOOK_URL = https://script.google.com/macros/s/AKfycbwv4r18zK1cN3zx4BXzP6s6xEt83Xe-NnFpjCoqlZci-v4v3rWN1m-AQ_YzPMz25d4X9g/exec

#@app.get("/api")
def health_check():
    return {
        "status": "online",
        "service": "UNIMINUTO Regional Survey Backend",
        "server_time": datetime.utcnow().isoformat(),
        "total_cached_records": len(RESPUESTAS_EN_MEMORIA),
        "google_sheets_connected": bool(GOOGLE_SHEETS_WEBHOOK_URL)
    }

#@app.post("/api/submit")
async def receive_survey(request: Request):
    try:
        data = await request.json()
        
        if not data.get("p3_perfil"):
            raise HTTPException(status_code=400, detail="El campo de perfil (p3_perfil) es obligatorio.")
        
        # Enriquecer datos con metadatos
        data["id"] = f"RESP-{len(RESPUESTAS_EN_MEMORIA) + 1}-{int(datetime.utcnow().timestamp())}"
        data["timestamp_utc"] = datetime.utcnow().isoformat()
        data["client_ip"] = request.client.host if request.client else "unknown"

        # Guardar en memoria para el Dashboard en tiempo real
        RESPUESTAS_EN_MEMORIA.append(data)

        # Reenviar automáticamente a Google Sheets en Google Drive si está configurado
        webhook_url = data.get("custom_sheets_url") or GOOGLE_SHEETS_WEBHOOK_URL
        sheets_synced = False
        
        if webhook_url:
            try:
                # Se envía como JSON con timeout seguro
                sheets_response = requests.post(
                    webhook_url, 
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                sheets_synced = (sheets_response.status_code in [200, 302])
            except Exception as sheet_err:
                print(f"[GOOGLE SHEETS ERROR] No se pudo sincronizar: {sheet_err}")

        print(f"[NUEVO REGISTRO] Perfil: {data.get('p3_perfil')} | Municipio: {data.get('p1_residencia')} | Sheets Sync: {sheets_synced}")
        
        return {
            "success": True,
            "message": "Respuesta procesada correctamente",
            "received_at": data["timestamp_utc"],
            "google_sheets_synced": sheets_synced,
            "id": data["id"]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error procesando encuesta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al registrar la encuesta.")

#@app.get("/api/stats")
def get_dashboard_stats():
    total = len(RESPUESTAS_EN_MEMORIA)
    
    # Contadores estadísticos
    por_municipio = {}
    por_perfil = {}
    por_modalidad = {}
    por_area_formacion = {}
    brechas_talento = {}
    niveles_urgencia = []

    for r in RESPUESTAS_EN_MEMORIA:
        # Municipio
        muni = r.get("p1_residencia", "Sin especificar")
        por_municipio[muni] = por_municipio.get(muni, 0) + 1
        
        # Perfil
        perf = r.get("p3_perfil", "otro")
        por_perfil[perf] = por_perfil.get(perf, 0) + 1
        
        # Modalidad
        mod = r.get("p11_modalidad")
        if mod:
            por_modalidad[mod] = por_modalidad.get(mod, 0) + 1
        
        # Áreas de interés (puede ser lista o string)
        areas = r.get("p10_areas", [])
        if isinstance(areas, str):
            areas = [areas]
        for a in areas:
            por_area_formacion[a] = por_area_formacion.get(a, 0) + 1

        # Brechas de talento
        brechas = r.get("p23_areas_dificultad", [])
        if isinstance(brechas, str):
            brechas = [brechas]
        for b in brechas:
            brechas_talento[b] = brechas_talento.get(b, 0) + 1

        # Urgencia
        if r.get("p26_urgencia_talento"):
            try:
                niveles_urgencia.append(int(r.get("p26_urgencia_talento")))
            except ValueError:
                pass

    promedio_urgencia = round(sum(niveles_urgencia) / len(niveles_urgencia), 1) if niveles_urgencia else 4.0

    return {
        "total_respuestas": total,
        "promedio_urgencia": promedio_urgencia,
        "por_municipio": por_municipio,
        "por_perfil": por_perfil,
        "por_modalidad": por_modalidad,
        "top_areas_formacion": dict(sorted(por_area_formacion.items(), key=lambda x: x[1], reverse=True)[:8]),
        "top_brechas_talento": dict(sorted(brechas_talento.items(), key=lambda x: x[1], reverse=True)[:8]),
        "ultimas_respuestas": RESPUESTAS_EN_MEMORIA[-10:] # Últimos 10 registros
    }
