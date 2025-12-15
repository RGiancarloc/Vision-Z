import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración general
CONFIG = {
    # Configuración de cámara
    'camera': {
        'width': 640,
        'height': 480,
        'fps': 30,
        'device_index': 0
    },
    
    # Configuración de YOLO
    'yolo': {
        'model': 'yolov8n.pt',
        'confidence_threshold': 0.5,
        'iou_threshold': 0.45
    },
    
    # Configuración de OLLAMA
    'ollama': {
        'model': 'llama3:8b',
        'temperature': 0.7,
        'max_tokens': 150,
        'timeout': 10
    },
    
    # Configuración de audio
    'audio': {
        'language': 'es',
        'volume': 0.7,
        'rate': 150,  # palabras por minuto
        'max_queue_size': 10
    },
    
    # Configuración de base de datos
    'database': {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'vision_assistant'),
        'user': os.getenv('DB_USER', 'vision_user'),
        'password': os.getenv('DB_PASSWORD', 'vision_pass'),
        'port': os.getenv('DB_PORT', 5432)
    },
    
    # Configuración de procesamiento
    'processing': {
        'frame_skip': 2,  # Procesar 1 de cada 2 frames
        'description_cooldown': 3.0,  # segundos entre descripciones
        'max_objects_per_description': 5
    },
    
    # Configuración de accesibilidad
    'accessibility': {
        'high_contrast': True,
        'large_buttons': True,
        'audio_feedback': True,
        'minimal_visual_elements': True
    }
}

# Objetos relevantes para detectar
RELEVANT_OBJECTS = {
    'person', 'bottle', 'chair', 'couch', 'bed', 'dining table', 
    'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'book', 'clock', 'scissors', 'toothbrush', 'cup', 'fork', 
    'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich',
    'orange', 'broccoli', 'carrot', 'pizza', 'donut', 'cake',
    'door', 'window', 'stairs', 'escalator', 'elevator', 'car',
    'bus', 'truck', 'motorcycle', 'bicycle', 'traffic light',
    'stop sign', 'bench', 'potted plant', 'sink', 'refrigerator'
}

# Traducciones al español
SPANISH_TRANSLATIONS = {
    'person': 'persona',
    'people': 'personas',
    'bottle': 'botella',
    'chair': 'silla',
    'couch': 'sofá',
    'bed': 'cama',
    'dining table': 'mesa',
    'tv': 'televisor',
    'laptop': 'ordenador portátil',
    'mouse': 'ratón',
    'remote': 'control remoto',
    'keyboard': 'teclado',
    'cell phone': 'teléfono móvil',
    'book': 'libro',
    'clock': 'reloj',
    'scissors': 'tijeras',
    'toothbrush': 'cepillo de dientes',
    'cup': 'taza',
    'fork': 'tenedor',
    'knife': 'cuchillo',
    'spoon': 'cuchara',
    'bowl': 'cuenco',
    'banana': 'plátano',
    'apple': 'manzana',
    'sandwich': 'sándwich',
    'orange': 'naranja',
    'broccoli': 'brócoli',
    'carrot': 'zanahoria',
    'pizza': 'pizza',
    'donut': 'dona',
    'cake': 'pastel',
    'door': 'puerta',
    'window': 'ventana',
    'stairs': 'escaleras',
    'car': 'coche',
    'bus': 'autobús',
    'truck': 'camión',
    'motorcycle': 'motocicleta',
    'bicycle': 'bicicleta',
    'traffic light': 'semáforo',
    'stop sign': 'señal de stop',
    'bench': 'banco',
    'potted plant': 'planta en maceta',
    'sink': 'lavabo',
    'refrigerator': 'nevera'
}

