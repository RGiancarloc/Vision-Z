#!/usr/bin/env python3
import ollama
import json

print("=" * 60)
print("Verificando Ollama")
print("=" * 60)

try:
    models_list = ollama.list()
    models = models_list.get('models', [])
    
    print(f"\nTotal de modelos: {len(models)}")
    print("\nModelos disponibles:")
    
    for i, model in enumerate(models):
        name = model.get('name', 'Unknown')
        print(f"\n{i+1}. Nombre completo: {name}")
        print(f"   Tipo: {type(name)}")
        print(f"   Repr: {repr(name)}")
        
        # Limpiar el nombre
        modelo_limpio = name.split(':')[0] if ':' in name else name
        modelo_limpio = modelo_limpio.replace('/', '-').replace('_', '-').lower()
        print(f"   Limpio: {modelo_limpio}")
        
        # Intentar usar el modelo
        try:
            print(f"   Probando con modelo: {modelo_limpio}")
            response = ollama.generate(model=modelo_limpio, prompt="Hola")
            print(f"   ✓ Funciona!")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
            # Intentar con el nombre original
            try:
                print(f"   Probando con nombre original: {name}")
                response = ollama.generate(model=name, prompt="Hola")
                print(f"   ✓ Funciona con nombre original!")
            except Exception as e2:
                print(f"   ✗ Error con original: {e2}")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
