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

# --- DETECCION AUTOMATICA DE CARD ---
def obtener_dispositivo_audio(nombre_card="ac101b"):
    try:
        resultado = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
        for linea in resultado.stdout.splitlines():
            match = re.search(r'card (\d+):.*?' + nombre_card, linea, re.IGNORECASE)
            if match:
                numero = match.group(1)
                print(f"[AUDIO] Card '{nombre_card}' detectada → plughw:{numero},0")
                return f"plughw:{numero},0"
    except Exception as e:
        print(f"[AUDIO] Error detectando card: {e}")
    print(f"[AUDIO] ADVERTENCIA: '{nombre_card}' no encontrada, usando plughw:1,0")
    return "plughw:1,0"

DISPOSITIVO_AUDIO = obtener_dispositivo_audio("ac101b")

# ─────────────────────────────────────────────
# CAPA DE AUDIO: dos modos, un solo worker
# ─────────────────────────────────────────────
# Cada item en la cola es una tupla: (texto, modo)
# modo = "robot"  → voz de búsqueda/sistema (pitch bajo + overdrive)
# modo = "normal" → voz de respuesta LLM (Piper limpio)
# ─────────────────────────────────────────────
_cola_audio = queue.Queue()
_worker_iniciado = False

def _piper_base(texto, env):
    """Lanza Piper y devuelve el Popen con stdout=PIPE."""
    return subprocess.Popen(
        [
            PIPER_EXE,
            "--model", VOZ_PATH,
            "--espeak_data", ESPEAK_DATA,
            "--length_scale", "1.9",
            "--sentence_silence", "0.3",
            "--output_raw"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env
    )

def _aplay(stdin_pipe):
    """Lanza aplay leyendo desde stdin_pipe."""
    return subprocess.Popen(
        ["aplay", "-D", DISPOSITIVO_AUDIO, "-r", "22050", "-f", "S16_LE", "-t", "raw"],
        stdin=stdin_pipe,
        stderr=subprocess.DEVNULL
    )

def _hablar_robot(texto, env):
    """Voz robótica: Piper → sox (pitch+overdrive+eco) → aplay."""
    try:
        piper = _piper_base(texto, env)

        sox = subprocess.Popen(
            [
                "sox",
                "-t", "raw", "-r", "22050", "-e", "signed", "-b", "16", "-c", "1", "-",
                "-t", "raw", "-r", "22050", "-e", "signed", "-b", "16", "-c", "1", "-",
                "pitch", "-500",          # más grave/metálico
                "echo", "0.7", "0.9", "30", "0.25",  # eco corto
                "overdrive", "15",        # distorsión metálica
                "rate", "22050"
            ],
            stdin=piper.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        aplay = _aplay(sox.stdout)

        piper.stdin.write(texto.encode("utf-8"))
        piper.stdin.close()
        piper.stdout.close()
        sox.stdout.close()

        piper.wait()
        sox.wait()
        aplay.wait()

    except FileNotFoundError:
        # sox no instalado → fallback normal
        _hablar_normal(texto, env)
    except Exception as e:
        print(f"[AUDIO-ROBOT] Error: {e}")

def _hablar_normal(texto, env):
    """Voz limpia para respuestas del LLM: Piper → aplay directo."""
    try:
        piper = _piper_base(texto, env)
        aplay = _aplay(piper.stdout)

        piper.stdin.write(texto.encode("utf-8"))
        piper.stdin.close()
        piper.stdout.close()

        piper.wait()
        aplay.wait()

    except Exception as e:
        print(f"[AUDIO-NORMAL] Error: {e}")

def _audio_worker():
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = PIPER_BIN_DIR

    while True:
        item = _cola_audio.get()
        if item is None:
            _cola_audio.task_done()
            break

        texto, modo = item
        texto_limpio = texto.replace('"', '').replace("'", '').replace('\n', ' ').strip()

        if texto_limpio:
            if modo == "robot":
                _hablar_robot(texto_limpio, env)
            else:
                _hablar_normal(texto_limpio, env)

        _cola_audio.task_done()

def iniciar_worker():
    global _worker_iniciado
    if not _worker_iniciado:
        t = threading.Thread(target=_audio_worker, daemon=True)
        t.start()
        _worker_iniciado = True

def hablar(texto, modo="normal"):
    """Encola un fragmento de texto con su modo de voz."""
    if texto.strip():
        _cola_audio.put((texto.strip(), modo))

# ─────────────────────────────────────────────
# REGEX ORACIONES COMPLETAS
# ─────────────────────────────────────────────
PATRON_ORACION = re.compile(r'([^.!?]*[.!?](?:\s|$))')

# ─────────────────────────────────────────────
# CONOCIMIENTO UACh
# ─────────────────────────────────────────────
class ManejadorConocimientoBmo:
    def __init__(self, RutaArchivo):
        self.BaseDatosRaw = []
        self.CargarDatos(RutaArchivo)

    def NormalizarTexto(self, Texto):
        Texto = re.sub(r'[¿?¡!,.]', '', Texto)
        return "".join(
            c for c in unicodedata.normalize('NFD', Texto)
            if unicodedata.category(c) != 'Mn'
        ).lower()

    def CargarDatos(self, RutaArchivo):
        try:
            with open(RutaArchivo, 'r', encoding='utf-8') as f:
                self.BaseDatosRaw = json.load(f)
            print("[SISTEMA] Base de datos UACh cargada.")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar JSON: {e}")

    def ObtenerContextoAvanzado(self, Consulta):
        ConsultaLimpia = self.NormalizarTexto(Consulta)
        StopWords = {'con','las','los','del','una','por','que','cual',
                     'como','para','esta','este','donde','hay'}
        Palabras = [p for p in ConsultaLimpia.split() if len(p) >= 3 and p not in StopWords]

        Contexto = ""
        Coincidencias = []

        # ── Verbosidad visual ──
        print(f"\n{'─'*50}")
        print(f"[BUSQUEDA] Tokens analizados: {Palabras}")

        # ── Voz robótica anuncia la búsqueda ──
        hablar(f"Analizando consulta. Tokens: {', '.join(Palabras)}.", modo="robot")

        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                Termino = self.NormalizarTexto(Concepto["termino"])
                Matches = [p for p in Palabras if p in Termino]
                if Matches:
                    Coincidencias.append(Concepto["termino"])
                    print(f"  ✔ MATCH → '{Concepto['termino']}' (tokens: {Matches})")
                    # Voz robótica anuncia cada match
                    hablar(f"Coincidencia detectada: {Concepto['termino']}.", modo="robot")
                    Contexto += (
                        f"CONCEPTO: {Concepto['termino']}\n"
                        f"DEFINICION: {Concepto['definicion_uach']}\n"
                        f"ECUACION/DATO: {Concepto.get('ecuacion','N/A')}\n"
                        f"APLICACION: {Concepto['aplicacion_practica']}\n"
                        f"-------------------\n"
                    )

        if not Coincidencias:
            print("  ✘ Sin coincidencias en base de conocimientos UACh.")
            hablar("Sin coincidencias en base de conocimientos. Dato no disponible.", modo="robot")
        else:
            print(f"  → Contexto construido: {len(Coincidencias)} concepto(s).")
            hablar(f"Contexto construido. {len(Coincidencias)} concepto encontrado. Procesando respuesta.", modo="robot")

        print(f"{'─'*50}")
        return Contexto

BuscadorUach = ManejadorConocimientoBmo('/home/radxa/Documents/BMO/base_conocimientos_uach.json')

# ─────────────────────────────────────────────
# CHAT PRINCIPAL
# ─────────────────────────────────────────────
def ChatInteractiva():
    iniciar_worker()
    print("\n" + "="*60)
    print("      BMO AGRO-IA v3.3 - DUAL VOICE MODE")
    print("      Hardware: Radxa Cubie A7A | Engine: Qwen2:0.5b")
    print("="*60)

    while True:
        try:
            Pregunta = input("\n[Brandon] >> ")
            if Pregunta.lower() in ['salir', 'exit']:
                _cola_audio.put(None)
                break

            # ── Búsqueda (voz robótica interna al método) ──
            Contexto = BuscadorUach.ObtenerContextoAvanzado(Pregunta)

            if not Contexto:
                continue  # el método ya encola el mensaje de fallo

            # ── LLM en hilo separado para no bloquear la cola de audio ──
            PromptFinal = (
                "ERES BMO, AGENTE DE IA ESPECIALIZADO EN INGENIERIA AGRONOMICA DE LA UACH.\n"
                "RESPONDE SOLO EN ESPAÑOL. USA EXCLUSIVAMENTE ESTE CONTEXTO:\n"
                f"{Contexto}\n\n"
                f"PREGUNTA: {Pregunta}\n\n"
                "INSTRUCCION: Respuesta técnica, directa y breve. "
                "Sin repetir la pregunta. Sin listas ni asteriscos. Solo texto continuo. "
                "Si la información no es suficiente di exactamente: "
                "'Dato no disponible en mi base de conocimientos UACh'."
            )

            print("[LLM] ► Generando respuesta...\n")
            Inicio = time.time()

            # Usamos stream con timeout por chunk para evitar cuelgues
            try:
                Stream = ollama.generate(
                    model='qwen2:0.5b',
                    prompt=PromptFinal,
                    options={
                        'temperature': 0.0,
                        'num_predict': 200,   # límite de tokens → evita loops infinitos
                        'stop': ['\n\n', '---']  # corta si el modelo empieza a alucinar
                    },
                    stream=True
                )
            except Exception as e:
                print(f"[ERROR LLM] No se pudo conectar con ollama: {e}")
                hablar("Error al conectar con el modelo de lenguaje.", modo="robot")
                continue

            buffer = ""
            print("[BMO] >> ", end="", flush=True)

            for Chunk in Stream:
                texto = Chunk.get('response', '')
                if not texto:
                    continue
                print(texto, end="", flush=True)
                buffer += texto

                # Extraer oraciones completas del buffer → voz normal
                coincidencias = PATRON_ORACION.findall(buffer)
                if coincidencias:
                    for oracion in coincidencias:
                        hablar(oracion, modo="normal")
                    ultimo = buffer.rfind(coincidencias[-1]) + len(coincidencias[-1])
                    buffer = buffer[ultimo:]

            # Resto sin punto final
            if buffer.strip():
                hablar(buffer, modo="normal")

            print(f"\n[TIEMPO] {time.time() - Inicio:.2f}s")

        except KeyboardInterrupt:
            print("\n[SISTEMA] Interrumpido por usuario.")
            _cola_audio.put(None)
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    ChatInteractiva()
