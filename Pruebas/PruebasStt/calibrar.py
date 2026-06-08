import sounddevice as sd
import numpy as np
import time

DEV = 'hw:1,0'

def rms(data):
    muestras = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    return np.sqrt(np.mean(muestras ** 2))

print("═"*40)
print(" CALIBRADOR DE MICRÓFONO BMO")
print("═"*40)

with sd.InputStream(samplerate=16000, blocksize=4000,
                    device=DEV, dtype='int16', channels=1) as Stream:

    print("\n[1/2] QUÉDATE EN SILENCIO — midiendo ruido de fondo...")
    time.sleep(1)
    RuidoFondo = []
    for _ in range(20):
        Data, _ = Stream.read(4000)
        R = rms(bytes(Data))
        RuidoFondo.append(R)
        print(f"  ruido: {R:.0f}")
        time.sleep(0.15)

    MaxRuido = max(RuidoFondo)
    print(f"\n  → Ruido de fondo máximo: {MaxRuido:.0f}")

    print("\n[2/2] HABLA NORMAL — di algo como 'qué son los GDD'...")
    time.sleep(0.5)
    RuidoVoz = []
    for _ in range(30):
        Data, _ = Stream.read(4000)
        R = rms(bytes(Data))
        RuidoVoz.append(R)
        print(f"  voz: {R:.0f}")
        time.sleep(0.15)

    MaxVoz = max(RuidoVoz)
    print(f"\n  → Voz máxima detectada: {MaxVoz:.0f}")

# Calcular umbral recomendado
Umbral = int(MaxRuido + (MaxVoz - MaxRuido) * 0.4)

print("\n═"*40)
print(f" Ruido fondo : {MaxRuido:.0f}")
print(f" Voz máxima  : {MaxVoz:.0f}")
print(f" UMBRAL RECOMENDADO: {Umbral}")
print("═"*40)
print(f"\n→ En BmoEar.py cambia la línea:")
print(f"  UMBRAL_VOZ = {Umbral}")
