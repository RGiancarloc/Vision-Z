"""
Aplicación principal del asistente visual
"""
import time
import argparse
from app import config
from app import main.py
from core.camera_handler import AdaptiveCameraHandler
from core.object_detector import ObjectDetector
from core.language_processor import AdaptiveLanguageProcessor
from core.audio_feedback import AudioFeedback, ProximityAlertSystem

class VisualAssistant:
    """Asistente visual completo"""
    
    def __init__(self, mode='local'):
        print("🚀 Iniciando Asistente Visual...")
        
        self.mode = mode
        self.running = False
        
        # Inicializar componentes
        self.camera = AdaptiveCameraHandler(camera_id=0)
        self.detector = ObjectDetector()
        self.language_processor = AdaptiveLanguageProcessor()
        self.audio = AudioFeedback()
        self.proximity_alerts = ProximityAlertSystem(self.audio)
        
        # Estadísticas
        self.stats = {
            'frames_processed': 0,
            'detections_total': 0,
            'descriptions_generated': 0,
            'start_time': None
        }
        
        print("✅ Asistente inicializado correctamente")
    
    def start(self):
        """Inicia el asistente"""
        print("\n" + "="*50)
        print("👁️  ASISTENTE VISUAL ACTIVADO")
        print("="*50)
        print("📱 Apunta la cámara hacia adelante")
        print("🎤 Escucha las descripciones de audio")
        print("⌨️  Presiona Ctrl+C para salir\n")
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        # Mensaje inicial
        self.audio.speak("Asistente visual activado. Apunta la cámara hacia adelante.")
        
        try:
            with self.camera:
                self._main_loop()
        except KeyboardInterrupt:
            print("\n\n🛑 Deteniendo asistente...")
        finally:
            self.stop()
    
    def _main_loop(self):
        """Loop principal de procesamiento"""
        last_description_time = 0
        min_interval = config.performance.min_time_between_descriptions
        
        while self.running:
            # Obtener frame
            frame = self.camera.read()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Detectar objetos
            detections = self.detector.detect(frame)
            self.stats['frames_processed'] += 1
            self.stats['detections_total'] += len(detections)
            
            if not detections:
                time.sleep(0.1)
                continue
            
            # Filtrar detecciones relevantes
            relevant = self.detector.filter_relevant(detections)
            
            if not relevant:
                continue
            
            # Sistema de alertas de proximidad
            self.proximity_alerts.check_proximity(relevant)
            
            # Generar descripción (con control de frecuencia)
            current_time = time.time()
            
            if current_time - last_description_time >= min_interval:
                description = self.language_processor.generate_description(relevant)
                
                if description:
                    # Reproducir descripción
                    self.audio.speak(description, priority='normal')
                    self.stats['descriptions_generated'] += 1
                    last_description_time = current_time
                    
                    # Mostrar en consola
                    print(f"\n🗣️  {description}")
                    print(f"📊 FPS: {self.camera.get_fps():.1f} | "
                          f"Detecciones: {len(relevant)}")
            
            # Pequeña pausa para no saturar CPU
            time.sleep(0.05)
    
    def stop(self):
        """Detiene el asistente"""
        self.running = False
        
        # Mostrar estadísticas
        self._show_stats()
        
        # Mensaje de despedida
        self.audio.speak("Asistente visual desactivado. Hasta pronto.")
        time.sleep(2)
        
        print("\n✅ Asistente detenido correctamente")
    
    def _show_stats(self):
        """Muestra estadísticas de la sesión"""
        if self.stats['start_time']:
            duration = time.time() - self.stats['start_time']
            
            print("\n" + "="*50)
            print("📊 ESTADÍSTICAS DE LA SESIÓN")
            print("="*50)
            print(f"⏱️  Duración: {duration:.1f} segundos")
            print(f"🎞️  Frames procesados: {self.stats['frames_processed']}")
            print(f"👁️  Detecciones totales: {self.stats['detections_total']}")
            print(f"🗣️  Descripciones generadas: {self.stats['descriptions_generated']}")
            print(f"📈 FPS promedio: {self.stats['frames_processed']/duration:.1f}")
            print("="*50 + "\n")


class ServerMode:
    """Modo cliente-servidor para procesamiento remoto"""
    
    def __init__(self, server_url):
        import requests
        self.server_url = server_url
        self.session = requests.Session()
        
    def process_frame(self, frame):
        """Envía frame al servidor y recibe descripción"""
        import cv2
        import base64
        
        # Codificar frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Enviar al servidor
        try:
            response = self.session.post(
                f"{self.server_url}/process",
                json={'frame': frame_b64},
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('description', '')
        except Exception as e:
            print(f"⚠️  Error de conexión con servidor: {e}")
        
        return None


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Asistente Visual para Personas con Discapacidad Visual'
    )
    parser.add_argument(
        '--mode',
        choices=['local', 'server', 'hybrid'],
        default='local',
        help='Modo de operación'
    )
    parser.add_argument(
        '--server-url',
        default='http://localhost:8000',
        help='URL del servidor (modo server/hybrid)'
    )
    parser.add_argument(
        '--camera',
        type=int,
        default=0,
        help='ID de la cámara'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Modo debug con visualización'
    )
    
    args = parser.parse_args()
    
    # Actualizar configuración
    config.performance.mode = args.mode
    
    if args.mode == 'server':
        config.performance.server_url = args.server_url
    
    # Crear e iniciar asistente
    assistant = VisualAssistant(mode=args.mode)
    assistant.start()


if __name__ == "__main__":
    main()

