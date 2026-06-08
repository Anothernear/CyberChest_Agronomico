import os
import subprocess

# --- RUTAS DEFINITIVAS ---
BMO_BASE = "/home/radxa/Documents/BMO"
PIPER_BIN_DIR = os.path.join(BMO_BASE, "piper")
PIPER_EXE = os.path.join(PIPER_BIN_DIR, "piper")
# Ruta al nuevo modelo x_low
VOZ_PATH = os.path.join(BMO_BASE, "bmo_voice/es_ES-carlfm-x_low.onnx")
ESPEAK_DATA = os.path.join(PIPER_BIN_DIR, "espeak-ng-data")

def Hablar(texto):
    if not texto: return
    
    # Limpieza de texto para el TTS
    texto_limpio = texto.replace('*', '').replace('$', '').replace('\n', ' ')
    
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = PIPER_BIN_DIR
    
    # Especificamos la Card 0, Device 0 (ac101b)
    DISPOSITIVO_AUDIO = "plughw:0,0" 
    
    try:
        # Comando optimizado para el Jack de 3.5mm
        comando = (
            f'echo "{texto_limpio}" | {PIPER_EXE} '
            f'--model {VOZ_PATH} '
            f'--espeak_data {ESPEAK_DATA} '
            f'--output_raw | aplay -D {DISPOSITIVO_AUDIO} -r 22050 -f S16_LE -t raw'
        )
        # Ejecución asíncrona (Popen) para que el robot siga operando mientras habla
        subprocess.Popen(comando, shell=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[ERROR VOZ] Error al enviar audio al jack: {e}")
