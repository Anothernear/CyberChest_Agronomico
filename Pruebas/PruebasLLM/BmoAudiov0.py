import socket, os, subprocess, re

BmoBase = "/home/radxa/Documents/BMO"
PiperBinDir = os.path.join(BmoBase, "piper")
PiperExe = os.path.join(PiperBinDir, "piper")
VozPath = os.path.join(BmoBase, "bmo_voice/es_ES-carlfm-x_low.onnx")
EspeakData = os.path.join(PiperBinDir, "espeak-ng-data")
SocketPath = "/tmp/bmo_audio.sock"

def ObtenerDispositivo():
    try:
        R = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
        for Linea in R.stdout.splitlines():
            M = re.search(r'card (\d+):.*?ac101b', Linea, re.IGNORECASE)
            if M:
                return f"plughw:{M.group(1)},0"
    except: pass
    return "plughw:1,0"

DispositivoAudio = ObtenerDispositivo()
print(f"[AUDIO] Dispositivo configurado: {DispositivoAudio}")

def Hablar(Texto, Modo):
    Env = os.environ.copy()
    Env["LD_LIBRARY_PATH"] = PiperBinDir
    Texto = Texto.replace('"','').replace("'",'').replace('\n',' ').strip()
    if not Texto: return

    PiperProceso = subprocess.Popen(
        [PiperExe, "--model", VozPath, "--espeak_data", EspeakData,
         "--length_scale", "1.9", "--sentence_silence", "0.3", "--output_raw"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, env=Env
    )

    if Modo == "robot":
        try:
            SoxProceso = subprocess.Popen(
                ["sox", "-t","raw","-r","22050","-e","signed","-b","16","-c","1","-",
                       "-t","raw","-r","22050","-e","signed","-b","16","-c","1","-",
                 "pitch","-500", "echo","0.7","0.9","30","0.25", "overdrive","15","rate","22050"],
                stdin=PiperProceso.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            AplayProceso = subprocess.Popen(
                ["aplay","-D",DispositivoAudio,"-r","22050","-f","S16_LE","-t","raw"],
                stdin=SoxProceso.stdout, stderr=subprocess.DEVNULL
            )
            PiperProceso.stdin.write(Texto.encode())
            PiperProceso.stdin.close()
            PiperProceso.stdout.close()
            SoxProceso.stdout.close()
            PiperProceso.wait()
            SoxProceso.wait()
            AplayProceso.wait()
            return
        except FileNotFoundError:
            print("[AUDIO] SoX no encontrado, usando modo normal.")

    AplayNormal = subprocess.Popen(
        ["aplay","-D",DispositivoAudio,"-r","22050","-f","S16_LE","-t","raw"],
        stdin=PiperProceso.stdout, stderr=subprocess.DEVNULL
    )
    PiperProceso.stdin.write(Texto.encode())
    PiperProceso.stdin.close()
    PiperProceso.stdout.close()
    PiperProceso.wait()
    AplayNormal.wait()

if __name__ == "__main__":
    if os.path.exists(SocketPath):
        os.remove(SocketPath)

    ServidorSocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ServidorSocket.bind(SocketPath)
    ServidorSocket.listen(1)
    print("[AUDIO] Servidor listo. Esperando datos del Cerebro...")

    while True:
        Conexion, _ = ServidorSocket.accept()
        DataAcumulada = b""
        while True:
            Fragmento = Conexion.recv(4096)
            if not Fragmento: break
            DataAcumulada += Fragmento
        Conexion.close()
        
        if not DataAcumulada: continue
        
        MensajeDecodificado = DataAcumulada.decode("utf-8", errors="replace")
        ModoVoz, _, TextoFinal = MensajeDecodificado.partition("|")
        Hablar(TextoFinal, ModoVoz.strip())
