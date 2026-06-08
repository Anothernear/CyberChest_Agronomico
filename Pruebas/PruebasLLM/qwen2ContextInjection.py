import json
import ollama
import time
import unicodedata

class ManejadorConocimientoBmo:
    def __init__(self, RutaArchivo):
        self.BaseDatosRaw = []
        self.CargarDatos(RutaArchivo)

    def NormalizarTexto(self, Texto):
        # Remueve acentos y convierte a minusculas para comparacion robusta
        TextoNormalizado = "".join(
            c for c in unicodedata.normalize('NFD', Texto)
            if unicodedata.category(c) != 'Mn'
        )
        return TextoNormalizado.lower()

    def CargarDatos(self, RutaArchivo):
        print(f"[INFO] Cargando BaseDeDatos desde: {RutaArchivo}...")
        try:
            with open(RutaArchivo, 'r', encoding='utf-8') as ArchivoJson:
                self.BaseDatosRaw = json.load(ArchivoJson)
            print(f"[EXITO] BaseDeDatos cargada. Dominios UACh detectados: {len(self.BaseDatosRaw)}")
        except Exception as Error:
            print(f"[ERROR] No se pudo leer el archivo JSON: {Error}")

    def ObtenerContextoAvanzado(self, Consulta):
        ConsultaLimpia = self.NormalizarTexto(Consulta)
        PalabrasConsulta = [P for P in ConsultaLimpia.split() if len(P) > 3]
        ContextoEncontrado = ""
        Coincidencias = []

        print(f"[BUSQUEDA] Analizando consulta: '{Consulta}'")
        print(f"[BUSQUEDA] Palabras clave identificadas: {PalabrasConsulta}")
        
        for Bloque in self.BaseDatosRaw:
            for Concepto in Bloque.get("conceptos_clave", []):
                TerminoOriginal = Concepto["termino"]
                TerminoLimpio = self.NormalizarTexto(TerminoOriginal)
                
                # Verificamos si el termino completo esta en la consulta o si hay palabras clave
                if TerminoLimpio in ConsultaLimpia or any(P in TerminoLimpio for P in PalabrasConsulta):
                    print(f"  [MATCH] Concepto detectado: '{TerminoOriginal}'")
                    Coincidencias.append(TerminoOriginal)
                    ContextoEncontrado += (
                        f"\n- Termino: {TerminoOriginal}\n"
                        f"- Definicion UACh: {Concepto['definicion_uach']}\n"
                        f"- Ecuacion: {Concepto.get('ecuacion','N/A')}\n"
                        f"- Aplicacion: {Concepto['aplicacion_practica']}\n"
                    )
        
        if Coincidencias:
            print(f"[RESUMEN] Total de coincidencias encontradas: {len(Coincidencias)} ({', '.join(Coincidencias)})")
        else:
            print("[ADVERTENCIA] No se encontraron coincidencias exactas en la BaseDeDatos.")
            
        return ContextoEncontrado

# Instancia Global
BuscadorUach = ManejadorConocimientoBmo('/home/radxa/Documents/BMO/base_conocimientos_uach.json')

def EjecutarInferenciaBmo(Pregunta):
    print("\n" + "="*60)
    print(f"[SISTEMA BMO] Iniciando procesamiento de Fase 1...")
    
    # 1. Obtencion de Contexto con Verbosidad
    InicioBusqueda = time.time()
    Contexto = BuscadorUach.ObtenerContextoAvanzado(Pregunta)
    FinBusqueda = time.time() - InicioBusqueda
    
    # 2. Preparacion del Prompt
    if not Contexto:
        Contexto = "No hay informacion especifica en los manuales de la UACh."

    PromptSistema = (
        "Eres BMO, un sistema experto en Horticultura Protegida de la UACh. "
        "Tu mision es responder dudas tecnicas de agricultores usando los datos proporcionados.\n"
        f"### CONTEXTO TECNICO DE LA UACH ###\n{Contexto}\n"
        "REGLA: Se breve, tecnico y no menciones temas de medicina o salud humana."
    )

    # 3. Inferencia
    print(f"[LLM] Llamando a Qwen2:0.5b (Ollama) | Tiempo Busqueda: {FinBusqueda:.4f}s")
    print("-" * 30)
    
    InicioInferencia = time.time()
    try:
        Stream = ollama.chat(
            model='qwen2:0.5b',
            messages=[
                {'role': 'system', 'content': PromptSistema},
                {'role': 'user', 'content': f"Basado en los datos de la UACh: {Pregunta}"}
            ],
            stream=True
        )

        for Chunk in Stream:
            print(Chunk['message']['content'], end="", flush=True)
            
    except Exception as Error:
        print(f"\n[ERROR LLM] Ocurrio un problema con Ollama: {Error}")

    FinInferencia = time.time() - InicioInferencia
    print(f"\n" + "-" * 30)
    print(f"[SISTEMA BMO] Ciclo completado. Tiempo Inferencia: {FinInferencia:.2f}s")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Prueba de estres con terminos del JSON
    EjecutarInferenciaBmo("¿Cual es la ecuacion de los GDD?")
    #"¿Cual es la aplicacion de la Radiacion Neta y los GDD?")
