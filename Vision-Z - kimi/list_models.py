#!/usr/bin/env python3
import ollama

try:
    models = ollama.list()
    print("Modelos disponibles en Ollama:")
    print("=" * 50)
    for model in models.get('models', []):
        name = model.get('name', 'Unknown')
        print(f"  - {name}")
    print("=" * 50)
except Exception as e:
    print(f"Error: {e}")
    print("Asegúrate de que Ollama está corriendo: ollama serve")
