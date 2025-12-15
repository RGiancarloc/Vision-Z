import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
import time

class VisionAgent:
    def __init__(self, model_path='yolov8n.pt'):
        """Inicializa el agente de visión con YOLO"""
        self.model = YOLO(model_path)
        self.class_names = self.model.names
        
        # Objetos relevantes para personas invidentes
        self.relevant_objects = {
            'person', 'bottle', 'chair', 'couch', 'bed', 'dining table', 
            'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
            'book', 'clock', 'scissors', 'toothbrush', 'cup', 'fork', 
            'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich',
            'orange', 'broccoli', 'carrot', 'pizza', 'donut', 'cake'
        }
        
        # Historial para evitar repeticiones
        self.detection_history = defaultdict(lambda: {'count': 0, 'last_seen': 0})
        
    def detect_objects(self, frame):
        """Detecta objetos en el fotograma"""
        results = self.model(frame, stream=False)
        
        detections = []
        current_time = time.time()
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf[0].item()
                    cls = int(box.cls[0].item())
                    class_name = self.class_names[cls]
                    
                    # Filtrar por objetos relevantes y confianza
                    if class_name in self.relevant_objects and conf > 0.5:
                        # Calcular posición relativa
                        position = self._calculate_position(frame, x1, y1, x2, y2)
                        
                        detection = {
                            'object': class_name,
                            'confidence': conf,
                            'position': position,
                            'bbox': (x1, y1, x2, y2),
                            'time': current_time
                        }
                        
                        detections.append(detection)
        
        # Filtrar por objetos que no se repiten con frecuencia
        filtered_detections = self._filter_recent_detections(detections)
        
        return filtered_detections
    
    def _calculate_position(self, frame, x1, y1, x2, y2):
        """Calcula la posición relativa del objeto"""
        height, width = frame.shape[:2]
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Determinar horizontal
        if center_x < width * 0.33:
            horizontal = "izquierda"
        elif center_x > width * 0.66:
            horizontal = "derecha"
        else:
            horizontal = "centro"
        
        # Determinar vertical
        if center_y < height * 0.33:
            vertical = "arriba"
        elif center_y > height * 0.66:
            vertical = "abajo"
        else:
            vertical = "centro"
        
        # Determinar distancia aproximada por tamaño
        obj_width = x2 - x1
        if obj_width > width * 0.5:
            distance = "muy cerca"
        elif obj_width > width * 0.25:
            distance = "cerca"
        elif obj_width > width * 0.1:
            distance = "medio"
        else:
            distance = "lejos"
        
        return {
            'horizontal': horizontal,
            'vertical': vertical,
            'distance': distance
        }
    
    def _filter_recent_detections(self, detections, cooldown=3.0):
        """Filtra detecciones para evitar repeticiones"""
        filtered = []
        current_time = time.time()
        
        for detection in detections:
            obj_name = detection['object']
            obj_key = f"{obj_name}_{detection['position']['horizontal']}"
            
            # Verificar si ha pasado suficiente tiempo
            if (current_time - self.detection_history[obj_key]['last_seen']) > cooldown:
                filtered.append(detection)
                self.detection_history[obj_key]['count'] += 1
                self.detection_history[obj_key]['last_seen'] = current_time
        
        return filtered
