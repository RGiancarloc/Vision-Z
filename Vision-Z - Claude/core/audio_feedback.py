"""
Sistema de retroalimentación auditiva y TTS
"""
import pyttsx3
import threading
import time
from queue import Queue
from config import config

class AudioFeedback:
    """Manejador de retroalimentación auditiva"""
    
    def __init__(self):
        self.engine = None
        self.audio_queue = Queue()
        self.speaking = False
        self.enabled = True
        
        # Inicializar motor TTS
        self._init_tts()
        
        # Hilo para procesamiento de audio
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()
        
    def _init_tts(self):
        """Inicializa el motor de text-to-speech"""
        try:
            self.engine = pyttsx3.init()
            
            # Configurar voz
            voices = self.engine.getProperty('voices')
            
            # Buscar voz en español
            spanish_voice = None
            for voice in voices:
                if 'spanish' in voice.name.lower() or 'es' in voice.languages:
                    spanish_voice = voice.id
                    break
            
            if spanish_voice:
                self.engine.setProperty('voice', spanish_voice)
            
            # Configurar velocidad y volumen
            self.engine.setProperty('rate', config.audio.rate)
            self.engine.setProperty('volume', config.audio.volume)
            
            print("✅ Sistema de audio inicializado")
            
        except Exception as e:
            print(f"❌ Error inicializando TTS: {e}")
            self.engine = None
    
    def speak(self, text: str, priority: str = 'normal', interrupt: bool = False):
        """
        Reproduce texto como voz
        
        Args:
            text: Texto a sintetizar
            priority: 'alta', 'media', 'normal'
            interrupt: Si True, interrumpe audio actual
        """
        if not self.enabled or not text:
            return
        
        # Si es alta prioridad, limpiar cola
        if priority == 'alta' or interrupt:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except:
                    break
        
        # Agregar a cola
        self.audio_queue.put({
            'text': text,
            'priority': priority,
            'timestamp': time.time()
        })
    
    def _audio_loop(self):
        """Loop de procesamiento de audio"""
        while True:
            try:
                # Esperar mensaje
                message = self.audio_queue.get()
                
                if not self.enabled:
                    continue
                
                text = message['text']
                
                # Reproducir con pyttsx3
                if self.engine:
                    self.speaking = True
                    self.engine.say(text)
                    self.engine.runAndWait()
                    self.speaking = False
                
            except Exception as e:
                print(f"⚠️  Error en audio: {e}")
                self.speaking = False
                time.sleep(0.1)
    
    def play_alert(self, alert_type: str = 'warning'):
        """
        Reproduce alerta sonora
        
        Args:
            alert_type: 'warning', 'danger', 'info'
        """
        alerts = {
            'warning': "⚠️",
            'danger': "🚨",
            'info': "ℹ️"
        }
        
        # En un sistema real, reproducir archivo de sonido
        # Por ahora, usar beep del sistema
        try:
            import winsound
            if alert_type == 'danger':
                winsound.Beep(1000, 200)  # 1000Hz, 200ms
            else:
                winsound.Beep(800, 100)
        except:
            # No disponible en todos los sistemas
            pass
    
    def vibrate(self, duration: float = 0.2, pattern: str = 'single'):
        """
        Activa vibración (Android)
        
        Args:
            duration: Duración en segundos
            pattern: 'single', 'double', 'continuous'
        """
        if not config.audio.enable_vibration:
            return
        
        try:
            # Requiere jnius y Android
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            Vibrator = autoclass('android.os.Vibrator')
            
            activity = PythonActivity.mActivity
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
            
            if pattern == 'single':
                vibrator.vibrate(int(duration * 1000))
            elif pattern == 'double':
                pattern_array = [0, 200, 100, 200]
                vibrator.vibrate(pattern_array, -1)
            elif pattern == 'continuous':
                pattern_array = [0, 300, 200, 300, 200, 300]
                vibrator.vibrate(pattern_array, -1)
                
        except Exception as e:
            # No disponible fuera de Android
            pass
    
    def stop(self):
        """Detiene audio actual"""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        self.speaking = False
    
    def toggle(self):
        """Activa/desactiva audio"""
        self.enabled = not self.enabled
        status = "activado" if self.enabled else "desactivado"
        print(f"🔊 Audio {status}")
    
    def is_speaking(self):
        """Verifica si está hablando"""
        return self.speaking


class GTTSAudioFeedback(AudioFeedback):
    """Versión alternativa usando gTTS (Google Text-to-Speech)"""
    
    def __init__(self):
        super().__init__()
        self.engine = 'gtts'
        
    def _init_tts(self):
        """No requiere inicialización para gTTS"""
        try:
            from gtts import gTTS
            import pygame
            
            # Verificar dependencias
            pygame.mixer.init()
            print("✅ gTTS inicializado")
        except ImportError:
            print("❌ Instalar: pip install gtts pygame")
    
    def _audio_loop(self):
        """Loop usando gTTS"""
        from gtts import gTTS
        import pygame
        import tempfile
        import os
        
        while True:
            try:
                message = self.audio_queue.get()
                
                if not self.enabled:
                    continue
                
                text = message['text']
                
                # Generar audio
                tts = gTTS(text=text, lang='es', slow=False)
                
                # Guardar temporalmente
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    temp_file = fp.name
                    tts.save(temp_file)
                
                # Reproducir
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                # Limpiar
                os.remove(temp_file)
                
            except Exception as e:
                print(f"⚠️  Error en gTTS: {e}")
                time.sleep(0.1)


class ProximityAlertSystem:
    """Sistema de alertas por proximidad"""
    
    def __init__(self, audio_feedback: AudioFeedback):
        self.audio = audio_feedback
        self.alert_distances = {
            'critical': 1.0,    # < 1m: alerta crítica
            'warning': 2.0,     # < 2m: advertencia
            'info': 4.0         # < 4m: información
        }
        self.last_alert_time = {}
        self.alert_cooldown = 3.0  # segundos entre alertas del mismo objeto
    
    def check_proximity(self, detections: list):
        """Verifica proximidad y emite alertas"""
        current_time = time.time()
        
        for det in detections:
            distance = det['distance']
            obj_class = det['class']
            
            # Determinar nivel de alerta
            alert_level = None
            if distance < self.alert_distances['critical']:
                alert_level = 'critical'
            elif distance < self.alert_distances['warning']:
                alert_level = 'warning'
            
            if not alert_level:
                continue
            
            # Verificar cooldown
            last_time = self.last_alert_time.get(obj_class, 0)
            if current_time - last_time < self.alert_cooldown:
                continue
            
            # Emitir alerta
            self._emit_alert(det, alert_level)
            self.last_alert_time[obj_class] = current_time
    
    def _emit_alert(self, detection: dict, level: str):
        """Emite alerta multimodal"""
        obj = detection['class']
        dist = detection['distance']
        pos = detection['position']
        
        if level == 'critical':
            # Alerta urgente
            self.audio.play_alert('danger')
            self.audio.vibrate(pattern='double')
            self.audio.speak(f"Cuidado, {obj} muy cerca", 
                           priority='alta', interrupt=True)
        
        elif level == 'warning':
            # Advertencia
            self.audio.play_alert('warning')
            self.audio.vibrate(pattern='single')
