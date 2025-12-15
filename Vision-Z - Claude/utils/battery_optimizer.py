"""
Optimización de consumo de batería
"""
import time
from enum import Enum
from dataclasses import dataclass

class PowerMode(Enum):
    """Modos de ahorro de energía"""
    PERFORMANCE = "performance"      # Máximo rendimiento
    BALANCED = "balanced"           # Balance rendimiento/batería
    POWER_SAVER = "power_saver"    # Máximo ahorro
    ULTRA_SAVER = "ultra_saver"    # Ahorro extremo

@dataclass
class PowerProfile:
    """Perfil de configuración de energía"""
    name: str
    fps_processing: int
    yolo_resolution: tuple
    description_interval: float
    use_half_precision: bool
    ollama_enabled: bool
    ollama_model: str
    
# Perfiles predefinidos
POWER_PROFILES = {
    PowerMode.PERFORMANCE: PowerProfile(
        name="Alto Rendimiento",
        fps_processing=10,
        yolo_resolution=(640, 480),
        description_interval=1.0,
        use_half_precision=True,
        ollama_enabled=True,
        ollama_model="llama3.2:1b"
    ),
    PowerMode.BALANCED: PowerProfile(
        name="Balanceado",
        fps_processing=5,
        yolo_resolution=(416, 416),
        description_interval=2.0,
        use_half_precision=True,
        ollama_enabled=True,
        ollama_model="llama3.2:1b"
    ),
    PowerMode.POWER_SAVER: PowerProfile(
        name="Ahorro de Batería",
        fps_processing=3,
        yolo_resolution=(320, 320),
        description_interval=3.0,
        use_half_precision=True,
        ollama_enabled=False,  # Usar descripciones básicas
        ollama_model=None
    ),
    PowerMode.ULTRA_SAVER: PowerProfile(
        name="Ahorro Extremo",
        fps_processing=1,
        yolo_resolution=(224, 224),
        description_interval=5.0,
        use_half_precision=True,
        ollama_enabled=False,
        ollama_model=None
    )
}

class BatteryOptimizer:
    """Optimizador adaptativo de batería"""
    
    def __init__(self):
        self.current_mode = PowerMode.BALANCED
        self.battery_level = 100
        self.is_charging = False
        
        # Umbrales de batería
        self.thresholds = {
            'ultra_saver': 10,
            'power_saver': 20,
            'balanced': 50,
            'performance': 80
        }
        
        # Estadísticas
        self.stats = {
            'total_frames': 0,
            'frames_skipped': 0,
            'ollama_calls_skipped': 0,
            'start_time': time.time()
        }
    
    def update_battery_status(self, level: int, is_charging: bool = False):
        """
        Actualiza estado de batería y ajusta modo
        
        Args:
            level: Nivel de batería (0-100)
            is_charging: Si está cargando
        """
        self.battery_level = level
        self.is_charging = is_charging
        
        # Si está cargando, usar mejor rendimiento
        if is_charging:
            self._switch_mode(PowerMode.PERFORMANCE)
            return
        
        # Ajustar modo según nivel de batería
        if level <= self.thresholds['ultra_saver']:
            self._switch_mode(PowerMode.ULTRA_SAVER)
        elif level <= self.thresholds['power_saver']:
            self._switch_mode(PowerMode.POWER_SAVER)
        elif level <= self.thresholds['balanced']:
            self._switch_mode(PowerMode.BALANCED)
        else:
            self._switch_mode(PowerMode.PERFORMANCE)
    
    def _switch_mode(self, new_mode: PowerMode):
        """Cambia a un nuevo modo de energía"""
        if new_mode != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = new_mode
            
            profile = POWER_PROFILES[new_mode]
            
            print(f"\n⚡ CAMBIO DE MODO DE ENERGÍA")
            print(f"   {old_mode.value} → {new_mode.value}")
            print(f"   📊 FPS: {profile.fps_processing}")
            print(f"   📐 Resolución: {profile.yolo_resolution}")
            print(f"   ⏱️  Intervalo: {profile.description_interval}s")
            print(f"   🔋 Batería: {self.battery_level}%\n")
    
    def get_current_profile(self) -> PowerProfile:
        """Retorna perfil actual"""
        return POWER_PROFILES[self.current_mode]
    
    def should_process_frame(self) -> bool:
        """Determina si se debe procesar el frame actual"""
        self.stats['total_frames'] += 1
        
        # En modo ultra ahorro, procesar solo 1 de cada N frames
        if self.current_mode == PowerMode.ULTRA_SAVER:
            # Procesar 1 de cada 30 frames
            if self.stats['total_frames'] % 30 != 0:
                self.stats['frames_skipped'] += 1
                return False
        
        return True
    
    def should_call_ollama(self, last_call_time: float) -> bool:
        """Determina si se debe llamar a Ollama"""
        profile = self.get_current_profile()
        
        # Si Ollama está deshabilitado en este perfil
        if not profile.ollama_enabled:
            self.stats['ollama_calls_skipped'] += 1
            return False
        
        # Respetar intervalo mínimo
        current_time = time.time()
        if current_time - last_call_time < profile.description_interval:
            return False
        
        return True
    
    def get_recommended_settings(self) -> dict:
        """Retorna configuración recomendada para el modo actual"""
        profile = self.get_current_profile()
        
        return {
            'camera': {
                'fps_processing': profile.fps_processing,
                'resolution': profile.yolo_resolution,
            },
            'yolo': {
                'half_precision': profile.use_half_precision,
                'input_size': profile.yolo_resolution,
            },
            'ollama': {
                'enabled': profile.ollama_enabled,
                'model': profile.ollama_model,
                'interval': profile.description_interval,
            }
        }
    
    def estimate_battery_life(self) -> float:
        """
        Estima tiempo de batería restante (horas)
        
        Basado en consumo actual y nivel de batería
        """
        # Consumo estimado por modo (mAh/hora)
        consumption = {
            PowerMode.PERFORMANCE: 800,
            PowerMode.BALANCED: 500,
            PowerMode.POWER_SAVER: 300,
            PowerMode.ULTRA_SAVER: 150
        }
        
        # Batería típica de smartphone: 3000-5000 mAh
        battery_capacity = 4000  # mAh promedio
        
        current_consumption = consumption[self.current_mode]
        available_mah = battery_capacity * (self.battery_level / 100)
        
        estimated_hours = available_mah / current_consumption
        
        return estimated_hours
    
    def get_stats(self) -> dict:
        """Retorna estadísticas de optimización"""
        runtime = time.time() - self.stats['start_time']
        
        return {
            'mode': self.current_mode.value,
            'battery_level': self.battery_level,
            'is_charging': self.is_charging,
            'runtime_hours': runtime / 3600,
            'total_frames': self.stats['total_frames'],
            'frames_skipped': self.stats['frames_skipped'],
            'skip_rate': self.stats['frames_skipped'] / max(self.stats['total_frames'], 1),
            'ollama_calls_skipped': self.stats['ollama_calls_skipped'],
            'estimated_battery_life_hours': self.estimate_battery_life()
        }
    
    def print_stats(self):
        """Imprime estadísticas"""
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("📊 ESTADÍSTICAS DE BATERÍA")
        print("="*50)
        print(f"🔋 Nivel: {stats['battery_level']}%")
        print(f"⚡ Modo: {stats['mode']}")
        print(f"🔌 Cargando: {'Sí' if stats['is_charging'] else 'No'}")
        print(f"⏱️  Tiempo activo: {stats['runtime_hours']:.2f} horas")
        print(f"🎞️  Frames procesados: {stats['total_frames']}")
        print(f"⏭️  Frames omitidos: {stats['frames_skipped']} ({stats['skip_rate']*100:.1f}%)")
        print(f"🤖 Llamadas Ollama omitidas: {stats['ollama_calls_skipped']}")
        print(f"⏳ Batería estimada restante: {stats['estimated_battery_life_hours']:.1f} horas")
        print("="*50 + "\n")


class ScreenOptimizer:
    """Optimización de pantalla para ahorro"""
    
    def __init__(self):
        self.screen_off = False
        self.brightness_level = 100
    
    def reduce_brightness(self, level: int = 20):
        """Reduce brillo de pantalla"""
        try:
            # Android
            from jnius import autoclass
            Settings = autoclass('android.provider.Settings$System')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            activity = PythonActivity.mActivity
            
            # Ajustar brillo (0-255)
            brightness = int(255 * level / 100)
            Settings.putInt(
                activity.getContentResolver(),
                Settings.SCREEN_BRIGHTNESS,
                brightness
            )
            
            self.brightness_level = level
            print(f"💡 Brillo reducido a {level}%")
            
        except:
            print("⚠️  Control de brillo no disponible")
    
    def turn_off_screen(self):
        """
        Apaga pantalla manteniendo app activa
        
        Útil cuando el usuario solo necesita audio
        """
        try:
            from jnius import autoclass
            PowerManager = autoclass('android.os.PowerManager')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            
            # Crear WakeLock para mantener CPU activa
            wakelock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "visual_assistant::wakelock"
            )
            wakelock.acquire()
            
            self.screen_off = True
            print("📱 Pantalla apagada, app activa")
            
        except:
            print("⚠️  Control de pantalla no disponible")

