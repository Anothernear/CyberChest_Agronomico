import json
import ollama
import time
import unicodedata
import re

class ManejadorConocimientoBmo:
    def __init__(self, RutaArchivo):
        self.BaseDatosRaw = []
        self.CargarDatos(RutaArchivo)

    def NormalizarTexto(self, Texto):
        # Limpieza profunda de caracteres que ensucian el match
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
        # Stopwords extendidas para evitar ruidos como "como", "esta", "que"
        StopWords = ['con', 'las', 'los', 'del', 'una', 'por', 'que', 'cual', 'como', 'para', 'esta', 'este', 'donde']
        PalabrasConsulta = [P for P in ConsultaLimpia.split() if len(P) >= 3 and P not in StopWords]
        
        ContextoEncontrado = ""
        Coincidencias = []
        
        print(f"\n[BUSQUEDA] Analizando términos: {PalabrasConsulta}")
        
        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                TerminoLimpio = self.NormalizarTexto(Concepto["termino"])
                # Buscamos si alguna palabra clave importante está en el término del JSON
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
                print("[BMO] >> Dato no disponible en mi base de conocimientos UACh.")
                print("[INFO] Se bloqueo el acceso al LLM para evitar alucinaciones técnicas.")
                continue # <--- AQUÍ DETENEMOS TODO SI NO HAY MATCH REAL
            
            # PROMPT DE SEGURIDAD EXTREMA
            PromptFinal = (
                "ERES UN ASISTENTE DE INGENIERIA AGRONOMICA DE LA UACH.\n"
                "TU UNICA FUENTE DE VERDAD ES EL SIGUIENTE CONTEXTO:\n"
                f"{Contexto if Contexto else 'NO HAY DATOS DISPONIBLES.'}\n\n"
                f"PREGUNTA DEL USUARIO: {Pregunta}\n\n"
                "REGLAS DE RESPUESTA:\n"
                "1. Si el contexto tiene la respuesta, sé breve y usa las ecuaciones dadas.\n"
                "2. SI LA RESPUESTA NO ESTA EN EL CONTEXTO, di exactamente: 'Dato no disponible en mi base de conocimientos UACh'.\n"
                "3. PROHIBIDO INVENTAR nombres de químicos, enfermedades o leyes físicas.\n"
                "4. No hables de medicina humana ni energía mística."
            )

            print("[LLM] Procesando respuesta...")
            Inicio = time.time()
            
            # Bajamos la temperatura a 0.0 para eliminar la "creatividad"
            Stream = ollama.generate(
                model='qwen2:0.5b',
                prompt=PromptFinal,
                options={'temperature': 0.0},
                stream=True
            )

            print("[BMO] >> ", end="", flush=True)
            for Chunk in Stream:
                print(Chunk['response'], end="", flush=True)
            
            print(f"\n[TIEMPO] {time.time() - Inicio:.2f}s")

        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    ChatInteractiva()
