
import pyttsx3
import threading
import queue
import time
from typing import Optional

class AudioModule:
    def __init__(self):
        """Inicializa el motor de síntesis de voz"""
        self.engine = pyttsx3.init()
        
        # Configuración inicial
        self.engine.setProperty('rate', 150)  # Velocidad
        self.engine.setProperty('volume', 0.9)  # Volumen
        
        # Configurar voz en español si está disponible
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'spanish' in voice.languages[0].lower() or 'es' in voice.id.lower():
                self.engine.setProperty('voice', voice.id)
                break
        
        # Cola para mensajes
        self.message_queue = queue.Queue()
        self.is_speaking = False
        self.stop_flag = threading.Event()
        
        # Hilo para procesar mensajes
        self.speech_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.speech_thread.start()
    
    def speak(self, text: str, priority: bool = False):
        """Agrega texto a la cola de voz"""
        if text and text.strip():
            if priority:
                # Insertar al principio de la cola
                temp_list = list(self.message_queue.queue)
                temp_list.insert(0, text)
                with self.message_queue.mutex:
                    self.message_queue.queue.clear()
                    for item in temp_list:
                        self.message_queue.put(item)
            else:
                self.message_queue.put(text)
    
    def _process_queue(self):
        """Procesa la cola de mensajes en segundo plano"""
        while not self.stop_flag.is_set():
            try:
                text = self.message_queue.get(timeout=1)
                if text:
                    self.is_speaking = True
                    
                    # Dividir texto largo en partes
                    if len(text) > 200:
                        parts = self._split_text(text)
                        for part in parts:
                            if not self.message_queue.empty():
                                # Hay mensajes nuevos, saltar este
                                break
                            self.engine.say(part)
                            self.engine.runAndWait()
                    else:
                        self.engine.say(text)
                        self.engine.runAndWait()
                    
                    self.is_speaking = False
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error en síntesis de voz: {e}")
                self.is_speaking = False
    
    def _split_text(self, text: str, max_length: int = 150) -> list:
        """Divide texto largo en partes manejables"""
        parts = []
        sentences = text.split('. ')
        
        current_part = ""
        for sentence in sentences:
            if len(current_part + sentence) <= max_length:
                current_part += sentence + ". "
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence + ". "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def set_volume(self, volume: float):
        """Ajusta el volumen (0.0 a 1.0)"""
        self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
    
    def set_rate(self, rate: int):
        """Ajusta la velocidad de habla (palabras por minuto)"""
        self.engine.setProperty('rate', max(50, min(300, rate)))
    
    def stop(self):
        """Detiene la reproducción actual"""
        self.engine.stop()
        self.is_speaking = False
    
    def clear_queue(self):
        """Limpia la cola de mensajes"""
        with self.message_queue.mutex:
            self.message_queue.queue.clear()
    
    def is_busy(self) -> bool:
        """Verifica si está hablando"""
        return self.is_speaking or not self.message_queue.empty()
    
    def shutdown(self):
        """Apaga el motor de voz"""
        self.stop_flag.set()
        self.clear_queue()
        self.engine.stop()
