# test_altavoces.py
import sounddevice as sd
import numpy as np

# ENCONTRAR EL ÍNDICE CORRECTO DE TUS ALTAVOCES
# Cambia este número por el que encontraste en el paso 1
INDICE_ALTAVOCES = 5  # <--- CAMBIA ESTE NÚMERO

print(f"🔊 Probando altavoces en índice {INDICE_ALTAVOCES}...")

fs = 44100
duracion = 2
t = np.linspace(0, duracion, int(fs * duracion))
tono = 0.5 * np.sin(2 * np.pi * 440 * t)

try:
    sd.play(tono, samplerate=fs, device=INDICE_ALTAVOCES)
    sd.wait()
    print(" Si escuchaste el tono, ¡funciona!")
except Exception as e:
    print(f" Error: {e}")