import os, sys, subprocess, numpy as np, pyaudio, time
from faster_whisper import WhisperModel
import ollama

# --- CONFIGURACIÓN DE HARDWARE ---
MIC_ID = 1
RATE = 16000
CHUNK = 1024 # Chunk pequeño para no perder muestras
UMBRAL_VOZ = 4500 # Umbral bajo para mantener la grabación activa
UMBRAL_DESPERTAR = 14000 

print("\n[SISTEMA] Iniciando BMO v5.2 (Modo Continuo)...")
# Usamos Whisper 'base' para evitar las "Voces" de 'tiny'
stt_model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)

def hablar(texto):
    print(f"\n [BMO] >> {texto}")
    # Espeak directo al hardware
    comando = f'espeak-ng -v es-mx -s 170 "{texto}" --stdout | aplay -D plughw:1,0 -r 8000 -f S16_LE -c 1 2>/dev/null'
    subprocess.run(comando, shell=True)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, 
                input=True, input_device_index=MIC_ID, 
                frames_per_buffer=CHUNK)

print("\n" + "="*45)
print("   BMO v5.2 - SMART RECORDING (IIAA)")
print("="*45)

try:
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            potencia = np.max(np.abs(np.frombuffer(data, dtype=np.int16)))
        except: continue

        print(f" [Monitor] Nivel: {potencia:5}", end='\r')

        if potencia >= UMBRAL_DESPERTAR:
            sys.stdout.write('\033[K')
            print(f"\n ✨ ¡TE ESCUCHO! (Pico: {potencia})")
            hablar("¿Dime?")
            
            # --- FASE DE GRABACIÓN DINÁMICA ---
            print(" [SISTEMA] Grabando hasta que guardes silencio...")
            frames_q = []
            silencio_cont = 0
            
            # Limpiar buffer antes de empezar
            while stream.get_read_available() > 0: stream.read(CHUNK, exception_on_overflow=False)

            # Bucle de escucha activa
            for _ in range(0, int(RATE / CHUNK * 10)): # Máximo 10 segundos
                chunk_data = stream.read(CHUNK, exception_on_overflow=False)
                frames_q.append(chunk_data)
                
                p_chunk = np.max(np.abs(np.frombuffer(chunk_data, dtype=np.int16)))
                
                if p_chunk < UMBRAL_VOZ:
                    silencio_cont += 1
                else:
                    silencio_cont = 0
                
                # Si hay medio segundo de silencio y ya grabamos algo, cortamos
                if silencio_cont > 8 and len(frames_q) > 15:
                    break

            # --- PROCESAMIENTO ---
            print(" [SISTEMA] Procesando audio dinámico...")
            audio_q = np.frombuffer(b''.join(frames_q), dtype=np.int16).astype(np.float32) / 32768.0
            
            # Eliminamos el ruido de fondo restando la media
            audio_q = audio_q - np.mean(audio_q)
            audio_q = audio_q / (np.max(np.abs(audio_q)) + 1e-6)

            seg_q, _ = stt_model.transcribe(
                audio_q, language="es", beam_size=5,
                initial_prompt="Operación matemática corta."
            )
            pregunta = " ".join([s.text for s in seg_q]).strip()

            if len(pregunta) > 2:
                print(f" [USER]: '{pregunta}'")
                try:
                    # Usamos gemma:2b para respuestas más coherentes que tinyllama
                    res = ollama.chat(model='gemma:2b', messages=[
                        {'role': 'system', 'content': 'Eres BMO. Solo responde el resultado de la operación matemática, sin texto extra.'},
                        {'role': 'user', 'content': pregunta}
                    ])
                    hablar(res['message']['content'])
                except:
                    hablar("Error en el cerebro.")
            else:
                print(" [!] No se detectó mensaje.")
            
            print("\n >> Esperando...")

except KeyboardInterrupt:
    stream.stop_stream()
    p.terminate()
