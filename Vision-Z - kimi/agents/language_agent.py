import ollama
import json
from typing import List, Dict

class LanguageAgent:
    def __init__(self, model_name='llama3:8b'):
        """Inicializa el agente de lenguaje con OLLAMA"""
        self.model_name = model_name
        self.client = ollama.Client()
        
        # Prompt sistemático para generar descripciones naturales
        self.system_prompt = """Eres un asistente visual que ayuda a personas ciegas. 
        Tu tarea es describir de forma clara, concisa y útil los objetos detectados.
        Usa español natural y coloquial. Sé específico pero no excesivamente detallado.
        Prioriza información relevante para la movilidad y seguridad."""
        
    def generate_description(self, detections: List[Dict]) -> str:
        """Genera una descripción natural en español"""
        if not detections:
            return ""
        
        # Agrupar por posición
        grouped = self._group_by_position(detections)
        
        # Crear prompt contextual
        prompt = self._create_prompt(grouped)
        
        try:
            # Generar descripción con OLLAMA
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 150
                }
            )
            
            description = response['message']['content'].strip()
            
            # Post-procesar para mejorar naturalidad
            description = self._post_process(description)
            
            return description
            
        except Exception as e:
            # Fallback a descripción básica
            return self._generate_basic_description(grouped)
    
    def _group_by_position(self, detections: List[Dict]) -> Dict:
        """Agrupa detecciones por posición"""
        grouped = {
            'izquierda': [],
            'derecha': [],
            'centro': []
        }
        
        for detection in detections:
            position = detection['position']['horizontal']
            obj_name = self._translate_object(detection['object'])
            distance = detection['position']['distance']
            
            grouped[position].append({
                'object': obj_name,
                'distance': distance
            })
        
        return grouped
    
    def _translate_object(self, obj_name: str) -> str:
        """Traduce nombres de objetos al español"""
        translations = {
            'person': 'persona',
            'bottle': 'botella',
            'chair': 'silla',
            'couch': 'sofá',
            'bed': 'cama',
            'dining table': 'mesa',
            'tv': 'televisor',
            'laptop': 'portátil',
            'cell phone': 'teléfono',
            'book': 'libro',
            'cup': 'taza',
            'bowl': 'plato',
            'spoon': 'cuchara',
            'fork': 'tenedor',
            'knife': 'cuchillo'
        }
        
        return translations.get(obj_name, obj_name)
    
    def _create_prompt(self, grouped: Dict) -> str:
        """Crea un prompt contextual"""
        prompt_parts = []
        
        for position, objects in grouped.items():
            if objects:
                obj_list = [f"{obj['distance']} {obj['object']}" for obj in objects]
                if len(obj_list) == 1:
                    prompt_parts.append(f"A tu {position} hay {obj_list[0]}")
                else:
                    obj_str = ", ".join(obj_list[:-1]) + f" y {obj_list[-1]}"
                    prompt_parts.append(f"A tu {position} hay {obj_str}")
        
        prompt = ". ".join(prompt_parts)
        prompt += ". Por favor, descríbelo de forma natural y útil para alguien que no puede ver."
        
        return prompt
    
    def _post_process(self, description: str) -> str:
        """Post-procesa la descripción para mejorarla"""
        # Eliminar partes innecesarias
        description = description.replace("Como asistente visual, ", "")
        description = description.replace("Te informo que ", "")
        
        # Asegurar que termine en punto
        if not description.endswith('.'):
            description += '.'
        
        return description
    
    def _generate_basic_description(self, grouped: Dict) -> str:
        """Genera una descripción básica como fallback"""
        descriptions = []
        
        for position, objects in grouped.items():
            if objects:
                for obj in objects:
                    descriptions.append(f"Hay {obj['object']} a tu {position}")
        
        return ". ".join(descriptions) + "."

