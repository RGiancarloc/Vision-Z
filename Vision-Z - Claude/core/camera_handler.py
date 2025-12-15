"""
Manejador de cámara con optimización de rendimiento
"""
import cv2
import numpy as np
import time
from threading import Thread, Lock
from queue import Queue
from config import config

class CameraHandler:
    """Captura optimizada de video con procesamiento en hilo separado"""
    
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.cap = None
        self.frame_queue = Queue(maxsize=config.camera.frame_buffer_size)
        self.running = False
        self.lock = Lock()
        
        # Estadísticas
        self.fps_actual = 0
        self.frame_count = 0
        self.last_time = time.time()
        
    def start(self):
        """Inicia la captura de video"""
        # Intentar con DirectShow (mejor soporte en Windows)
        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            # Fallback: intentar backend por defecto
            self.cap = cv2.VideoCapture(self.camera_id)
            
        if not self.cap.isOpened():
            raise RuntimeError("❌ No se pudo abrir la cámara")

        
        # Configurar resolución
        width, height = config.camera.resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, config.camera.fps_capture)
        
        if not self.cap.isOpened():
            raise RuntimeError("❌ No se pudo abrir la cámara")
        
        self.running = True
        
        # Hilo de captura
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        print("✅ Cámara iniciada")
        
    def _capture_loop(self):
        """Loop de captura en hilo separado"""
        frame_interval = 1.0 / config.camera.fps_processing
        last_capture = 0
        
        while self.running:
            current_time = time.time()
            
            # Control de FPS de procesamiento
            if current_time - last_capture < frame_interval:
                time.sleep(0.001)
                continue
            
            ret, frame = self.cap.read()
            
            if not ret:
                print("⚠️  Error al capturar frame")
                continue
            
            # Preprocesar frame
            processed_frame = self._preprocess_frame(frame)
            
            # Agregar a cola (no bloqueante)
            if not self.frame_queue.full():
                self.frame_queue.put(processed_frame)
            
            last_capture = current_time
            self.frame_count += 1
            
            # Calcular FPS real
            if current_time - self.last_time >= 1.0:
                self.fps_actual = self.frame_count
                self.frame_count = 0
                self.last_time = current_time
    
    def _preprocess_frame(self, frame):
        """Preprocesamiento del frame para optimización"""
        # Conversión de color si es necesario
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Reducción de ruido (opcional, cuesta CPU)
        # frame = cv2.GaussianBlur(frame, (3, 3), 0)
        
        return frame
    
    def read(self):
        """Obtiene el frame más reciente"""
        if self.frame_queue.empty():
            return None
        return self.frame_queue.get()
    
    def get_fps(self):
        """Retorna FPS actual"""
        return self.fps_actual
    
    def stop(self):
        """Detiene la captura"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("🛑 Cámara detenida")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class AdaptiveCameraHandler(CameraHandler):
    """Versión con FPS adaptativo según batería"""
    
    def __init__(self, camera_id=0):
        super().__init__(camera_id)
        self.battery_level = 100
        
    def update_battery(self, level):
        """Actualiza nivel de batería y ajusta FPS"""
        self.battery_level = level
        
        if config.performance.adaptive_fps:
            if level < config.performance.battery_save_threshold:
                # Modo ahorro: reducir a 2 FPS
                config.camera.fps_processing = 2
                print("🔋 Modo ahorro de batería activado")
            elif level < 50:
                # Nivel medio: 3 FPS
                config.camera.fps_processing = 3
            else:
                # Nivel normal: 5 FPS
                config.camera.fps_processing = 5


# Utilidad para obtener batería en Android (requiere pyjnius)
def get_battery_level():
    """Obtiene nivel de batería (Android)"""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        IntentFilter = autoclass('android.content.IntentFilter')
        BatteryManager = autoclass('android.os.BatteryManager')
        
        activity = PythonActivity.mActivity
        ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        battery_status = activity.registerReceiver(None, ifilter)
        
        level = battery_status.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        scale = battery_status.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        
        return int(level / scale * 100)
    except:
        return 100  # Asumir carga completa si no se puede obtener


