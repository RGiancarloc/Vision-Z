"""
Servidor API para procesamiento remoto
Útil para dispositivos móviles con recursos limitados
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import cv2
import numpy as np
from typing import Optional
import time

# Importar componentes del asistente
import sys
sys.path.append('..')
from core.object_detector import ObjectDetector
from core.language_processor import LanguageProcessor

app = FastAPI(
    title="Visual Assistant API",
    description="Servidor de procesamiento para asistente visual",
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar modelos (una sola vez al arrancar)
detector = None
language_processor = None

@app.on_event("startup")
async def startup_event():
    """Inicializa modelos al arrancar el servidor"""
    global detector, language_processor
    
    print("🚀 Inicializando servidor...")
    detector = ObjectDetector()
    language_processor = LanguageProcessor()
    print("✅ Servidor listo")

# Modelos de datos
class FrameRequest(BaseModel):
    frame: str  # Frame en base64
    generate_description: bool = True
    language: str = "es"

class DetectionResponse(BaseModel):
    detections: list
    description: Optional[str] = None
    processing_time: float
    timestamp: float

# Endpoints
@app.get("/")
async def root():
    """Endpoint de prueba"""
    return {
        "status": "online",
        "service": "Visual Assistant API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Verifica salud del servidor"""
    return {
        "status": "healthy",
        "detector": detector is not None,
        "language_processor": language_processor is not None,
        "timestamp": time.time()
    }

@app.post("/process", response_model=DetectionResponse)
async def process_frame(request: FrameRequest):
    """
    Procesa un frame y retorna detecciones y descripción
    
    Args:
        frame: Frame codificado en base64
        generate_description: Si generar descripción en lenguaje natural
        language: Idioma de la descripción
    
    Returns:
        DetectionResponse con detecciones y descripción
    """
    start_time = time.time()
    
    try:
        # Decodificar frame
        frame_data = base64.b64decode(request.frame)
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Frame inválido")
        
        # Detectar objetos
        detections = detector.detect(frame)
        
        # Filtrar relevantes
        relevant = detector.filter_relevant(detections)
        
        # Generar descripción si se solicita
        description = None
        if request.generate_description and relevant:
            description = language_processor.generate_description(relevant)
        
        processing_time = time.time() - start_time
        
        return DetectionResponse(
            detections=relevant,
            description=description,
            processing_time=processing_time,
            timestamp=time.time()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect")
async def detect_only(request: FrameRequest):
    """Solo detección de objetos (sin descripción)"""
    start_time = time.time()
    
    try:
        # Decodificar frame
        frame_data = base64.b64decode(request.frame)
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Frame inválido")
        
        # Detectar
        detections = detector.detect(frame)
        relevant = detector.filter_relevant(detections)
        
        processing_time = time.time() - start_time
        
        return {
            "detections": relevant,
            "processing_time": processing_time,
            "count": len(relevant)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/describe")
async def describe_scene(detections: list):
    """Genera descripción de detecciones existentes"""
    try:
        description = language_processor.generate_description(detections)
        
        return {
            "description": description,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Estadísticas
request_count = 0
total_processing_time = 0

@app.get("/stats")
async def get_stats():
    """Retorna estadísticas del servidor"""
    global request_count, total_processing_time
    
    avg_time = total_processing_time / request_count if request_count > 0 else 0
    
    return {
        "requests_processed": request_count,
        "total_processing_time": total_processing_time,
        "average_processing_time": avg_time,
        "uptime": time.time() - startup_time
    }

startup_time = time.time()

# WebSocket para streaming (opcional)
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para procesamiento en tiempo real"""
    await websocket.accept()
    
    try:
        while True:
            # Recibir frame
            data = await websocket.receive_json()
            
            # Procesar
            frame_b64 = data.get('frame')
            if not frame_b64:
                continue
            
            # Decodificar
            frame_data = base64.b64decode(frame_b64)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detectar
            detections = detector.detect(frame)
            relevant = detector.filter_relevant(detections)
            
            # Generar descripción
            description = None
            if relevant:
                description = language_processor.generate_description(relevant)
            
            # Enviar respuesta
            await websocket.send_json({
                "detections": relevant,
                "description": description,
                "timestamp": time.time()
            })
            
    except WebSocketDisconnect:
        print("Cliente desconectado")

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔════════════════════════════════════════╗
    ║   SERVIDOR API - ASISTENTE VISUAL     ║
    ╚════════════════════════════════════════╝
    
    📡 Servidor iniciando...
    🌐 API Docs: http://localhost:8000/docs
    🔌 WebSocket: ws://localhost:8000/ws
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Accesible desde red local
        port=8000,
        log_level="info"
    )

