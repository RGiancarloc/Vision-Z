import streamlit as st
import cv2
import pickle
from pathlib import Path
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import av
import face_recognition

st.set_page_config(page_title="Registrar Rostros", layout="centered")
st.title("👤 Registrar Rostros Conocidos")

st.markdown("""
Usa esta página para registrar los rostros de tus amigos y familiares. 
La aplicación aprenderá a reconocerlos y los nombrará cuando aparezcan.
""")

class FaceRegistrationProcessor(VideoTransformerBase):
    def __init__(self):
        self.capture_frame = False

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        if self.capture_frame:
            st.session_state["frame_to_register"] = img
            self.capture_frame = False
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# Cargar rostros conocidos
def load_known_faces():
    if Path("faces.pkl").exists():
        with open("faces.pkl", "rb") as f:
            return pickle.load(f)
    return {}

known_faces = load_known_faces()
st.write(f"Actualmente hay {len(known_faces)} rostros registrados.")

# Interfaz de registro
name_input = st.text_input("Nombre de la persona:")
ctx = webrtc_streamer(
    key="registration_camera",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"video": True, "audio": False},
    video_processor_factory=FaceRegistrationProcessor,
)

if ctx.state.playing:
    if st.button("📸 Capturar Rostro"):
        if not name_input:
            st.warning("Por favor, introduce un nombre.")
        else:
            # Indicar al procesador que capture el siguiente frame
            ctx.video_processor.capture_frame = True

# Procesamiento del frame capturado
if "frame_to_register" in st.session_state:
    frame = st.session_state["frame_to_register"]
    st.image(frame, channels="BGR", caption="Frame capturado para registro.")
    
    with st.spinner("Procesando rostro..."):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if len(face_locations) == 0:
            st.error("No se detectó ningún rostro en la imagen. Inténtalo de nuevo.")
        elif len(face_locations) > 1:
            st.error("Se detectaron múltiples rostros. Por favor, captura una imagen con una sola cara.")
        else:
            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
            known_faces[name_input] = face_encoding
            
            # Guardar en el archivo
            with open("faces.pkl", "wb") as f:
                pickle.dump(known_faces, f)
            
            st.success(f"¡Rostro de '{name_input}' registrado con éxito!")
            # Limpiar el frame de la sesión
            del st.session_state["frame_to_register"]
            st.rerun()
