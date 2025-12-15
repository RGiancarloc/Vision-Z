import streamlit as st
import cv2
import numpy as np
import ollama
import io
import time
import threading
import pickle
import json
import subprocess
from pathlib import Path
from collections import deque
import base64

from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import av

# ---------------- IMPORTS OPCIONALES ----------------

# OCR (EasyOCR) – opcional
try:
    import easyocr
    HAS_EASYOCR = True
except Exception:
    easyocr = None
    HAS_EASYOCR = False

# Reconocimiento facial – opcional
try:
    import face_recognition
    HAS_FACE = True
except Exception:
    face_recognition = None
    HAS_FACE = False

# MediaPipe (detección de caídas) – opcional
try:
    import mediapipe as mp
    from mediapipe.python.solutions import pose as mp_pose
    HAS_MEDIAPIPE = True
    print("✅ MediaPipe cargado correctamente")
except ImportError as e:
    mp = None
    mp_pose = None
    HAS_MEDIAPIPE = False
    print(f"⚠️ MediaPipe no disponible: {e}")
except Exception as e:
    mp = None
    mp_pose = None
    HAS_MEDIAPIPE = False
    print(f"⚠️ Error cargando MediaPipe: {e}")

from ultralytics import YOLO

# ---------------- CONFIGURACIÓN ---------------- 
OLLAMA_MODEL = "llava"  # Modelo con visión para describir imágenes
CONFIDENCE_THRESHOLD = 0.5

STATIC_OBJECTS_FILE = "static_objects.json"
LEARNING_THRESHOLD = 5  # Nº de apariciones para considerar un objeto estático

FALL_DETECTION_THRESHOLD = 0.6  # Umbral simple para caída
READER_TEXT_HISTORY_SIZE = 5    # Historial de texto OCR

# ---------------- TTS (Piper) ----------------

def tts_with_piper(text: str):
    """Llama a Piper TTS por línea de comandos (opcional)."""
    if not text:
        return
    try:
        command = "piper --model es_ES-dave-medium.onnx --output_file output.wav"
        process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        process.communicate(input=text.encode())

        with open("output.wav", "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/wav", autoplay=True)

    except Exception as e:
        print(f"[ERROR] Piper TTS: {e}")

# ---------------- INICIALIZACIÓN DE YOLO ----------------
@st.cache_resource
def init_yolo():
    try:
        model = YOLO("yolov8n.pt")
        print("[DEBUG] YOLO cargado correctamente")
        return model
    except Exception as e:
        print(f"[ERROR] al cargar YOLO: {e}")
        return None

yolo_model = init_yolo()

# ---------------- GESTIÓN DE ESTADO Y PERSISTENCIA ----------------

def load_state():
    """Carga estado inicial (rostros, objetos estáticos, etc.)."""
    default_state = {
        "known_faces": {},
        "static_objects": {},
        "mode": "description",  # 'description' o 'navigation'
        "status": "En espera...",
        "last_description": "N/A",
        "tts_trigger": False,
        "process_frame": False,
    }

    # Cargar rostros registrados
    if Path("faces.pkl").exists():
        try:
            with open("faces.pkl", "rb") as f:
                default_state["known_faces"] = pickle.load(f)
        except Exception as e:
            print(f"[WARN] No se pudo cargar faces.pkl: {e}")

    # Cargar objetos estáticos
    if Path(STATIC_OBJECTS_FILE).exists():
        try:
            with open(STATIC_OBJECTS_FILE, "r", encoding="utf-8") as f:
                default_state["static_objects"] = json.load(f)
        except Exception as e:
            print(f"[WARN] No se pudo cargar {STATIC_OBJECTS_FILE}: {e}")

    return default_state

def save_static_objects():
    try:
        with open(STATIC_OBJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                st.session_state["static_objects"],
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(f"[WARN] No se pudo guardar {STATIC_OBJECTS_FILE}: {e}")

# Inicializar session_state según estado persistente
for key, value in load_state().items():
    st.session_state.setdefault(key, value)

# ---------------- VIDEO PROCESSOR MEJORADO ----------------
class VideoProcessor(VideoTransformerBase):
    def __init__(self):
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.processing = False
        
        # Historial de textos para modo "lector"
        self.text_history = deque(maxlen=READER_TEXT_HISTORY_SIZE)

        # Pose de MediaPipe para detección de caídas
        if HAS_MEDIAPIPE and mp_pose is not None:
            self.pose_estimator = mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.pose_estimator = None

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        # Guardar el frame más reciente para procesamiento
        with self.frame_lock:
            self.latest_frame = img.copy()
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

# ---------------- FUNCIONES DE PROCESAMIENTO ----------------
def detect_objects(frame):
    """Detección de objetos con YOLO"""
    if not yolo_model:
        return []
    
    results = yolo_model(frame, verbose=False)
    detected_objects = []
    
    for result in results:
        for box in result.boxes:
            conf = float(box.conf.item())
            if conf > CONFIDENCE_THRESHOLD:
                class_id = int(box.cls.item())
                label = yolo_model.names[class_id]
                detected_objects.append(label)
    
    return list(set(detected_objects))  # Remover duplicados

def frame_to_base64(frame):
    """Convertir frame a base64 para enviar a Ollama"""
    if frame is None:
        return None
    try:
        # Reducir tamaño para mejor rendimiento
        frame_resized = cv2.resize(frame, (640, 480))
        _, buffer = cv2.imencode('.jpg', frame_resized)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Convirtiendo frame a base64: {e}")
        return None

def generate_description(frame):
    """Generar descripción usando Ollama con visión"""
    try:
        # 1. Detectar objetos con YOLO
        objects = detect_objects(frame)
        objects_text = ", ".join(objects) if objects else "no se detectaron objetos específicos"
        
        # 2. Convertir frame a base64
        image_base64 = frame_to_base64(frame)
        if not image_base64:
            return f"Detectado: {objects_text}. Error procesando imagen."
        
        # 3. Preparar prompt para Ollama
        prompt = """
Eres un asistente útil para personas con discapacidad visual. 
**RESPONDE EXCLUSIVAMENTE EN ESPAÑOL**

Describe esta imagen de manera concisa, clara y útil en español. 
Enfócate en elementos importantes para la navegación y seguridad.

Información de detección automática: {objects_text}

IMPORTANTE: Tu respuesta debe ser completamente en español.
        
        Descripción:
        """.format(objects_text=objects_text)
        
        # 4. Llamar a Ollama con la imagen
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            images=[image_base64]
        )
        
        description = response.get('response', '').strip()
        return description if description else "No se pudo generar descripción."
        
    except Exception as e:
        return f"Error generando descripción: {str(e)}"

# ---------------- INTERFAZ STREAMLIT ----------------
st.set_page_config(page_title="Ojo Electrónico v3.0", layout="centered")
st.title("🧠 Ojo Electrónico v3.0")
st.markdown("Asistencia cognitiva, proactiva y adaptativa. Soporta descripción de escena y modo de navegación básico.")

# Estado de la sesión
if 'last_description' not in st.session_state:
    st.session_state.last_description = "N/A"
if 'status' not in st.session_state:
    st.session_state.status = "En espera..."

# Controles de modo
mode = st.radio(
    "Modo de funcionamiento:",
    options=["description", "navigation"],
    format_func=lambda m: "Descripción" if m == "description" else "Navegación",
    horizontal=True,
)
st.session_state["mode"] = mode

# Función para el procesador de video
def video_processor_factory():
    return VideoProcessor()

# Componente de video
webrtc_ctx = webrtc_streamer(
    key="camera",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"video": True, "audio": False},
    video_processor_factory=video_processor_factory,
    async_processing=True,
)

# Información de estado de la cámara
if webrtc_ctx.state.playing:
    if webrtc_ctx.video_processor:
        st.success("✅ Cámara activa y lista para describir escenas")
    else:
        st.warning("⏳ Cámara iniciando, espera unos segundos...")
else:
    st.info("📷 Haz clic en 'START' para activar la cámara")

# Botón para describir escena
if st.button("📸 Describir escena ahora", use_container_width=True):
    st.session_state.status = "Procesando..."
    
    # Verificar si el WebRTC está activo y tiene video_processor
    if webrtc_ctx.state.playing and webrtc_ctx.video_processor:
        current_frame = webrtc_ctx.video_processor.get_latest_frame()
        if current_frame is not None:
            with st.spinner("Generando descripción..."):
                description = generate_description(current_frame)
                st.session_state.last_description = description
                st.session_state.status = "Descripción completada"
                
                # Reproducir audio con la descripción
                try:
                    tts_with_piper(description)
                except Exception as e:
                    print(f"[ERROR] TTS: {e}")
        else:
            st.session_state.last_description = "Error: No hay frame disponible. Espera a que la cámara capture una imagen."
            st.session_state.status = "Error"
    else:
        st.session_state.last_description = "Error: Cámara no activa. Haz clic en 'START' para activar la cámara primero."
        st.session_state.status = "Error"

# Mostrar estado y descripción
st.markdown("---")
st.write(f"**Estado:** {st.session_state.status}")
st.write(f"**Última descripción:** {st.session_state.last_description}")

# Debug info (opcional - puedes comentar estas líneas después)
with st.expander("🔍 Información de Debug"):
    if webrtc_ctx:
        st.write(f"WebRTC State: {webrtc_ctx.state}")
        st.write(f"Video Processor: {webrtc_ctx.video_processor is not None}")
        if webrtc_ctx.video_processor:
            frame = webrtc_ctx.video_processor.get_latest_frame()
            st.write(f"Frame disponible: {frame is not None}")
    st.write(f"OLLAMA_MODEL: {OLLAMA_MODEL}")
    st.write(f"YOLO Model: {yolo_model is not None}")