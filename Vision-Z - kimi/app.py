import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import threading
import queue
import time
import logging
from agents.vision_agent import VisionAgent
from agents.language_agent import LanguageAgent
from modules.audio_module import AudioModule
from modules.database_manager import DatabaseManager
from utils.config import CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de página accesible
st.set_page_config(
    page_title="Asistente Visual para Invidentes",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para accesibilidad mejorada
st.markdown("""
    <style>
    /* Estilo principal - Alto contraste amarillo/negro */
    .main {
        background-color: #000000;
        color: #FFFF00;
    }
    
    /* Botones grandes para personas con discapacidad visual */
    .stButton > button {
        font-size: 28px !important;
        height: 100px !important;
        width: 100% !important;
        background-color: #000000 !important;
        color: #FFFF00 !important;
        border: 4px solid #FFFF00 !important;
        border-radius: 15px !important;
        font-weight: bold !important;
        margin: 10px 0 !important;
    }
    .stButton > button:hover {
        background-color: #FFFF00 !important;
        color: #000000 !important;
        transform: scale(1.02);
        transition: all 0.3s ease;
    }
    
    /* Texto grande y claro */
    .big-text {
        font-size: 36px !important;
        color: #FFFF00 !important;
        background-color: #000000 !important;
        padding: 25px !important;
        text-align: center !important;
        border-radius: 15px !important;
        border: 3px solid #FFFF00 !important;
        margin-bottom: 30px !important;
        font-weight: bold !important;
    }
    
    /* Panel de estado */
    .status-panel {
        background-color: #111111;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #444444;
        margin: 20px 0;
    }
    
    /* Historial de descripciones */
    .history-item {
        background-color: #222222;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 5px solid #FFFF00;
    }
    
    /* Ocultar elementos de Streamlit no necesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

class VisionAssistantApp:

  
    def __init__(self):
        """Inicializa la aplicación de asistencia visual"""
        # Inicializar TODAS las variables de estado
        self._initialize_session_state()
        
        # Inicializar componentes esenciales
        self.vision_agent = VisionAgent()
        self.language_agent = LanguageAgent()
        self.audio_module = AudioModule()
        
        # Base de datos SQLite
        self.db_enabled = True
        try:
            self.db_manager = DatabaseManager()
            print("✅ Base de datos SQLite conectada")
        except Exception as e:
            print(f"⚠️ Error con SQLite: {e}")
            self.db_enabled = False
        
        # Queues para procesamiento en hilos
        self.frame_queue = queue.Queue(maxsize=3)
        self.description_queue = queue.Queue()
        
        # Variables de instancia para hilos
        self.frame_thread = None
        self.analysis_thread = None
        
        # Configuración inicial de audio
        self.audio_module.set_volume(CONFIG['audio']['volume'])
        self.audio_module.set_rate(CONFIG['audio']['rate'])
    
    def _initialize_session_state(self):
        """Inicializa todas las variables de estado de Streamlit"""
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        if 'last_description' not in st.session_state:
            st.session_state.last_description = ''
        if 'detection_history' not in st.session_state:
            st.session_state.detection_history = []
        if 'frame_count' not in st.session_state:
            st.session_state.frame_count = 0
        if 'object_count' not in st.session_state:
            st.session_state.object_count = 0
        if 'vision_agent' not in st.session_state:
            st.session_state.vision_agent = None
        if 'language_agent' not in st.session_state:
            st.session_state.language_agent = None
        if 'audio_module' not in st.session_state:
            st.session_state.audio_module = None

    def process_frames(self):
        """Captura y procesa frames de la cámara"""
        cap = cv2.VideoCapture(CONFIG['camera']['device_index'])
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['camera']['width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['camera']['height'])
        cap.set(cv2.CAP_PROP_FPS, CONFIG['camera']['fps'])
        
        frame_skip = CONFIG['processing']['frame_skip']
        frame_counter = 0
        
        while st.session_state.is_running:
            ret, frame = cap.read()
            if not ret:
                logger.error("Error capturando frame")
                self.audio_module.speak("Error con la cámara")
                break
            
            frame_counter += 1
            
            # Procesar solo algunos frames para optimizar
            if frame_counter % frame_skip == 0:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            
            time.sleep(0.01)  # Pequeña pausa para no saturar
        
        cap.release()
        logger.info("Procesamiento de frames detenido")
    
    def analyze_frames(self):
        """Analiza frames y genera descripciones"""
        last_description_time = 0
        
        while st.session_state.is_running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get(timeout=1)
                    
                    current_time = time.time()
                    
                    # Verificar cooldown
                    cooldown = CONFIG['processing']['description_cooldown']
                    if current_time - last_description_time < cooldown:
                        continue
                    
                    # Detectar objetos
                    detections = self.vision_agent.detect_objects(frame)
                    
                    if detections:
                        st.session_state.object_count = len(detections)
                        
                        # Generar descripción
                        description = self.language_agent.generate_description(detections)
                        
                        if description and description != st.session_state.last_description:
                            st.session_state.last_description = description
                            
                            # Agregar al historial
                            history_item = {
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'description': description,
                                'objects': len(detections)
                            }
                            st.session_state.detection_history.insert(0, history_item)
                            
                            # Limitar historial
                            if len(st.session_state.detection_history) > 10:
                                st.session_state.detection_history = st.session_state.detection_history[:10]
                            
                            # Reproducir audio
                            self.audio_module.speak(description, priority=True)
                            
                            # Guardar en base de datos
                            if self.db_enabled and description:
                                try:
                                    self.db_manager.save_detection(detections, description)
                                    logger.debug("Guardado en base de datos")
                                except Exception as e:
                                    logger.error(f"Error guardando en DB: {e}")
                            
                            last_description_time = current_time
                    
                    st.session_state.frame_count += 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error en análisis: {e}")
                if "OLLAMA" in str(e):
                    self.audio_module.speak("Error con el motor de descripciones")
    
    def start_assistant(self):
        """Inicia el asistente visual"""
        if not st.session_state.is_running:
            st.session_state.is_running = True
            
            # Iniciar hilos
            self.frame_thread = threading.Thread(target=self.process_frames, daemon=True)
            self.analysis_thread = threading.Thread(target=self.analyze_frames, daemon=True)
            
            self.frame_thread.start()
            self.analysis_thread.start()
            
            # Mensaje de inicio
            self.audio_module.speak("Asistente visual activado. Empezando a analizar el entorno.")
            logger.info("Asistente iniciado")
            
            return True
        return False
    
    def stop_assistant(self):
        """Detiene el asistente visual"""
        if st.session_state.is_running:
            st.session_state.is_running = False
            
            # Esperar a que los hilos terminen
            if self.frame_thread and self.frame_thread.is_alive():
                self.frame_thread.join(timeout=2)
            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=2)
            
            # Limpiar colas
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Mensaje de parada
            self.audio_module.speak("Asistente visual desactivado.")
            logger.info("Asistente detenido")
            
            return True
        return False
    
    def render_dashboard(self):
        """Renderiza el dashboard principal"""
        # Título principal
        st.markdown('<div class="big-text">👁️ ASISTENTE VISUAL PARA PERSONAS INVIDENTES</div>', 
                   unsafe_allow_html=True)
        
        # Panel de estado
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_text = "🟢 ACTIVO" if st.session_state.is_running else "🔴 INACTIVO"
                st.metric("Estado", status_text)
            
            with col2:
                st.metric("Frames procesados", st.session_state.frame_count)
            
            with col3:
                st.metric("Objetos detectados", st.session_state.object_count)
        
        # Controles principales
        st.markdown("### 🎛️ CONTROLES PRINCIPALES")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ INICIAR ASISTENTE", type="primary", 
                        use_container_width=True,
                        disabled=st.session_state.is_running):
                if self.start_assistant():
                    st.rerun()
        
        with col2:
            if st.button("⏹️ DETENER ASISTENTE", 
                        use_container_width=True,
                        disabled=not st.session_state.is_running):
                if self.stop_assistant():
                    st.rerun()
        
        # Configuración
        with st.expander("⚙️ CONFIGURACIÓN", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                volume = st.slider("🔊 Volumen", 0.0, 1.0, 
                                  CONFIG['audio']['volume'], 0.1,
                                  help="Ajusta el volumen de la voz")
                self.audio_module.set_volume(volume)
            
            with col2:
                rate = st.slider("💬 Velocidad", 80, 250, 
                                CONFIG['audio']['rate'], 10,
                                help="Palabras por minuto")
                self.audio_module.set_rate(rate)
        
        # Última descripción
        if st.session_state.last_description:
            st.markdown("### 🔊 ÚLTIMA DESCRIPCIÓN")
            st.info(f"**{st.session_state.last_description}**")
        
        # Historial
        if st.session_state.detection_history:
            st.markdown("### 📜 HISTORIAL RECIENTE")
            
            for item in st.session_state.detection_history[:5]:
                with st.container():
                    st.markdown(f"""
                    <div class="history-item">
                        <strong>{item['timestamp']}</strong> - {item['description']}<br>
                        <small>Objetos: {item['objects']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Información del sistema
        with st.expander("ℹ️ INFORMACIÓN DEL SISTEMA", expanded=False):
            st.write(f"**Cámara:** {CONFIG['camera']['width']}x{CONFIG['camera']['height']} @ {CONFIG['camera']['fps']} FPS")
            st.write(f"**Modelo YOLO:** {CONFIG['yolo']['model']}")
            st.write(f"**Modelo LLM:** {CONFIG['ollama']['model']}")
            st.write(f"**Base de datos:** {'🟢 Conectada' if self.db_enabled else '🔴 Desconectada'}")
            
            if st.button("🗑️ Limpiar historial", key="clear_history"):
                st.session_state.detection_history = []
                st.session_state.last_description = ""
                st.rerun()
    
    def main(self):
        """Función principal de la aplicación"""
        self.render_dashboard()

def main():
    """Función de entrada de la aplicación"""
    try:
        # Inicializar aplicación
        app = VisionAssistantApp()
        
        # Sidebar con información
        with st.sidebar:
            st.image("https://img.icons8.com/color/96/000000/eye.png", width=100)
            st.markdown("### Asistente Visual")
            st.markdown("---")
            st.markdown("**Instrucciones:**")
            st.markdown("1. Haz clic en 'Iniciar Asistente'")
            st.markdown("2. El sistema describirá lo que ve")
            st.markdown("3. Usa 'Detener' para pausar")
            st.markdown("---")
            st.markdown("🔄 La aplicación se actualiza automáticamente")
        
        # Ejecutar aplicación principal
        app.main()
        
        # Footer
        st.markdown("---")
        st.markdown(
            "Desarrollado con ❤️ para personas invidentes | "
            "[Reportar problema](mailto:soporte@asistentevisual.org)",
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"❌ Error crítico: {str(e)}")
        logger.error(f"Error en la aplicación: {e}", exc_info=True)

if __name__ == "__main__":
    main()