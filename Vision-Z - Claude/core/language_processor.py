"""
Procesador de lenguaje natural usando Ollama
"""
import requests
import json
from config import config
from typing import List, Dict

class LanguageProcessor:
    """Genera descripciones naturales de escenas usando Ollama"""
    
    def __init__(self):
        self.base_url = config.ollama.base_url
        self.model = config.ollama.model_name
        self.timeout = config.ollama.timeout
        
        # Verificar conexión
        self._check_connection()
        
    def _check_connection(self):
        """Verifica que Ollama esté corriendo"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"✅ Conectado a Ollama ({self.model})")
            else:
                print("⚠️  Ollama no responde correctamente")
        except Exception as e:
            print(f"❌ Error conectando a Ollama: {e}")
            print("   Asegúrate de que Ollama esté corriendo: ollama serve")
    
    def generate_description(self, detections: List[Dict]) -> str:
        """
        Genera descripción natural de las detecciones
        
        Args:
            detections: Lista de objetos detectados con formato:
                [{
                    'class': str,
                    'distance': float,
                    'position': str,
                    'priority': str
                }, ...]
        
        Returns:
            str: Descripción en español para TTS
        """
        if not detections:
            return "Camino despejado"
        
        # Construir contexto estructurado
        context = self._build_context(detections)
        
        # Prompt para Ollama
        prompt = self._build_prompt(context)
        
        try:
            # Llamada a Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": config.ollama.system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": config.ollama.temperature,
                        "num_predict": config.ollama.max_tokens,
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                description = result.get('response', '').strip()
                
                # Limpieza de respuesta
                description = self._clean_description(description)
                
                return description
            else:
                print(f"⚠️  Error Ollama: {response.status_code}")
                return self._fallback_description(detections)
                
        except requests.Timeout:
            print("⏱️  Timeout de Ollama, usando descripción básica")
            return self._fallback_description(detections)
        except Exception as e:
            print(f"❌ Error generando descripción: {e}")
            return self._fallback_description(detections)
    
    def _build_context(self, detections: List[Dict]) -> str:
        """Construye contexto estructurado para el prompt"""
        lines = []
        
        for i, det in enumerate(detections[:5], 1):  # Máximo 5 objetos
            obj = det['class']
            dist = det['distance']
            pos = det['position']
            
            # Traducir nombres de clases
            obj_es = self._translate_class(obj)
            
            lines.append(f"{i}. {obj_es} a {dist:.1f}m {pos}")
        
        return "\n".join(lines)
    
    def _build_prompt(self, context: str) -> str:
        """Construye el prompt para Ollama"""
        prompt = f"""Objetos detectados:
{context}

Describe la escena para una persona ciega que camina. 
Menciona solo lo más importante para su seguridad.
Usa frases cortas y claras.
Máximo 2 frases."""
        
        return prompt
    
    def _clean_description(self, text: str) -> str:
        """Limpia y normaliza la descripción"""
        # Remover posibles artefactos
        text = text.replace('*', '')
        text = text.replace('#', '')
        text = text.strip()
        
        # Limitar longitud
        if len(text) > 200:
            text = text[:200].rsplit('.', 1)[0] + '.'
        
        return text
    
    def _fallback_description(self, detections: List[Dict]) -> str:
        """
        Descripción básica sin IA cuando Ollama falla
        """
        if not detections:
            return "Camino despejado"
        
        # Tomar el objeto más prioritario
        obj = detections[0]
        
        obj_es = self._translate_class(obj['class'])
        dist = obj['distance']
        pos = obj['position']
        
        # Construir frase simple
        if dist < 1.5:
            urgencia = "muy cerca"
        elif dist < 3:
            urgencia = "cerca"
        else:
            urgencia = ""
        
        if pos == "frente":
            return f"{obj_es} {urgencia} frente a ti"
        else:
            return f"{obj_es} {urgencia} a tu {pos}"
    
    def _translate_class(self, class_name: str) -> str:
        """Traduce nombres de clases COCO al español"""
        translations = {
            'person': 'persona',
            'car': 'auto',
            'truck': 'camión',
            'bicycle': 'bicicleta',
            'motorcycle': 'motocicleta',
            'bus': 'autobús',
            'chair': 'silla',
            'door': 'puerta',
            'stairs': 'escaleras',
            'bench': 'banco',
            'bottle': 'botella',
            'cup': 'taza',
            'fork': 'tenedor',
            'knife': 'cuchillo',
            'cell phone': 'teléfono',
            'laptop': 'computadora',
            'dog': 'perro',
            'cat': 'gato',
            'tree': 'árbol',
        }
        
        return translations.get(class_name, class_name)


# Ejemplo de prompts optimizados
PROMPT_TEMPLATES = {
    'safety': """Eres un asistente de movilidad para personas ciegas.
Describe SOLO los obstáculos y peligros en el camino.
Usa: "Cuidado" para peligros cercanos (<2m).
Formato: [Objeto] [distancia] [dirección].
Máximo 15 palabras.""",
    
    'detailed': """Describe la escena completa para una persona ciega.
Incluye: personas, objetos y ambiente general.
Prioriza información útil para navegación.
Usa lenguaje natural y claro. 2-3 frases.""",
    
    'navigation': """Asiste en navegación interior para persona ciega.
Menciona: puertas, pasillos, escaleras, obstáculos.
Indica direcciones claras (izquierda/derecha/frente).
Conciso y preciso."""
}


class AdaptiveLanguageProcessor(LanguageProcessor):
    """Procesador que adapta el nivel de detalle según contexto"""
    
    def __init__(self):
        super().__init__()
        self.last_description_time = 0
        self.danger_threshold = 2.0  # metros
    
    def generate_description(self, detections: List[Dict]) -> str:
        """Genera descripción adaptativa"""
        import time
        
        current_time = time.time()
        
        # Verificar peligro inmediato
        has_danger = any(d['distance'] < self.danger_threshold 
                        for d in detections)
        
        # Si hay peligro, descripción inmediata
        if has_danger:
            self.last_description_time = current_time
            return super().generate_description(detections)
        
        # Si no, respetar intervalo mínimo
        min_interval = config.performance.min_time_between_descriptions
        
        if current_time - self.last_description_time < min_interval:
            return None  # No generar descripción aún
        
        self.last_description_time = current_time
        return super().generate_description(detections)
