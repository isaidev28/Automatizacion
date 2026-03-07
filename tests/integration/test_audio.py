import sounddevice as sd
import numpy as np

print("=" * 60)
print("TEST DE AUDIO - VERIFICACIÓN COMPLETA")
print("=" * 60)

# 1. Listar dispositivos con sus frecuencias soportadas
print("\n1. DISPOSITIVOS DISPONIBLES:")
for i, d in enumerate(sd.query_devices()):
    if "CABLE" in d["name"] or "Altavoces" in d["name"]:
        print(f"\n   {i}: {d['name']}")
        print(f"      IN:{d['max_input_channels']} OUT:{d['max_output_channels']}")
        print(f"      Frecuencia predeterminada: {d['default_samplerate']} Hz")

# 2. Encontrar TODOS los CABLE Input
cable_inputs = []
for i, d in enumerate(sd.query_devices()):
    if "CABLE Input" in d["name"] and d["max_output_channels"] > 0:
        cable_inputs.append((i, d['name'], d['default_samplerate']))

print(f"\n✅ CABLE Inputs encontrados: {cable_inputs}")

# 3. Probar cada uno con su frecuencia NATIVA
for idx, nombre, sr in cable_inputs:
    print(f"\n2. REPRODUCIENDO TONO en dispositivo {idx} ({nombre})")
    print(f"   Frecuencia de muestreo: {sr} Hz")
    print("   ⏱️  Deberías ESCUCHAR un tono de 440Hz AHORA")
    
    try:
        # Usar la frecuencia NATIVA del dispositivo
        fs = int(sr) if sr else 48000  # Fallback a 48kHz si no hay
        
        # Generar tono de 440Hz
        duracion = 2
        t = np.linspace(0, duracion, int(fs * duracion))
        tono = 0.8 * np.sin(2 * np.pi * 440 * t)
        
        # Reproducir
        sd.play(tono, samplerate=fs, device=idx)
        sd.wait()
        print(f"   ✅ Reproducción exitosa en dispositivo {idx}")
        break  # Si uno funciona, terminamos
    except Exception as e:
        print(f"   ❌ Error en dispositivo {idx}: {e}")
        continue

print("\n3. VERIFICACIÓN DE CONFIGURACIÓN:")
print("   ✅ Escuchar este dispositivo: ACTIVADO (según tu imagen)")
print("   ✅ Dispositivo de reproducción: Altavoces (Realtek(R) Audio)")
print("")
print("⚠️  Si NO escuchaste el tono:")
print("   1. Verifica que los altavoces estén encendidos")
print("   2. Revisa el volumen en el mezclador:")
print("      - Clic derecho en altavoz → 'Abrir mezclador de volumen'")
print("      - Busca 'CABLE Input' y sube el volumen")
print("   3. Prueba con audífonos conectados directamente")