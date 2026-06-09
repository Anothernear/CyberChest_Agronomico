import json, ollama, time, unicodedata, re, os, socket
import requests
from config import OPENROUTER_API_KEY, OR_MODEL

SocketAudio = "/tmp/bmo_audio.sock"
SocketEar   = "/tmp/bmo_ear.sock"
SocketBrain = "/tmp/bmo_brain.sock"
PatronOracion = re.compile(r'([^.!?]*[.!?](?:\s|$))')
BmoBase = "/home/radxa/Documents/BMO"

def enviar_emocion(emocion):
    try:
        pipe_path = "/tmp/bmo_pipe"
        # Verificar que el pipe existe
        if not os.path.exists(pipe_path):
            print(f"Advertencia: Pipe {pipe_path} no existe")
            return
        
        # Abrir en modo no bloqueante con timeout
        with open(pipe_path, "w") as pipe:
            pipe.write(f"{emocion}\n")
            pipe.flush()  # Forzar escritura inmediata
    except Exception as e:
        print(f"Error al enviar emoción '{emocion}': {e}")

def ControlarOido(Estado):
    try:
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketEar)
        S.sendall(Estado.encode())
        S.close()
    except: pass

def EnviarAudio(Texto, Modo="normal"):
    if not Texto.strip(): return
    try:
        S = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        S.connect(SocketAudio)
        S.sendall(f"{Modo}|{Texto}".encode("utf-8"))
        S.close()
    except: pass

class ManejadorConocimientoBmo:
    def __init__(self, Ruta):
        self.Db = []
        try:
            with open(Ruta, 'r', encoding='utf-8') as F:
                self.Db = json.load(F)
        except: pass

    def Normalizar(self, Texto):
        Texto = re.sub(r'[¿?¡!,.]', '', Texto)
        return "".join(C for C in unicodedata.normalize('NFD', Texto) if unicodedata.category(C) != 'Mn').lower()

    def Buscar(self, Consulta):
        Limpia = self.Normalizar(Consulta)
        Stops = {'con','las','los','del','una','por','que','cual','como','para'}
        Palabras = [P for P in Limpia.split() if len(P) >= 3 and P not in Stops]
        Contexto = ""
        for Bloque in self.Db:
            for Concepto in Bloque.get("conceptos_clave", []):
                Termino = self.Normalizar(Concepto["termino"])
                if any(P in Termino for P in Palabras):
                    Contexto += f"CONCEPTO: {Concepto['termino']}\nDEFINICION: {Concepto['definicion_uach']}\nAPLICACION: {Concepto['aplicacion_practica']}\n---\n"
        return Contexto

DbUach = ManejadorConocimientoBmo(os.path.join(BmoBase, 'base_conocimientos_uach.json'))

def ProcesarPregunta(PreguntaFinal):
    enviar_emocion("pensar")
    
    # PRIMERO buscar en la base de datos
    Contexto = DbUach.Buscar(PreguntaFinal)
    
    # --- VERIFICAR MODO SELECCIONADO ---
    ModoBMO = "normal"
    try:
        with open("/tmp/bmo_mode", "r") as f:
            ModoBMO = f.read().strip()
    except: pass
    
    # Si es modo superior, usar Gemini vía OpenRouter
    if ModoBMO == "superior":
        enviar_emocion("pensar")
        EnviarAudio("Usando modo superior con Gemini.", Modo="robot")
        time.sleep(0.8)
        
        try:
            # Prompt con el contexto de la DB de la UACH
            PromptGemini = (
                "Eres BMO, agente de IA de Ingeniería Agronómica de la UACH. "
                "Responde SOLO en español. Usa exclusivamente este contexto:\n"
                f"{Contexto}\n\n"
                f"Pregunta: {PreguntaFinal}\n\n"
                "Instrucción: Respuesta técnica, directa y breve. "
                "Sin repetir la pregunta. Sin listas ni asteriscos. Texto continuo. "
                "Si no hay información suficiente di exactamente: "
                "'Dato no disponible en mi base de conocimientos UACh'."
            )
            
            # Configuración de OpenRouter
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            body = {
                "model": OR_MODEL,
                "messages": [
                    {"role": "system", "content": "Eres BMO, asistente experto en agronomía de la UACH."},
                    {"role": "user", "content": PromptGemini}
                ],
                "temperature": 0.0,
                "max_tokens": 250
            }
            
            # Llamada a la API
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                headers=headers, 
                json=body,
                timeout=15
            )
            data = response.json()
            RespuestaGemini = data["choices"][0]["message"]["content"]
            
            # Dividir en oraciones y enviar al audio
            OracionesGemini = PatronOracion.findall(RespuestaGemini)
            for O in OracionesGemini:
                if O.strip():
                    EnviarAudio(O, Modo="normal")
            
            # Señal de terminado
            with open("/tmp/brain_done", "a") as f: pass
            return  # Salimos de la función para no ejecutar Ollama
            
        except Exception as e:
            print(f"Error en OpenRouter: {e}")
            EnviarAudio("Error de conexión en modo superior. Usando cerebro local.", Modo="robot")
            time.sleep(1)
            # Si falla, continuamos con Ollama (no hacemos return)
    
    # --- MODO NORMAL O FALLBACK ---
    EnviarAudio("Procesando respuesta.", Modo="normal")
    time.sleep(0.5)

    # Si encontró algo, leer los conceptos recuperados de la DB
    if Contexto:
        Conceptos = re.findall(r'CONCEPTO:\s*(.*?)\n', Contexto)
        if Conceptos:
            Resumen = " y ".join(Conceptos[:2])
            EnviarAudio(f"Datos recuperados: {Resumen}.", Modo="normal")
            time.sleep(0.5)
    
    # Aviso de transición antes de llamar a Ollama
    EnviarAudio("Generando respuesta técnica.", Modo="robot")
    time.sleep(0.5)
    
    if not Contexto:
        enviar_emocion("triste")
        EnviarAudio("No tengo esa información en mi base UACh.", Modo="robot")
        enviar_emocion("llorar")
        enviar_emocion("muerto")
        with open("/tmp/brain_done", "a") as f: pass
        return

    Prompt = (
            "ERES BMO, AGENTE DE IA DE INGENIERIA AGRONOMICA DE LA UACH.\n"
            "RESPONDE SOLO EN ESPAÑOL. USA EXCLUSIVAMENTE ESTE CONTEXTO:\n"
            f"{Contexto}\n\n"
            f"PREGUNTA: {PreguntaFinal}\n\n"
            "INSTRUCCION: Respuesta técnica, directa y breve. "
            "Sin repetir la pregunta. Sin listas ni asteriscos. Texto continuo. "
            "Si no hay info suficiente di exactamente: "
            "'Dato no disponible en mi base de conocimientos UACh'."
        )
    try:
        enviar_emocion("pensar")
        Stream = ollama.generate(
                   model='qwen2:0.5b',
                   prompt=Prompt,
                   options={'temperature': 0.0, 'num_predict': 200,
                            'stop': ['\n\n', '---']},
                   stream=True
               )
        Buffer = ""
        for Chunk in Stream:
            Texto = Chunk.get('response', '')
            Buffer += Texto
            Oraciones = PatronOracion.findall(Buffer)
            if Oraciones:
                for O in Oraciones: EnviarAudio(O, Modo="normal")
                Buffer = Buffer[Buffer.rfind(Oraciones[-1]) + len(Oraciones[-1]):]
        if Buffer.strip(): EnviarAudio(Buffer, Modo="normal")
    except Exception as e:
        print(f"Error en Ollama: {e}")
        EnviarAudio("Error en el cerebro local.", Modo="robot")
    
    # SEÑAL DE TERMINADO
    with open("/tmp/brain_done", "a") as f: pass

def Chat():
    if os.path.exists(SocketBrain): os.remove(SocketBrain)
    Srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    Srv.bind(SocketBrain)
    Srv.listen(1)
    while True:
        try:
            Conn, _ = Srv.accept()
            Data = Conn.recv(4096).decode("utf-8").strip()
            Conn.close()
            if not Data: continue
            
            # --- INTERCEPTOR DE MODO INICIAL ---
            if not hasattr(Chat, "modo_definido"):
                Chat.modo_definido = os.path.exists("/tmp/bmo_mode")

            if not Chat.modo_definido:
                DataLower = Data.lower()
                if "superior" in DataLower:
                    with open("/tmp/bmo_mode", "w") as f: f.write("superior")
                    EnviarAudio("Modo superior activado. Gemini en línea.", Modo="robot")
                    Chat.modo_definido = True
                elif "normal" in DataLower:
                    with open("/tmp/bmo_mode", "w") as f: f.write("normal")
                    EnviarAudio("Modo normal activado. Cerebro local en línea.", Modo="normal")
                    Chat.modo_definido = True
                else:
                    EnviarAudio("No entendí. Por favor di normal o superior.", Modo="normal")
                
                # Señal de terminado para que el lanzador reinicie el oído
                with open("/tmp/brain_done", "a") as f: pass
                continue
            # --- INTERCEPTOR DE CAMBIO DE MODO ---
            DataLower = Data.lower()
            if "cambiar" in DataLower and "modo" in DataLower:
                if "superior" in DataLower:
                    with open("/tmp/bmo_mode", "w") as f: f.write("superior")
                    EnviarAudio("Cambiando a modo superior con Gemini.", Modo="robot")
                    enviar_emocion("feliz")
                elif "normal" in DataLower:
                    with open("/tmp/bmo_mode", "w") as f: f.write("normal")
                    EnviarAudio("Cambiando a modo normal local.", Modo="normal")
                    enviar_emocion("feliz")
                else:
                    EnviarAudio("¿Cambiar a qué modo? Di: cambiar a modo normal o superior.", Modo="normal")
                
                time.sleep(1)
                with open("/tmp/brain_done", "a") as f: pass
                continue
            # -------------------------------------
            # -------------------------------------
            
            ControlarOido("PAUSA")
            ProcesarPregunta(Data)
        except Exception as e:
            print(f"Error en Chat: {e}")


def LimpiarModo():
    """Limpia el archivo de modo al cerrar"""
    try:
        if os.path.exists("/tmp/bmo_mode"):
            os.remove("/tmp/bmo_mode")
    except: pass

if __name__ == "__main__":
    Chat()
