import json
import ollama
import time
import unicodedata
import re
import os
import subprocess
import threading
import queue

# --- CONFIGURACION DE RUTAS ---
BMO_BASE = "/home/radxa/Documents/BMO"
PIPER_BIN_DIR = os.path.join(BMO_BASE, "piper")
PIPER_EXE = os.path.join(PIPER_BIN_DIR, "piper")
VOZ_PATH = os.path.join(BMO_BASE, "bmo_voice/es_ES-carlfm-x_low.onnx")
ESPEAK_DATA = os.path.join(PIPER_BIN_DIR, "espeak-ng-data")
def obtener_dispositivo_audio(nombre_card="ac101b"):
    """Busca la card por nombre en aplay -l y devuelve plughw:N,0"""
    try:
        resultado = subprocess.run(
            ["aplay", "-l"], capture_output=True, text=True
        )
        for linea in resultado.stdout.splitlines():
            match = re.search(r'card (\d+):.*?' + nombre_card, linea, re.IGNORECASE)
            if match:
                numero = match.group(1)
                print(f"[AUDIO] Card '{nombre_card}' detectada → plughw:{numero},0")
                return f"plughw:{numero},0"
    except Exception as e:
        print(f"[AUDIO] Error detectando card: {e}")
    
    print(f"[AUDIO] ADVERTENCIA: '{nombre_card}' no encontrada, usando plughw:1,0 por defecto")
    return "plughw:1,0"

# Reemplaza la línea fija por esto:
DISPOSITIVO_AUDIO = obtener_dispositivo_audio("ac101b")
# --- COLA Y WORKER DE AUDIO ---
_cola_audio = queue.Queue()
_worker_iniciado = False

def _audio_worker():
    """Hilo dedicado: consume oraciones completas de la cola y las habla una por una."""
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = PIPER_BIN_DIR
    while True:
        texto = _cola_audio.get()
        if texto is None:  # señal de cierre
            break
        texto_limpio = texto.replace('"', '').replace('\n', ' ').strip()
        if not texto_limpio:
            _cola_audio.task_done()
            continue
        try:
            comando = (
                f'echo "{texto_limpio}" | {PIPER_EXE} '
                f'--model {VOZ_PATH} '
                f'--espeak_data {ESPEAK_DATA} '
                f'--length_scale 1.7 '
                f'--sentence_silence 0.5 '
                f'--output_raw | aplay -D {DISPOSITIVO_AUDIO} -r 22050 -f S16_LE -t raw'
            )
            subprocess.run(comando, shell=True, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        _cola_audio.task_done()

def iniciar_worker():
    global _worker_iniciado
    if not _worker_iniciado:
        t = threading.Thread(target=_audio_worker, daemon=True)
        t.start()
        _worker_iniciado = True

# Regex: corta solo cuando hay punto/signo al FINAL de una palabra
PATRON_ORACION = re.compile(r'([^.!?]*[.!?](?:\s|$))')

def encolar_oraciones(texto):
    """Extrae oraciones completas del texto y las manda a la cola."""
    for oracion in PATRON_ORACION.findall(texto):
        if oracion.strip():
            _cola_audio.put(oracion.strip())

# --- CONOCIMIENTO UACh (sin cambios) ---
class ManejadorConocimientoBmo:
    def __init__(self, RutaArchivo):
        self.BaseDatosRaw = []
        self.CargarDatos(RutaArchivo)

    def NormalizarTexto(self, Texto):
        Texto = re.sub(r'[¿?¡!,.]', '', Texto)
        TextoNormalizado = "".join(
            c for c in unicodedata.normalize('NFD', Texto)
            if unicodedata.category(c) != 'Mn'
        )
        return TextoNormalizado.lower()

    def CargarDatos(self, RutaArchivo):
        try:
            with open(RutaArchivo, 'r', encoding='utf-8') as f:
                self.BaseDatosRaw = json.load(f)
            print("[SISTEMA] Base de datos UACh cargada con éxito.")
        except Exception as e:
            print(f"[ERROR] No se pudo acceder al JSON: {e}")

    def ObtenerContextoAvanzado(self, Consulta):
        ConsultaLimpia = self.NormalizarTexto(Consulta)
        StopWords = ['con','las','los','del','una','por','que','cual',
                     'como','para','esta','este','donde']
        Palabras = [p for p in ConsultaLimpia.split() if len(p) >= 3 and p not in StopWords]
        Contexto = ""
        Coincidencias = []
        print(f"\n[BUSQUEDA] Analizando términos: {Palabras}")
        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                Termino = self.NormalizarTexto(Concepto["termino"])
                Matches = [p for p in Palabras if p in Termino]
                if Matches:
                    Coincidencias.append(Concepto["termino"])
                    print(f"  [!] MATCH: '{Concepto['termino']}' vía {Matches}")
                    Contexto += (
                        f"CONCEPTO: {Concepto['termino']}\n"
                        f"DEFINICION: {Concepto['definicion_uach']}\n"
                        f"ECUACION/DATO: {Concepto.get('ecuacion','N/A')}\n"
                        f"APLICACION: {Concepto['aplicacion_practica']}\n"
                        f"-------------------\n"
                    )
        if not Coincidencias:
            print("  [?] Sin coincidencias en DB.")
        else:
            print(f"  [OK] {len(Coincidencias)} conceptos encontrados.")
        return Contexto

BuscadorUach = ManejadorConocimientoBmo('/home/radxa/Documents/BMO/base_conocimientos_uach.json')

# --- CHAT PRINCIPAL ---
def ChatInteractiva():
    iniciar_worker()  # arranca el hilo de audio al inicio
    print("\n" + "="*60)
    print("      BMO AGRO-IA v3.1 - AUDIO FLUIDO")
    print("      Hardware: Radxa Cubie A7A | Engine: Qwen2:0.5b")
    print("="*60)

    while True:
        try:
            Pregunta = input("\n[Brandon] >> ")
            if Pregunta.lower() in ['salir', 'exit']:
                _cola_audio.put(None)  # cierra el worker limpiamente
                break

            Contexto = BuscadorUach.ObtenerContextoAvanzado(Pregunta)

            if not Contexto:
                msg = "Dato no disponible en mi base de conocimientos UACh."
                print(f"[BMO] >> {msg}")
                _cola_audio.put(msg)
                continue

            PromptFinal = (
                "ERES UN ASISTENTE DE INGENIERIA AGRONOMICA DE LA UACH.\n"
                "USA EXCLUSIVAMENTE ESTE CONTEXTO PARA RESPONDER:\n"
                f"{Contexto}\n\n"
                f"PREGUNTA: {Pregunta}\n\n"
                "INSTRUCCION: Da una respuesta técnica y breve. No repitas la pregunta. "
                "Si la información no es suficiente, di: "
                "'Dato no disponible en mi base de conocimientos UACh'."
            )

            print("[LLM] Procesando respuesta...")
            Inicio = time.time()

            Stream = ollama.generate(
                model='qwen2:0.5b',
                prompt=PromptFinal,
                options={'temperature': 0.0},
                stream=True
            )

            buffer = ""
            print("[BMO] >> ", end="", flush=True)

            for Chunk in Stream:
                texto = Chunk['response']
                print(texto, end="", flush=True)
                buffer += texto

                # Busca oraciones completas en el buffer acumulado
                coincidencias = PATRON_ORACION.findall(buffer)
                if coincidencias:
                    for oracion in coincidencias:
                        if oracion.strip():
                            _cola_audio.put(oracion.strip())
                    # Conserva solo el sobrante (sin oración completa aún)
                    ultimo = buffer.rfind(coincidencias[-1]) + len(coincidencias[-1])
                    buffer = buffer[ultimo:]

            # Resto del buffer al terminar el stream (sin punto final)
            if buffer.strip():
                _cola_audio.put(buffer.strip())

            print(f"\n[TIEMPO] {time.time() - Inicio:.2f}s")

        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    ChatInteractiva()
