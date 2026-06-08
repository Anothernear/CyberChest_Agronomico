import json
import ollama
import time
import unicodedata
import re
import os
import subprocess

# --- CONFIGURACION DE RUTAS DEFINITIVAS (PIPER & AUDIO) ---
BMO_BASE = "/home/radxa/Documents/BMO"
PIPER_BIN_DIR = os.path.join(BMO_BASE, "piper")
PIPER_EXE = os.path.join(PIPER_BIN_DIR, "piper")
VOZ_PATH = os.path.join(BMO_BASE, "bmo_voice/es_ES-carlfm-x_low.onnx")
ESPEAK_DATA = os.path.join(PIPER_BIN_DIR, "espeak-ng-data")
DISPOSITIVO_AUDIO = "plughw:0,0" # Salida Jack 3.5mm (ac101b)

def HablarStream(texto_chunk):
    """Envia fragmentos de texto a Piper esperando a que termine cada uno para no chocar procesos."""
    if not texto_chunk.strip(): return
    
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = PIPER_BIN_DIR
    
    # Limpieza rápida para evitar errores en la shell
    texto_limpio = texto_chunk.replace('"', '').replace('\n', ' ')
    
    try:
        # CAMBIO: subprocess.run asegura que el audio termine antes de lanzar el siguiente
        comando = (
            f'echo "{texto_limpio}" | {PIPER_EXE} '
            f'--model {VOZ_PATH} '
            f'--espeak_data {ESPEAK_DATA} '
            f'--length_scale 1.7 '
            f'--sentence_silence 0.5 '
            f'--output_raw | aplay -D {DISPOSITIVO_AUDIO} -r 22050 -f S16_LE -t raw'
        )
        subprocess.run(comando, shell=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass 

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
            with open(RutaArchivo, 'r', encoding='utf-8') as ArchivoJson:
                self.BaseDatosRaw = json.load(ArchivoJson)
            print(f"[SISTEMA] Base de datos UACh cargada con éxito.")
        except Exception as Error:
            print(f"[ERROR] No se pudo acceder al JSON: {Error}")

    def ObtenerContextoAvanzado(self, Consulta):
        ConsultaLimpia = self.NormalizarTexto(Consulta)
        StopWords = ['con', 'las', 'los', 'del', 'una', 'por', 'que', 'cual', 'como', 'para', 'esta', 'este', 'donde']
        PalabrasConsulta = [P for P in ConsultaLimpia.split() if len(P) >= 3 and P not in StopWords]
        
        ContextoEncontrado = ""
        Coincidencias = []
        
        print(f"\n[BUSQUEDA] Analizando términos: {PalabrasConsulta}")
        
        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                TerminoLimpio = self.NormalizarTexto(Concepto["termino"])
                MatchesPalabras = [P for P in PalabrasConsulta if P in TerminoLimpio]
                
                if MatchesPalabras:
                    Coincidencias.append(Concepto["termino"])
                    print(f"  [!] MATCH DETECTADO: '{Concepto['termino']}' vía tokens {MatchesPalabras}")
                    ContextoEncontrado += (
                        f"CONCEPTO: {Concepto['termino']}\n"
                        f"DEFINICION: {Concepto['definicion_uach']}\n"
                        f"ECUACION/DATO: {Concepto.get('ecuacion', 'N/A')}\n"
                        f"APLICACION: {Concepto['aplicacion_practica']}\n"
                        f"-------------------\n"
                    )
        
        if not Coincidencias:
            print("  [?] RESULTADO: No se encontraron coincidencias técnicas en la DB.")
        else:
            print(f"  [OK] Contexto construido con {len(Coincidencias)} conceptos.")
            
        return ContextoEncontrado

BuscadorUach = ManejadorConocimientoBmo('/home/radxa/Documents/BMO/base_conocimientos_uach.json')

def ChatInteractiva():
    print("\n" + "="*60)
    print("      BMO AGRO-IA v3.0 - MODO RIGOR TECNICO")
    print("      Hardware: Radxa Cubie A7A | Engine: Qwen2:0.5b")
    print("="*60)

    while True:
        try:
            Pregunta = input("\n[Brandon] >> ")
            if Pregunta.lower() in ['salir', 'exit']: break

            Contexto = BuscadorUach.ObtenerContextoAvanzado(Pregunta)

            if not Contexto:
                respuesta_fail = "Dato no disponible en mi base de conocimientos UACh."
                print(f"[BMO] >> {respuesta_fail}")
                HablarStream(respuesta_fail)
                continue 
            
            # PROMPT: Ajustado para que sea directo y NO repita la pregunta del usuario
            PromptFinal = (
                "ERES UN ASISTENTE DE INGENIERIA AGRONOMICA DE LA UACH.\n"
                "USA EXCLUSIVAMENTE ESTE CONTEXTO PARA RESPONDER:\n"
                f"{Contexto}\n\n"
                f"PREGUNTA: {Pregunta}\n\n"
                "INSTRUCCION: Da una respuesta técnica y breve. No repitas la pregunta. "
                "Si la información no es suficiente, di: 'Dato no disponible en mi base de conocimientos UACh'."
            )

            print("[LLM] Procesando respuesta...")
            Inicio = time.time()
            
            Stream = ollama.generate(
                model='qwen2:0.5b',
                prompt=PromptFinal,
                options={'temperature': 0.0},
                stream=True
            )

            RespuestaAcumulada = ""
            ContadorPalabras = 0
            print("[BMO] >> ", end="", flush=True)
            for Chunk in Stream:
                textoChunk = Chunk['response']
                print(textoChunk, end="", flush=True)
                RespuestaAcumulada += textoChunk

                if " " in textoChunk:
                    ContadorPalabras += 1

                # Disparo de audio por puntuación o cada 7 palabras para fluidez
                if any(p in textoChunk for p in ['.', ',', '\n', ':', ';']) or ContadorPalabras >= 7:
                    if RespuestaAcumulada.strip():
                        HablarStream(RespuestaAcumulada)
                        RespuestaAcumulada = "" 
                        ContadorPalabras = 0

            if RespuestaAcumulada.strip():
                HablarStream(RespuestaAcumulada)
            print(f"\n[TIEMPO] {time.time() - Inicio:.2f}s")

        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    ChatInteractiva()
