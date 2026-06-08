import webrtcvad, queue, sys, socket, json, os, time
import sounddevice as sd
from vosk import Model, KaldiRecognizer

BmoBase     = "/home/radxa/Documents/BMO"
SocketBrain = "/tmp/bmo_brain.sock"
SocketEar   = "/tmp/bmo_ear.sock"
SocketAudio = "/tmp/bmo_audio.sock"
DevId       = 'hw:1,0'

SI_WORDS  = {"si", "sí", "correcto", "exacto", "afirmativo", "adelante"}
NO_WORDS  = {"no", "mal", "incorrecto", "repite", "otra"}

audio_queue      = queue.Queue()
EscuchandoActivo = True
vad              = webrtcvad.Vad(1)

ESCUCHANDO  = "escuchando"
CONFIRMANDO = "confirmando"
PROCESANDO  = "procesando"
Estado    = ESCUCHANDO
Pregunta  = ""

# Acumulador de frames de voz
FramesVoz        = []
FramesSilencio   = 0
SILENCIO_FRAMES  = 20  # 20 frames x 30ms = 600ms de silencio → procesa

def Hablar(Texto, Modo="robot"):
    try:
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketAudio)
        S.sendall(f"{Modo}|{Texto}".encode("utf-8"))
        S.close()
    except: pass

def EnviarAlCerebro(Texto):
    try:
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketBrain)
        S.sendall(Texto.encode("utf-8"))
        S.close()
        print(f"\n[→ BRAIN] {Texto}")
    except Exception as E:
        print(f"[EAR] Error: {E}")

def callback(indata, frames, time, status):
    if EscuchandoActivo:
        audio_queue.put(indata.copy())

print("[1/3] Cargando Vosk...")
try:
    model = Model(os.path.join(BmoBase, "model"))
    rec   = KaldiRecognizer(model, 16000)
    print("[2/3] Modelo cargado.")
except Exception as E:
    print(f"[ERROR]: {E}"); sys.exit()

if os.path.exists(SocketEar): os.remove(SocketEar)
SrvCmd = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
SrvCmd.setblocking(False)
try:
    SrvCmd.bind(SocketEar); SrvCmd.listen(1)
except: pass

print("[3/3] Stream iniciado.")
print("═"*45)
print(" BMO OÍDO v5.4 - ACUMULADOR DE VOZ")
print("═"*45)
time.sleep(1)
Hablar("Sistema listo. Habla cuando quieras.")

try:
    with sd.InputStream(samplerate=16000, blocksize=480, dtype='int16',
                        channels=1, callback=callback, device=DevId):
        while True:

            try:
                Conn, _ = SrvCmd.accept()
                Cmd = Conn.recv(1024).decode(); Conn.close()
                if "PAUSA" in Cmd:
                    EscuchandoActivo = False
                    Estado = PROCESANDO
                    FramesVoz = []
                if "REANUDAR" in Cmd:
                    EscuchandoActivo = True
                    Estado = ESCUCHANDO
                    Pregunta = ""
                    FramesVoz = []
                    Hablar("Listo. Puedes hacer otra pregunta.")
            except: pass

            if not EscuchandoActivo:
                try:
                    while True: audio_queue.get_nowait()
                except: pass
                time.sleep(0.05)
                continue

            try:
                frame = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            raw = frame.tobytes()

            try:
                es_voz = vad.is_speech(raw, 16000)
            except:
                continue

            if Estado == PROCESANDO:
                continue

            if es_voz:
                FramesSilencio = 0
                FramesVoz.append(raw)
                # Mostrar que está escuchando
                sys.stdout.write(f"\r[MIC] Grabando... {len(FramesVoz)} frames")
                sys.stdout.flush()

            else:
                if FramesVoz:
                    FramesSilencio += 1

                    if FramesSilencio >= SILENCIO_FRAMES:
                        # Mandar todo el audio acumulado a Vosk de una vez
                        print(f"\n[VAD] Silencio → procesando {len(FramesVoz)} frames")
                        AudioCompleto = b"".join(FramesVoz)
                        FramesVoz = []
                        FramesSilencio = 0

                        rec.AcceptWaveform(AudioCompleto)
                        Texto = json.loads(rec.FinalResult()).get('text','').strip()

                        if not Texto:
                            print("[STT] Sin resultado")
                            if Estado == ESCUCHANDO:
                                Hablar("No entendí. Intenta de nuevo.")
                            continue

                        Tokens = set(Texto.lower().split())
                        print(f"\n[STT] '{Texto}'  estado={Estado}")

                        if Estado == ESCUCHANDO:
                            Pregunta += " " + Texto
                            Hablar(f"Entendí: {Pregunta.strip()}. ¿Es correcto?")
                            Estado = CONFIRMANDO

                        elif Estado == CONFIRMANDO:
                            if Tokens & SI_WORDS:
                                Final = Pregunta.strip()
                                Hablar("Procesando.")
                                EnviarAlCerebro(Final)
                                Estado   = PROCESANDO
                                Pregunta = ""
                            elif Tokens & NO_WORDS:
                                Pregunta = ""
                                Estado   = ESCUCHANDO
                                Hablar("De acuerdo. Repite tu pregunta.")
                            else:
                                Hablar("Di sí para enviar, o no para repetir.")

except KeyboardInterrupt:
    print("\n[SISTEMA] Oído apagado.")
except Exception as E:
    print(f"\n[ERROR]: {E}")
