from fastapi import FastAPI, HTTPException, Request
   from fastapi.middleware.cors import CORSMiddleware
   from datetime import datetime

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
           print(f"[REGISTRO] Perfil: {data.get('p3_perfil')} | Municipio: {data.get('p1_residencia')}")
           
           return {
               "success": True,
               "message": "Respuesta recibida correctamente",
               "received_at": data["timestamp_utc"]
           }
       except HTTPException as he:
           raise he
       except Exception as e:
           raise HTTPException(status_code=500, detail="Error interno al procesar.")
