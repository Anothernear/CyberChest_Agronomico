import json, ollama, time, unicodedata, re, os, socket

SocketAudio = "/tmp/bmo_audio.sock"
SocketEar   = "/tmp/bmo_ear.sock"
SocketBrain = "/tmp/bmo_brain.sock"
PatronOracion = re.compile(r'([^.!?]*[.!?](?:\s|$))')
BmoBase = "/home/radxa/Documents/BMO"


def enviar_emocion(emocion):
    try:
        # Abrimos el pipe en modo escritura
        with open("/tmp/bmo_pipe", "w") as pipe:
            pipe.write(f"{emocion}\n")
    except Exception as e:
        print(f"Error al enviar emoción: {e}")

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
    Contexto = DbUach.Buscar(PreguntaFinal)
    if not Contexto:
        enviar_emocion("triste")
        EnviarAudio("No tengo esa información en mi base UACh.", Modo="robot")
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
    except: pass
    
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
            ControlarOido("PAUSA")
            ProcesarPregunta(Data)
        except: pass

if __name__ == "__main__":
    Chat()
