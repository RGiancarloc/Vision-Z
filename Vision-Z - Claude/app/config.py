import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Literal, List

# ==========================
# Configuración de cámara
# ==========================

@dataclass
class CameraConfig:
    """Configuración de la cámara"""
    # Resolución base del frame
    resolution: tuple = (640, 480)
    # FPS de captura desde la cámara física
    fps_capture: int = 30
    # FPS de procesamiento (cuántos frames realmente se procesan)
    fps_processing: int = 5
    # Índice de cámara (0 = cámara por defecto)
    device_index: int = 0
    # Tamaño del buffer de frames (usado en CameraHandler)
    frame_buffer_size: int = 10


# ==========================
# Configuración de YOLO
# ==========================

@dataclass
class YOLOConfig:
    """Configuración del modelo YOLOv8"""
    model_path: str = "models/yolov8n.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    device: str = "cpu"          # "cpu" o "cuda"
    half_precision: bool = True  # usar FP16 si la GPU lo soporta
    # Clases prioritarias para seguridad/navegación
    priority_classes: List[str] = field(default_factory=lambda: [
        "person", "car", "bus", "truck", "bicycle", "motorcycle",
        "chair", "bench", "door", "stairs"
    ])


# ==========================
# Configuración de Ollama (LLM)
# ==========================

@dataclass
class OllamaConfig:
    """Configuración del modelo de lenguaje"""
    model_name: str = "llama3:instruct"  # Modelo ligero
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3         # Respuestas consistentes
    max_tokens: int = 100
    timeout: int = 5                 # Segundos

    # Sistema de prompts
    system_prompt: str = (
        "Eres un asistente de descripción visual para personas con discapacidad visual.\n"
        "Debes describir la escena de forma CONCISA, CLARA y ÚTIL para la movilidad.\n"
        "Prioriza: distancia, dirección y seguridad.\n"
        "Usa español natural. Máximo 2 frases cortas."
    )


# ==========================
# Configuración de audio / TTS
# ==========================

@dataclass
class AudioConfig:
    """Configuración de retroalimentación auditiva"""
    engine: Literal["pyttsx3", "gtts"] = "pyttsx3"
    language: str = "es"
    rate: int = 180        # palabras por minuto
    volume: float = 0.9    # 0.0 - 1.0

    # Alertas de proximidad
    proximity_alert_distance: float = 1.5  # metros
    alert_sound_path: str = "assets/beep.wav"
    enable_vibration: bool = True          # usado en Android


# ==========================
# Configuración de rendimiento
# ==========================

@dataclass
class PerformanceConfig:
    """Configuración de rendimiento y batería"""
    mode: Literal["local", "server", "hybrid"] = "local"
    server_url: str = "http://192.168.1.100:8000"

    # Optimización de batería / frecuencia de descripciones
    min_time_between_descriptions: float = 2.0  # segundos
    adaptive_fps: bool = True                   # Reduce FPS si batería baja
    battery_save_threshold: int = 20            # % batería

    # Privacidad
    save_frames: bool = False
    encrypt_transmission: bool = True


# ==========================
# Configuración global
# ==========================

@dataclass
class AppConfig:
    """Configuración global de la aplicación"""
    camera: CameraConfig = field(default_factory=CameraConfig)
    yolo: YOLOConfig = field(default_factory=YOLOConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/visual_assistant.log"


# Instancia global
config = AppConfig()


# ==========================
# Cargar configuración externa (opcional)
# ==========================

def load_config(config_path: str = "config.yaml") -> AppConfig:
    """
    Carga configuración desde archivo YAML.
    Si no existe o hay error, usa la configuración por defecto.
    """
    import yaml
    global config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Partimos de la config actual y pisamos lo que venga en YAML
        cfg = AppConfig()

        if "camera" in data:
            for k, v in data["camera"].items():
                setattr(cfg.camera, k, v)

        if "yolo" in data:
            for k, v in data["yolo"].items():
                setattr(cfg.yolo, k, v)

        if "ollama" in data:
            for k, v in data["ollama"].items():
                setattr(cfg.ollama, k, v)

        if "audio" in data:
            for k, v in data["audio"].items():
                setattr(cfg.audio, k, v)

        if "performance" in data:
            for k, v in data["performance"].items():
                setattr(cfg.performance, k, v)

        if "log_level" in data:
            cfg.log_level = data["log_level"]
        if "log_file" in data:
            cfg.log_file = data["log_file"]

        config = cfg
        return cfg

    except FileNotFoundError:
        print("⚠️  config.yaml no encontrado, usando configuración por defecto")
        return config
    except Exception as e:
        print(f"⚠️  Error cargando config.yaml: {e}. Usando configuración por defecto.")
        return config
