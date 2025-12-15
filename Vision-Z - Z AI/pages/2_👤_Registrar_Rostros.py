import streamlit as st
import cv2
import pickle
from pathlib import Path
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import av

# --- IMPORT OPCIONAL DE face_recognition ---
try:
    import face_recognition
    HAS_FACE_RECOG = True
except ImportError:
    face_recognition = None
    HAS_FACE_RECOG = False

st.set_page_config(page_title="Registrar Rostros", layout="centered")
st.title("👤 Registrar Rostros Conocidos")

st.markdown("""
Usa esta página para registrar los rostros de tus amigos y familiares. 
La aplicación aprenderá a reconocerlos y los nombrará cuando aparezcan.
""")

# Si no está instalada la librería, mostramos aviso y salimos de la página
if not HAS_FACE_RECOG:
    st.error(
        "La funcionalidad de **registro de rostros** requiere la librería "
        "`face_recognition`, que no está instalada en este entorno."
    )
    st.info(
        "Puedes seguir usando el resto de la aplicación. Cuando logres instalar "
        "`face_recognition`, vuelve a esta página para registrar rostros."
    )
    st.stop()

# ---------------- ESTADO ----------------
st.session_state.setdefault("capture_stage", 0)        # 0: listo para capturar, 1: listo para guardar
st.session_state.setdefault("pending_name", "")        # nombre asociado al frame
st.session_state.setdefault("info_msg", "")            # mensaje informativo

# ---------------- CARGA DE ROSTROS ----------------
def load_known_faces():
    if Path("faces.pkl").exists():
        try:
            with open("faces.pkl", "rb") as f:
                return pickle.load(f)
        except Exception as e:
            st.warning(f"No se pudo cargar faces.pkl: {e}")
    return {}

known_faces = load_known_faces()
st.write(f"Actualmente hay **{len(known_faces)}** rostros registrados.")

# ---------------- PROCESADOR DE VIDEO ----------------
class FaceRegistrationProcessor(VideoTransformerBase):
    def __init__(self):
        self.capture_frame = False
        self.latest_frame = None  # aquí guardamos el último frame capturado

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        # Si se ha solicitado captura, guardamos este frame
        if self.capture_frame:
            self.latest_frame = img
            self.capture_frame = False

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ---------------- INTERFAZ ----------------
name_input = st.text_input("Nombre de la persona:")

ctx = webrtc_streamer(
    key="registration_camera",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"video": True, "audio": False},
    video_processor_factory=FaceRegistrationProcessor,
)

# Mostrar mensaje de ayuda / estado
if st.session_state["info_msg"]:
    st.info(st.session_state["info_msg"])

# Lógica del botón de dos etapas
button_label = "📸 Capturar Rostro" if st.session_state["capture_stage"] == 0 else "✅ Guardar Rostro Capturado"

if ctx.state.playing:
    if st.button(button_label):
        # ETAPA 0: pedir captura al procesador
        if st.session_state["capture_stage"] == 0:
            if not name_input.strip():
                st.warning("Por favor, introduce un nombre antes de capturar.")
            elif ctx.video_processor is None:
                st.warning("La cámara todavía se está inicializando. Intenta de nuevo en 1 segundo.")
            else:
                st.session_state["pending_name"] = name_input.strip()
                ctx.video_processor.capture_frame = True
                st.session_state["capture_stage"] = 1
                st.session_state["info_msg"] = (
                    "Rostro capturado. Mantén la posición y vuelve a pulsar "
                    "'✅ Guardar Rostro Capturado' para registrar."
                )

        # ETAPA 1: usar el frame capturado y registrar
        elif st.session_state["capture_stage"] == 1:
            vp = ctx.video_processor
            if vp is None or vp.latest_frame is None:
                st.warning(
                    "Todavía no tengo una imagen capturada. Espera un momento con la cámara encendida "
                    "y vuelve a pulsar el botón."
                )
            else:
                frame = vp.latest_frame
                person_name = st.session_state.get("pending_name", "").strip()
                st.image(frame, channels="BGR", caption=f"Frame capturado para '{person_name}'")

                if not person_name:
                    st.error("No hay nombre asociado al rostro capturado. Intenta de nuevo.")
                else:
                    with st.spinner("Procesando rostro..."):
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_frame)

                        if len(face_locations) == 0:
                            st.error("No se detectó ningún rostro en la imagen. Inténtalo de nuevo.")
                        elif len(face_locations) > 1:
                            st.error("Se detectaron múltiples rostros. Por favor, captura una imagen con una sola cara.")
                        else:
                            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                            known_faces[person_name] = face_encoding

                            # Guardar en archivo
                            try:
                                with open("faces.pkl", "wb") as f:
                                    pickle.dump(known_faces, f)
                                st.success(f"¡Rostro de '{person_name}' registrado con éxito!")
                            except Exception as e:
                                st.error(f"Error al guardar faces.pkl: {e}")

                            # Reiniciar estado
                            st.session_state["capture_stage"] = 0
                            st.session_state["pending_name"] = ""
                            st.session_state["info_msg"] = ""
                            # Limpiamos el frame del procesador
                            vp.latest_frame = None
                            st.rerun()
else:
    st.info("Enciende la cámara con el botón **START** de arriba para poder capturar.")
