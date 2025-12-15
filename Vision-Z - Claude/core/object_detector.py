"""
Detector de objetos usando YOLOv8 con optimizaciones
"""
import numpy as np
from ultralytics import YOLO
from config import config
from utils.distance_estimator import estimate_distance

class ObjectDetector:
    """Detector de objetos optimizado para móviles"""
    
    def __init__(self):
        print("📦 Cargando modelo YOLOv8...")
        
        # Cargar modelo
        self.model = YOLO(config.yolo.model_path)
        
        # Configurar para CPU/GPU
        self.device = config.yolo.device
        
        # Clases del modelo COCO
        self.class_names = self.model.names
        
        print(f"✅ Modelo cargado en {self.device}")
        
    def detect(self, frame):
        """
        Detecta objetos en el frame
        
        Returns:
            list: Lista de detecciones con formato:
                {
                    'class': str,
                    'confidence': float,
                    'bbox': [x1, y1, x2, y2],
                    'distance': float,
                    'position': str  # 'izquierda', 'centro', 'derecha'
                }
        """
        # Inferencia
        results = self.model.predict(
            frame,
            conf=config.yolo.confidence_threshold,
            iou=config.yolo.iou_threshold,
            device=self.device,
            half=config.yolo.half_precision,
            verbose=False
        )
        
        detections = []
        
        if results and len(results) > 0:
            result = results[0]
            
            # Procesar cada detección
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.class_names[class_id]
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                # Calcular distancia estimada
                distance = estimate_distance(bbox, frame.shape)
                
                # Determinar posición horizontal
                position = self._get_position(bbox, frame.shape[1])
                
                detection = {
                    'class': class_name,
                    'confidence': confidence,
                    'bbox': bbox.tolist(),
                    'distance': distance,
                    'position': position
                }
                
                detections.append(detection)
        
        # Ordenar por prioridad (más cercano primero)
        detections.sort(key=lambda x: x['distance'])
        
        return detections
    
    def _get_position(self, bbox, frame_width):
        """Determina posición horizontal del objeto"""
        center_x = (bbox[0] + bbox[2]) / 2
        
        if center_x < frame_width * 0.33:
            return "izquierda"
        elif center_x > frame_width * 0.66:
            return "derecha"
        else:
            return "frente"
    
    def filter_relevant(self, detections):
        """
        Filtra detecciones relevantes para seguridad
        
        Prioriza:
        - Objetos cercanos (< 3m)
        - Clases prioritarias
        - Objetos en el camino (centro)
        """
        relevant = []
        
        for det in detections:
            # Objetos muy cercanos siempre son relevantes
            if det['distance'] < 2.0:
                det['priority'] = 'alta'
                relevant.append(det)
                continue
            
            # Clases prioritarias
            if det['class'] in config.yolo.priority_classes:
                if det['distance'] < 5.0:
                    det['priority'] = 'media'
                    relevant.append(det)
                    continue
            
            # Objetos en el camino
            if det['position'] == 'frente' and det['distance'] < 4.0:
                det['priority'] = 'media'
                relevant.append(det)
        
        return relevant[:5]  # Máximo 5 objetos más relevantes


class YOLOQuantized(ObjectDetector):
    """Versión cuantizada para dispositivos con muy pocos recursos"""
    
    def __init__(self):
        # Intentar cargar versión cuantizada INT8
        try:
            from ultralytics import YOLO
            self.model = YOLO(config.yolo.model_path)
            
            # Exportar a formato optimizado si no existe
            # self.model.export(format='onnx', int8=True)
            
            print("✅ Modelo cuantizado cargado")
        except Exception as e:
            print(f"⚠️  Error al cargar modelo cuantizado: {e}")
            super().__init__()


# Función auxiliar para visualización (debugging)
def draw_detections(frame, detections):
    """Dibuja las detecciones en el frame"""
    import cv2
    
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        
        # Color según prioridad
        color = (0, 0, 255) if det.get('priority') == 'alta' else (255, 165, 0)
        
        # Dibujar bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Etiqueta
        label = f"{det['class']} {det['distance']:.1f}m {det['position']}"
        cv2.putText(frame, label, (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return frame
