import queue
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json

# 1. Configuración de Buffer y Cola
# Usamos una cola para que el procesamiento no detenga la captura
audio_queue = queue.Queue()

def callback(indata, frames, time, status):
    """Solo mete los datos a la cola, no procesa nada aquí"""
    if status:
        # Imprimimos en stderr para no ensuciar la salida principal
        print(f"\rStatus: {status}", file=sys.stderr, end="")
    audio_queue.put(bytes(indata))

# 2. Carga del modelo
model = Model("/home/radxa/Documents/BMO/model")
rec = KaldiRecognizer(model, 16000)

# 3. Flujo principal
print("\n--- BMO: STT Estable (Fase 1) ---")
try:
    # Usamos hw:1,0 para tu manos libres AC101B
    # Aumentamos el blocksize para dar más aire a la CPU
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback, device='hw:1,0'):
        
        while True:
            data = audio_queue.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if result['text']:
                    print(f"\n>> FINAL: {result['text']}")
            else:
                partial = json.loads(rec.PartialResult())
                if partial['partial']:
                    sys.stdout.write(f"\rEntendiendo: {partial['partial']}... ")
                    sys.stdout.flush()

except KeyboardInterrupt:
    print("\nDetenido.")
