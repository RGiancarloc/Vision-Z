# pages/3_⚙️_Ajustes.py
import streamlit as st
import json

st.set_page_config(page_title="Ajustes", layout="centered")
st.title("⚙️ Ajustes de Ojo Electrónico")

st.header("Personalización de Voz")
# Aquí deberías listar las voces de Piper que el usuario ha descargado
available_voices = ["es_ES-dave-medium", "es_ES-carlfm-x-low", "otra_voz"]
selected_voice = st.selectbox("Elige una voz:", available_voices, index=available_voices.index(st.session_state.get("piper_voice", available_voices[0])))
voice_speed = st.slider("Velocidad de Voz:", 0.5, 2.0, float(st.session_state.get("voice_speed", 1.0)))

st.header("Funcionalidades de Seguridad")
fall_detection = st.checkbox("Activar Detección de Caídas", value=st.session_state.get("fall_detection_enabled", False))

if st.button("Guardar Ajustes"):
    st.session_state["piper_voice"] = selected_voice
    st.session_state["voice_speed"] = voice_speed
    st.session_state["fall_detection_enabled"] = fall_detection
    st.success("¡Ajustes guardados correctamente!")
    st.info("Reinicia el sistema por voz para que los cambios surtan efecto.")

st.markdown("---")
st.subheader("¿Cómo añadir más voces de Piper?")
st.markdown("""
1.  Ve a la [página de modelos de Piper en Hugging Face](https://huggingface.co/models?other=piper).
2.  Busca una voz en español (ej. `es_ES-...`).
3.  Descarga los archivos `.onnx` y `.json`.
4.  Colócalos en la misma carpeta que el ejecutable de Piper.
5.  Recarga esta página y la nueva voz debería aparecer en la lista.
""")

