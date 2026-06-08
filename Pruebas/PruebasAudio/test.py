import os, pyaudio, numpy as np, ollama, time
from openwakeword.model import Model
from faster_whisper import WhisperModel

# --- LA CLAVE ES EL ID 0 ---
MIC_ID = 0  
BMO_PIPE = "/tmp/bmo_pipe"
MODEL_PATH = "/home/radxa/Documents/BMO/models/alexa_v0.1.tflite"
PIPER_EXE = "/home/radxa/Documents/BMO/piper/piper"
PIPER_VOICE = "/home/radxa/Documents/BMO/piper/voices/es_MX-claude-medium.onnx"

audio = pyaudio.PyAudio()
oww_model = Model(wakeword_models=[MODEL_PATH], inference_framework="tflite")
stt_model = WhisperModel("tiny", device="cpu", compute_type="int8")

# Abrimos el stream en la tarjeta 0
stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, 
                    input_device_index=MIC_ID, frames_per_buffer=1280)

def bmo_hablar(texto):
    if not os.path.exists(PIPER_VOICE): return
    os.system(f'echo "hablar" > {BMO_PIPE} &')
    # Cambiado a plughw:0,0 para que coincida con tu hardware
    os.system(f'echo "{texto}" | {PIPER_EXE} --model {PIPER_VOICE} --output_raw | aplay -D plughw:0,0 -r 22050 -f S16_LE -t raw')
    os.system(f'echo "normal" > {BMO_PIPE} &')

print("\n🚀 BMO CONECTADO AL MICRÓFONO CORRECTO (ID 0)")
print("Grita 'ALEXA' para probar...")

while True:
    try:
        data = stream.read(1280, exception_on_overflow=False)
        frame = np.frombuffer(data, dtype=np.int16)
        
        # Monitor de potencia real
        potencia = np.sqrt(np.mean(frame.astype(np.float32)**2))
        
        prediction = oww_model.predict(frame)
        conf = prediction.get('alexa_v0.1', 0)
        
        # Si la potencia es mayor a 100, ya hay señal física
        print(f"POTENCIA: {int(potencia):5} | CONFIANZA: {conf:.4f}", end='\r')

        if conf > 0.35:
            print(f"\n✨ ¡DESPIERTO! Confianza: {conf:.2f}")
            bmo_hablar("¡Por fin me escuchas, Fabian!")
            # Aquí sigue tu lógica de escucha...
            
    except KeyboardInterrupt: break
