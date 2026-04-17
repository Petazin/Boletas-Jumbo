from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import upload
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Zenith Finance API")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Routers
app.include_router(upload.router, prefix="/api/v1/files", tags=["Ingesta de Archivos"])

@app.get("/")
async def root():
    return {
        "message": "Bienvenido a Zenith Finance API",
        "status": "online",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    # Aquí se podría añadir validación de conexión a la DB
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
