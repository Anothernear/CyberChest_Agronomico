import webrtcvad, queue, sys, socket, json, os, time, subprocess, threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Configuración de rutas
BmoBase = "/home/radxa/Documents/BMO"
SocketBrain = "/tmp/bmo_brain.sock"
# ID 1 para el chip Allwinner A733 de la Radxa
DevId = 1 

def enviar_emocion(emocion):
    try:
        # Abrimos el pipe en modo escritura
        with open("/tmp/bmo_pipe", "w") as pipe:
            pipe.write(f"{emocion}\n")
    except Exception as e:
        print(f"Error al enviar emoción: {e}")

def AjustarGanancia():
    """Configura el hardware de audio para reducir ruido de fondo"""
    try:
        subprocess.run(["amixer", "-c", "1", "sset", "ADC2", "180"], check=False)
        subprocess.run(["amixer", "-c", "1", "sset", "ADC2 Gain", "15"], check=False)
    except: pass

audio_queue = queue.Queue()
EscuchandoActivo = True 
vad = webrtcvad.Vad(1) # Nivel 1: El menos agresivo

def EnviarAlCerebro(Texto):
    """Envía el texto y mata el proceso para forzar el reinicio del lanzador"""
    # Filtro básico de ruido
    if len(Texto.split()) == 1 and len(Texto) < 4:
        enviar_emocion("pensar")
        enviar_emocion("normal")
        return

    try:
        enviar_emocion("sorpresa")
        # 1. Enviar datos al Cerebro
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketBrain)
        S.sendall(Texto.encode("utf-8"))
        S.close()
        print(f"\n[→ BRAIN] {Texto}")
        
        # 2. Pequeña pausa para asegurar el envío
        time.sleep(1.5) 
        
        # 3. EL MARTILLAZO: Matamos el script para que lanzador.sh reinicie todo
        print("[SISTEMA] Cerrando Oído para reinicio de hardware...")
        enviar_emocion("normal")
        os._exit(0) 
    except Exception as e:
        enviar_emocion("llorar")
        print(f"[ERROR] No se pudo conectar con el Cerebro: {e}")

def callback(indata, frames, time_info, status):
    """Captura audio y maneja el fallback de canales si es necesario"""
    if EscuchandoActivo:
        if indata.shape[1] > 1:
            audio_queue.put(indata[:, 0].copy())
        else:
            audio_queue.put(indata.copy())

def AbrirMicro():
    """Intenta abrir el micro en Mono, si falla intenta Stereo (común en errores -9998)"""
    try:
        return sd.InputStream(samplerate=16000, blocksize=480, dtype='int16',
                             channels=1, callback=callback, device=DevId)
    except:
        # Fallback a 2 canales para evitar el bloqueo del driver
        return sd.InputStream(samplerate=16000, blocksize=480, dtype='int16',
                             channels=2, callback=callback, device=DevId)

# --- INICIALIZACIÓN ---
AjustarGanancia()
model = Model(os.path.join(BmoBase, "model"))
rec = KaldiRecognizer(model, 16000)

print("[LISTO] BMO OÍDO v9.0 - MODO ITERATIVO")
enviar_emocion("guiño")
enviar_emocion("normal")

try:
    mic = AbrirMicro()
    mic.start()
    is_speaking = False

    while True:
        try:
            frame = audio_queue.get(timeout=0.1)
        except queue.Empty: continue

        raw = frame.tobytes()
        if len(raw) != 960: continue

        # Detección de voz (VAD)
        if vad.is_speech(raw, 16000):
            if not is_speaking: is_speaking = True
            
            if rec.AcceptWaveform(raw):
                res = json.loads(rec.Result()).get('text', '').strip()
                if res: EnviarAlCerebro(res)
        else:
            if is_speaking:
                is_speaking = False
                final = json.loads(rec.FinalResult()).get('text', '').strip()
                if final: EnviarAlCerebro(final)

except KeyboardInterrupt:
    os._exit(0)
    enviar_emocion("muerto")
finally:
    if 'mic' in locals():
        mic.stop()
        mic.close()
        enviar_emocion("dormido")
        enviar_emocion("normal")
