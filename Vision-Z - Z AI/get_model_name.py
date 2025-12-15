#!/usr/bin/env python3
import subprocess
import json

print("Obteniendo lista de modelos con ollama list...")

try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
