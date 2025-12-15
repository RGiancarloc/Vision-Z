#!/usr/bin/env python3
"""Script de debug para verificar que los componentes funcionan."""

import sys
sys.path.insert(0, 'c:\\Users\\veras\\Music\\Vision-Z')

print("=" * 60)
print("DEBUG: Verificando componentes")
print("=" * 60)

# 1. Verificar YOLO
print("\n1. Verificando YOLO...")
try:
    from ultralytics import YOLO
    yolo = YOLO('yolov8n.pt')
    print("✓ YOLO cargado correctamente")
except Exception as e:
    print(f"✗ Error en YOLO: {e}")

# 2. Verificar Ollama
print("\n2. Verificando Ollama...")
try:
    import ollama
    models = ollama.list()
    print(f"✓ Ollama conectado. Modelos disponibles: {len(models.get('models', []))}")
    for model in models.get('models', [])[:3]:
        print(f"  - {model.get('name', 'Unknown')}")
except Exception as e:
    print(f"✗ Error en Ollama: {e}")
    print("  Asegúrate de que Ollama está corriendo: ollama serve")

# 3. Verificar gTTS
print("\n3. Verificando gTTS...")
try:
    from gtts import gTTS
    import io
    tts = gTTS(text="Prueba de audio", lang='es')
    buffer = io.BytesIO()
    tts.write_to_fp(buffer)
    print(f"✓ gTTS funcionando. Audio generado: {len(buffer.getvalue())} bytes")
except Exception as e:
    print(f"✗ Error en gTTS: {e}")

# 4. Verificar OpenCV
print("\n4. Verificando OpenCV...")
try:
    import cv2
    print(f"✓ OpenCV {cv2.__version__} cargado")
except Exception as e:
    print(f"✗ Error en OpenCV: {e}")

# 5. Verificar Streamlit
print("\n5. Verificando Streamlit...")
try:
    import streamlit
    print(f"✓ Streamlit {streamlit.__version__} cargado")
except Exception as e:
    print(f"✗ Error en Streamlit: {e}")

print("\n" + "=" * 60)
print("DEBUG: Verificación completada")
print("=" * 60)
