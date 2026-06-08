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
        Texto = re.sub(r'[¿?¡!,.]', '', Texto)
        TextoNormalizado = "".join(
            c for c in unicodedata.normalize('NFD', Texto)
            if unicodedata.category(c) != 'Mn'
        )
        return TextoNormalizado.lower()

    def CargarDatos(self, RutaArchivo):
        print(f"[INFO] Cargando BaseDeDatos: {RutaArchivo}...")
        try:
            with open(RutaArchivo, 'r', encoding='utf-8') as ArchivoJson:
                self.BaseDatosRaw = json.load(ArchivoJson)
            print(f"[EXITO] BaseDeDatos lista. Dominios: {len(self.BaseDatosRaw)}")
        except Exception as Error:
            print(f"[ERROR] {Error}")

    def ObtenerContextoAvanzado(self, Consulta):
        ConsultaLimpia = self.NormalizarTexto(Consulta)
        # Reducimos a 3 letras para captar GDD, DPV, etc. 
        # Excluimos articulos comunes manualmente.
        StopWords = ['con', 'las', 'los', 'del', 'una', 'por', 'que', 'cual']
        PalabrasConsulta = [P for P in ConsultaLimpia.split() if len(P) >= 3 and P not in StopWords]
        
        ContextoEncontrado = ""
        print(f"[BUSQUEDA] Query: '{ConsultaLimpia}' | Filtro: {PalabrasConsulta}")
        
        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                TerminoLimpio = self.NormalizarTexto(Concepto["termino"])
                # Match si la palabra clave esta contenida en el termino del JSON
                if any(P in TerminoLimpio for P in PalabrasConsulta):
                    print(f"  [MATCH] Concepto detectado: '{Concepto['termino']}'")
                    ContextoEncontrado += f"Dato: {Concepto['termino']}. Def: {Concepto['definicion_uach']}. Ec: {Concepto['ecuacion']}.\n"
        
        return ContextoEncontrado

BuscadorUach = ManejadorConocimientoBmo('/home/radxa/Documents/BMO/base_conocimientos_uach.json')

def EjecutarInferenciaBmo(Pregunta):
    print("\n" + "="*60)
    Contexto = BuscadorUach.ObtenerContextoAvanzado(Pregunta)
    
    if not Contexto:
        print("[SISTEMA] Sin contexto relevante. Forzando respuesta de seguridad.")
        PromptFinal = f"Pregunta: {Pregunta}\nRespuesta: Lo siento Brandon, no tengo datos sobre eso en la base de la UACh."
    else:
        # Prompt Estricto: El contexto va arriba y la orden de usarlo es directa
        PromptFinal = (
            f"CONTEXTO TECNICO agronomico UACh:\n{Contexto}\n\n"
            f"INSTRUCCION: Usa el CONTEXTO anterior para responder la pregunta argonomica: {Pregunta}. "
            "Se breve y exacto con las ecuaciones."
        )

    print(f"[LLM] Generando respuesta en Radxa...")
    print("-" * 30)
    
    Stream = ollama.generate(
        model='qwen2:0.5b',
        prompt=PromptFinal,
        stream=True
    )

    for Chunk in Stream:
        print(Chunk['response'], end="", flush=True)
    print("\n" + "="*60)

if __name__ == "__main__":
    # Prueba enfocada en GDD
    EjecutarInferenciaBmo("¿Cual es la aplicacion de la Radiacion Neta y los GDD?")
    #¿Cual es la ecuacion de los GDD?")
