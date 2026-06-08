import subprocess, numpy as np, time, os
from faster_whisper import WhisperModel

os.environ["HF_HUB_OFFLINE"] = "1"
DEVICE = "plughw:1,0"
RATE = 16000
CHUNK_READ = 2048 

print("\n[SISTEMA] Cargando Whisper Tiny (Local)...")
model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)

def hablar(texto):
    print(f"\n [BMO] >> {texto}")
    subprocess.run(f'espeak-ng -v es-mx -s 165 "{texto}" --stdout | aplay -D plughw:1,0 -q', shell=True)

def iniciar_bmo():
    # Arecord con buffer pequeño para evitar lag
    cmd = ['arecord', '-D', DEVICE, '-f', 'S16_LE', '-r', str(RATE), '-c', '1', '-t', 'raw', '-q']
    proc = subprocess.PIPE
    
    print("\n" + "="*45)
    print("   BMO v9.7 - TIEMPO FORZADO (UACh)")
    print("   Habla en cuanto veas 'GRABANDO'")
    print("="*45)

    try:
        while True:
            # Reiniciamos el proceso de arecord en cada ciclo para limpiar el buffer de ALSA
            p = subprocess.Popen(cmd, stdout=proc, stderr=subprocess.DEVNULL)
            
            # 1. ESPERA DE ENERGÍA (Trigger)
            print(" [Monitor] Esperando sonido...          ", end='\r')
            while True:
                raw = p.stdout.read(CHUNK_READ * 2)
                data = np.frombuffer(raw, dtype=np.int16)
                if np.max(np.abs(data - np.mean(data))) > 1500: # Umbral de disparo
                    break
            
            # 2. GRABACIÓN FORZADA (4 segundos)
            print("\n 🔴 GRABANDO... (4s) ", end='', flush=True)
            frames = [raw]
            for _ in range(int(RATE / CHUNK_READ * 4)):
                frames.append(p.stdout.read(CHUNK_READ * 2))
                print(".", end='', flush=True)
            
            p.terminate() # Matamos arecord para que la CPU respire
            
            # 3. PROCESAMIENTO
            print("\n 🧠 PROCESANDO...")
            audio = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
            audio -= np.mean(audio) # Filtro de offset
            
            segments, _ = model.transcribe(audio, language="es")
            frase = " ".join([s.text for s in segments]).strip()
            
            if len(frase) > 1:
                print(f" >>> OÍ: {frase}")
                if "hola" in frase.lower(): hablar("Hola Brandon")
                # AQUÍ CONECTAREMOS EL RAG
            else:
                print(" >>> (No entendí nada)")
            
            print("-" * 30)

    except KeyboardInterrupt:
        print("\n\n[SISTEMA] Apagado.")

if __name__ == "__main__":
    iniciar_bmo()
