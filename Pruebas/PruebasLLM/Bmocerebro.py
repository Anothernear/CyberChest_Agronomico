import json, ollama, time, unicodedata, re, os, socket

SocketAudio = "/tmp/bmo_audio.sock"
SocketEar   = "/tmp/bmo_ear.sock"
SocketBrain = "/tmp/bmo_brain.sock"
PatronOracion = re.compile(r'([^.!?]*[.!?](?:\s|$))')
BmoBase = "/home/radxa/Documents/BMO"

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
    except Exception as E:
        print(f"[BRAIN] Error audio: {E}")

class ManejadorConocimientoBmo:
    def __init__(self, Ruta):
        self.Db = []
        try:
            with open(Ruta, 'r', encoding='utf-8') as F:
                self.Db = json.load(F)
            print("[SISTEMA] Base de datos UACh cargada.")
        except Exception as E:
            print(f"[ERROR] {E}")

    def Normalizar(self, Texto):
        Texto = re.sub(r'[¿?¡!,.]', '', Texto)
        return "".join(
            C for C in unicodedata.normalize('NFD', Texto)
            if unicodedata.category(C) != 'Mn'
        ).lower()

    def Buscar(self, Consulta):
        Limpia = self.Normalizar(Consulta)
        Stops = {'con','las','los','del','una','por','que','cual',
                 'como','para','esta','este','donde','hay'}
        Palabras = [P for P in Limpia.split() if len(P) >= 3 and P not in Stops]

        Contexto = ""
        Matches = []

        print(f"\n{'─'*50}")
        print(f"[BUSQUEDA] Tokens: {Palabras}")

        for Bloque in self.Db:
            for Concepto in Bloque.get("conceptos_clave", []):
                Termino = self.Normalizar(Concepto["termino"])
                Found = [P for P in Palabras if P in Termino]
                if Found:
                    Matches.append(Concepto["termino"])
                    print(f"  ✔ MATCH → '{Concepto['termino']}' (tokens: {Found})")
                    Contexto += (
                        f"CONCEPTO: {Concepto['termino']}\n"
                        f"DEFINICION: {Concepto['definicion_uach']}\n"
                        f"ECUACION/DATO: {Concepto.get('ecuacion','N/A')}\n"
                        f"APLICACION: {Concepto['aplicacion_practica']}\n---\n"
                    )

        if not Matches:
            print("  ✘ Sin coincidencias.")
            EnviarAudio("No encontré información sobre ese tema.", Modo="robot")
        else:
            print(f"  → {len(Matches)} concepto(s) encontrado(s).")

        print(f"{'─'*50}")
        return Contexto

DbUach = ManejadorConocimientoBmo(os.path.join(BmoBase, 'base_conocimientos_uach.json'))

def ProcesarPregunta(PreguntaFinal):
    # 1. Avisar qué tokens se encontraron (Feedback de Match)
    Limpia = DbUach.Normalizar(PreguntaFinal)
    Stops = {'con','las','los','del','una','por','que','cual','como','para'}
    Palabras = [P for P in Limpia.split() if len(P) >= 3 and P not in Stops]
    
    Matches = []
    for Bloque in DbUach.Db:
        for Concepto in Bloque.get("conceptos_clave", []):
            Termino = DbUach.Normalizar(Concepto["termino"])
            if any(P in Termino for P in Palabras):
                Matches.append(Concepto["termino"])
    
    if Matches:
        match_msg = f"Encontré información sobre: {', '.join(set(Matches[:2]))}"
        print(f"[LLM] Iniciando generación...")
        # Envía el sonido de "pensando" DESPUÉS del match para que no haya silencio
        EnviarAudio(match_msg, Modo="robot") # BMO asiste diciendo qué encontró
    
    Contexto = DbUach.Buscar(PreguntaFinal)
    if not Contexto:
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

    print(f"[LLM] Procesando: '{PreguntaFinal}'")
    EnviarAudio("Buscando en la base de datos de Chapingo, dame un momento.", Modo="robot")
    Inicio = time.time()

    try:
        EnviarAudio("Dame un segundo, estoy pensando.", Modo="robot")
        print(f"[LLM] Procesando...")
        Stream = ollama.generate(
            model='qwen2:0.5b',
            prompt=Prompt,
            options={'temperature': 0.0, 'num_predict': 200,
                     'stop': ['\n\n', '---']},
            stream=True
        )
        Buffer = ""
        print("[BMO] >> ", end="", flush=True)
        for Chunk in Stream:
            Texto = Chunk.get('response', '')
            print(Texto, end="", flush=True)
            Buffer += Texto
            Oraciones = PatronOracion.findall(Buffer)
            if Oraciones:
                for O in Oraciones:
                    EnviarAudio(O, Modo="normal")
                Buffer = Buffer[Buffer.rfind(Oraciones[-1]) + len(Oraciones[-1]):]
        if Buffer.strip():
            EnviarAudio(Buffer, Modo="normal")

    except Exception as E:
        print(f"\n[ERROR LLM] {E}")
        EnviarAudio("Error al procesar la pregunta.", Modo="robot")

    print(f"\n[TIEMPO] {time.time() - Inicio:.2f}s")

def Chat():
    if os.path.exists(SocketBrain):
        os.remove(SocketBrain)

    Srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    Srv.bind(SocketBrain)
    Srv.listen(1)

    print("\n" + "="*60)
    print("      BMO AGRO-IA v6.0 - SINCRONIZADO")
    print("="*60)

    while True:
        try:
            Conn, _ = Srv.accept()
            Data = Conn.recv(4096).decode("utf-8").strip()
            Conn.close()
            if not Data: continue

            # PASO 1: Bloquear oído antes de nada
            ControlarOido("PAUSA")
            print(f"\n[BRAIN] Procesando: '{Data}'")

            # PASO 2: Generar respuesta
            ProcesarPregunta(Data)

            # PASO 3: Reanudar solo después de que BMO terminó de hablar
            # Nota: Si BmoAudio es asíncrono, asegúrate que termine.
            # Aquí asumimos que EnviarAudio espera o que el flujo es continuo.
            time.sleep(0.5) 
            ControlarOido("REANUDAR")

        except KeyboardInterrupt:
            break
        except Exception as E:
            print(f"[ERROR] {E}")

if __name__ == "__main__":
    Chat()
