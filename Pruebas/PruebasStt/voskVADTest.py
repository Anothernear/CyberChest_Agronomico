import webrtcvad
import queue
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import os
import numpy as np

PIPE_PATH = "/tmp/bmo_pipe"
DEV_ID = 'hw:1,0'
audio_queue = queue.Queue()

# Agresividad en 1 (permisivo) o 2 (balanceado)
vad = webrtcvad.Vad(1) 

def callback(indata, frames, time, status):
    # indata viene como float32 o int16 según dtype
    audio_queue.put(indata.copy())

model = Model("/home/radxa/Documents/BMO/model")
rec = KaldiRecognizer(model, 16000)

print("\n--- BMO Fase 2: VAD Calibrado ---")

try:
    # blocksize de 480 para 16000Hz son exactamente 30ms
    with sd.InputStream(samplerate=16000, blocksize=480, dtype='int16',
                         channels=1, callback=callback, device=DEV_ID):
        
        is_speaking = False
        
        while True:
            frame_int16 = audio_queue.get()
            
            # Convertimos a bytes para el VAD
            raw_bytes = frame_int16.tobytes()
            
            # Detección de voz
            try:
                detectado = vad.is_speech(raw_bytes, 16000)
            except:
                continue

            if detectado:
                if not is_speaking:
                    os.system(f'echo "sorpresa" > {PIPE_PATH} 2>/dev/null &')
                    is_speaking = True
                
                if rec.AcceptWaveform(raw_bytes):
                    result = json.loads(rec.Result())
                    if result['text']:
                        print(f"\n>> BMO: {result['text']}")
                else:
                    partial = json.loads(rec.PartialResult())
                    if partial['partial']:
                        sys.stdout.write(f"\rEscuchando: {partial['partial']}... ")
                        sys.stdout.flush()
            else:
                if is_speaking:
                    is_speaking = False
                    sys.stdout.write("\n(En espera)\n")
                    os.system(f'echo "normal" > {PIPE_PATH} 2>/dev/null &')

except KeyboardInterrupt:
    print("\nFase 2 detenida.")
