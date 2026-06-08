import webrtcvad, queue, sys, socket, json, os, time, subprocess, threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer

BmoBase = "/home/radxa/Documents/BMO"
SocketBrain = "/tmp/bmo_brain.sock"
SocketEar = "/tmp/bmo_ear.sock"
SocketAudio = "/tmp/bmo_audio.sock"
DevId = 1 # Según tus logs, el ID 1 es el que abrió con éxito

def AjustarGanancia():
    try:
        subprocess.run(["amixer", "-c", "1", "sset", "ADC2", "180"], check=False)
        subprocess.run(["amixer", "-c", "1", "sset", "ADC2 Gain", "15"], check=False)
        print("[SISTEMA] Sensibilidad ajustada para reducir ruido de fondo.")
    except: pass

audio_queue = queue.Queue()
EscuchandoActivo = True
SordoTemporal = False 

# VAD nivel 3: El más agresivo para filtrar ruido no humano
vad = webrtcvad.Vad(3)

def LimpiarCola():
    while not audio_queue.empty():
        try: audio_queue.get_nowait()
        except queue.Empty: break

def Hablar(Texto, Modo="robot"):
    global SordoTemporal
    def _hablar():
        global SordoTemporal
        try:
            SordoTemporal = True
            LimpiarCola()
            S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            S.connect(SocketAudio)
            S.sendall(f"{Modo}|{Texto}".encode("utf-8"))
            S.close()
            # Espera proporcional al texto
            time.sleep(len(Texto) * 0.08 + 1.0)
            LimpiarCola()
        finally:
            SordoTemporal = False
    threading.Thread(target=_hablar, daemon=True).start()

def EnviarAlCerebro(Texto):
    global EscuchandoActivo
    # Filtrar basura: frases de 1 sola palabra corta suelen ser ruido
    if len(Texto.split()) == 1 and len(Texto) < 4:
        print(f"[DESCARTADO] Ruido detectado como: {Texto}")
        return

    try:
        EscuchandoActivo = False 
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketBrain)
        S.sendall(Texto.encode("utf-8"))
        S.close()
        print(f"\n[→ BRAIN] {Texto}")
    except:
        EscuchandoActivo = True

def callback(indata, frames, time, status):
    if EscuchandoActivo and not SordoTemporal:
        audio_queue.put(indata.copy())

def AbrirMicro():
    # Usamos directamente el ID 1 que ya sabemos que funciona en tu Radxa
    return sd.InputStream(samplerate=16000, blocksize=480, dtype='int16',
                         channels=1, callback=callback, device=DevId)

# Inicialización
AjustarGanancia()
model = Model(os.path.join(BmoBase, "model"))
rec = KaldiRecognizer(model, 16000)

if os.path.exists(SocketEar): os.remove(SocketEar)
SrvCmd = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
SrvCmd.setblocking(False)
SrvCmd.bind(SocketEar)
SrvCmd.listen(1)

print("[LISTO] BMO OÍDO v7.5 - FILTRADO AGRESIVO")

try:
    mic = AbrirMicro()
    mic.start()
    is_speaking = False

    while True:
        try:
            Conn, _ = SrvCmd.accept()
            Cmd = Conn.recv(1024).decode(); Conn.close()
            if "REANUDAR" in Cmd:
                # PURGA TOTAL antes de volver a escuchar
                time.sleep(0.5) 
                LimpiarCola()
                rec.Reset()
                EscuchandoActivo = True
                print("[SISTEMA] Oído limpio y reanudado.")
        except: pass

        if not EscuchandoActivo:
            time.sleep(0.1)
            continue

        try:
            frame = audio_queue.get(timeout=0.1)
        except queue.Empty: continue

        raw = frame.tobytes()
        if len(raw) != 960: continue

        # El VAD nivel 3 es clave aquí
        if vad.is_speech(raw, 16000):
            if not is_speaking:
                is_speaking = True
            
            if rec.AcceptWaveform(raw):
                res = json.loads(rec.Result()).get('text', '').strip()
                if res:
                    EnviarAlCerebro(res)
        else:
            if is_speaking:
                is_speaking = False
                final = json.loads(rec.FinalResult()).get('text', '').strip()
                if final:
                    EnviarAlCerebro(final)

except KeyboardInterrupt: pass
finally:
    if 'mic' in locals(): mic.stop(); mic.close()
