"""
Estimador de distancias usando geometría de cámara
"""
import numpy as np

# Constantes de calibración (ajustar según el dispositivo)
FOCAL_LENGTH = 600  # Longitud focal en píxeles (calibrar)
KNOWN_WIDTHS = {
    'person': 0.5,      # metros (ancho promedio de persona)
    'car': 1.8,
    'door': 0.9,
    'chair': 0.5,
    'bicycle': 0.6,
    'bottle': 0.08,
    'cell phone': 0.07,
    'laptop': 0.35,
}

def estimate_distance(bbox, frame_shape):
    """
    Estima distancia al objeto usando ancho en píxeles
    
    Fórmula: distance = (known_width * focal_length) / pixel_width
    
    Args:
        bbox: [x1, y1, x2, y2] coordenadas del bounding box
        frame_shape: (height, width, channels) del frame
        
    Returns:
        float: Distancia estimada en metros
    """
    # Ancho del objeto en píxeles
    pixel_width = bbox[2] - bbox[0]
    pixel_height = bbox[3] - bbox[1]
    
    # Usar altura para objetos verticales (personas)
    # Usar ancho para objetos horizontales
    pixel_size = max(pixel_width, pixel_height)
    
    # Estimación básica usando tamaño relativo
    # Objetos más grandes en pantalla = más cercanos
    frame_width = frame_shape[1]
    
    # Proporción del objeto respecto al frame
    size_ratio = pixel_size / frame_width
    
    # Distancia estimada (heurística simple)
    # Si ocupa 50% del frame → ~1m
    # Si ocupa 25% del frame → ~2m
    # Si ocupa 10% del frame → ~5m
    
    if size_ratio > 0.5:
        distance = 1.0
    elif size_ratio > 0.3:
        distance = 1.5
    elif size_ratio > 0.2:
        distance = 2.5
    elif size_ratio > 0.1:
        distance = 4.0
    else:
        distance = 6.0
    
    return distance


def estimate_distance_calibrated(bbox, object_class, frame_shape):
    """
    Estimación mejorada usando anchos conocidos
    
    Requiere calibración previa del focal_length de la cámara
    """
    if object_class not in KNOWN_WIDTHS:
        # Fallback a estimación básica
        return estimate_distance(bbox, frame_shape)
    
    known_width = KNOWN_WIDTHS[object_class]
    pixel_width = bbox[2] - bbox[0]
    
    # Evitar división por cero
    if pixel_width < 1:
        return 10.0
    
    # Fórmula de proyección pinhole
    distance = (known_width * FOCAL_LENGTH) / pixel_width
    
    # Limitar rango razonable
    distance = np.clip(distance, 0.5, 20.0)
    
    return distance


def calibrate_focal_length(known_distance, known_width, pixel_width):
    """
    Calibra el focal_length de la cámara
    
    Usar: colocar un objeto de ancho conocido a distancia conocida,
    medir su ancho en píxeles, y calcular focal_length
    
    Ejemplo:
        Persona (0.5m de ancho) a 2 metros de distancia
        Ocupa 150 píxeles en el frame
        focal_length = (150 * 2) / 0.5 = 600 píxeles
    """
    focal_length = (pixel_width * known_distance) / known_width
    return focal_length


def get_relative_position(bbox, frame_width):
    """
    Determina posición relativa del objeto
    
    Returns:
        tuple: (horizontal_pos, vertical_pos)
            horizontal: 'izquierda', 'centro', 'derecha'
            vertical: 'arriba', 'medio', 'abajo'
    """
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    
    # Posición horizontal
    if center_x < frame_width * 0.33:
        h_pos = "izquierda"
    elif center_x > frame_width * 0.66:
        h_pos = "derecha"
    else:
        h_pos = "frente"
    
    # Posición vertical (para escaleras, puertas, etc.)
    frame_height = frame_width * 0.75  # Asumiendo 4:3
    if center_y < frame_height * 0.33:
        v_pos = "arriba"
    elif center_y > frame_height * 0.66:
        v_pos = "abajo"
    else:
        v_pos = "medio"
    
    return h_pos, v_pos


# Clase para calibración interactiva
class CameraCalibrator:
    """Asistente de calibración de cámara"""
    
    def __init__(self):
        self.focal_length = None
        self.measurements = []
    
    def add_measurement(self, known_distance, known_width, pixel_width):
        """Agrega una medición de calibración"""
        fl = calibrate_focal_length(known_distance, known_width, pixel_width)
        self.measurements.append(fl)
        print(f"📏 Medición: focal_length = {fl:.1f} píxeles")
    
    def get_focal_length(self):
        """Calcula focal_length promedio de todas las mediciones"""
        if not self.measurements:
            return FOCAL_LENGTH  # Valor por defecto
        
        self.focal_length = np.mean(self.measurements)
        print(f"✅ Focal length calibrado: {self.focal_length:.1f} píxeles")
        return self.focal_length

