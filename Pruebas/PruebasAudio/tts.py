import os, subprocess, numpy as np, requests, sys
from faster_whisper import WhisperModel

# --- CONFIGURACIÓN ---
DEVICE = "plughw:1,0" 
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELO_LLM = "phi3:mini" # <--- CAMBIADO PARA COINCIDIR CON TU LISTA

print("[SISTEMA] Cargando Cerebro Auditivo (Faster-Whisper)...")
try:
    # 'tiny' con int8 es lo más veloz para la Radxa Cubie
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("[OK] BMO ha despertado exitosamente.")
except Exception as e:
    print(f"[ERROR CRÍTICO] {e}")
    sys.exit(1)

def hablar(texto):
    """Voz de BMO con espeak-ng"""
    print(f"\n[BMO]: {texto}")
    # es-mx para acento mexicano
    cmd = f'espeak-ng -v es-mx -s 160 "{texto}" --stdout | aplay -D {DEVICE} -q'
    subprocess.run(cmd, shell=True)

def chat_bmo(pregunta):
    """Conexión con el servicio Ollama que ya tienes activo"""
    payload = {
        "model": MODELO_LLM, 
        "prompt": f"Eres BMO, asistente de Brandon en la UACh. Responde en español, muy breve: {pregunta}", 
        "stream": False
    }
    try:
        # Timeout de 45s porque la Radxa en CPU-only tarda en procesar
        r = requests.post(OLLAMA_URL, json=payload, timeout=45)
        if r.status_code == 200:
            return r.json().get('response', "¡Rayos! Mi cerebro hizo corto.")
        else:
            return f"Error de Ollama: Código {r.status_code}"
    except Exception as e:
        return "No pude conectar con el servicio Ollama. Revisa 'systemctl status ollama'."

def iniciar_bmo():
    # arecord captura audio de la Radxa Cubie
    cmd_audio = ['arecord', '-D', DEVICE, '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'raw', '-q']
    
    try:
        proc = subprocess.Popen(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        print("\n" + "="*45)
        print("   BMO v14.3 - RADXA CUBIE (CULTIVAI)")
        print(f"   MODELO: {MODELO_LLM} | UACh IIAA")
        print("="*45)
        
        buffer_audio, hablando, silencio = [], False, 0

        while True:
            raw = proc.stdout.read(3200) # Bloques de 0.1s
            if not raw: break
            
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio**2))

            # Umbral de 0.12 para el ruido de la Radxa
            if rms > 0.12: 
                if not hablando: print("\n[!] Escuchando...", end='', flush=True)
                hablando, silencio = True, 0
                buffer_audio.append(audio)
            else:
                if hablando:
                    silencio += 1
                    # Tras 0.5s de silencio, procesamos
                    if silencio > 5: 
                        print(" [Procesando...]")
                        wav = np.concatenate(buffer_audio)
                        
                        # Transcripción forzada a español
                        segments, _ = model.transcribe(wav, beam_size=1, language="es")
                        txt = " ".join([s.text for s in segments]).strip()
                        
                        if txt:
                            print(f" >>> USER: {txt}")
                            hablar(chat_bmo(txt))
                        
                        buffer_audio, hablando, silencio = [], False, 0
                else:
                    # Monitor para ver el volumen ambiental
                    print(f" [Monitor] Vol: {rms:.4f} ", end='\r', flush=True)

    except KeyboardInterrupt:
        print("\n[BMO] ¡Adiós Brandon!")
    finally:
        if 'proc' in locals(): proc.terminate()

if __name__ == "__main__":
    iniciar_bmo()
