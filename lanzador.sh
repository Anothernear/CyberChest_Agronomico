#!/bin/bash

#####################################
# Este script lanzador.sh es el orquestador
# principal de BMO. Su trabajo no es procesar
# la IA directamente, sino actuar como el director:
# levanta los scripts de Python, limpia la memoria de
# la Radxa, decora la terminal con colores y controla
# el ciclo de vida del robot para que escuche, procese
# y hable en el orden correcto sin que los módulos se 
# pisen entre sí.
#####################################

# --- CONFIGURACIÓN ---
BMO_DIR="/home/radxa/Documents/BMO"
VENV="$BMO_DIR/venv_bmo/bin/activate"
ESC=$(printf '\033')

# Colores BMO
CYAN="${ESC}[36m"
GREEN="${ESC}[32m"
YELLOW="${ESC}[33m"
BLUE="${ESC}[34m"
RED="${ESC}[31m"
RESET="${ESC}[0m"

soft_cleanup() {
    # Liberar el hardware de la Radxa (Allwinner A733)
    sudo fuser -k /dev/snd/pcmC1D0c 2>/dev/null
    # Limpiar solo semáforos de flujo, mantenemos sockets vivos
    rm -f /tmp/brain_done /tmp/bmo_speaking
}

source $VENV
cd $BMO_DIR

# Reinicio limpio de servicios
pkill -f BmoAudio.py
pkill -f BmoBrain.py
rm -f /tmp/bmo_*.sock
rm -f /tmp/bmo_mode
sleep 1

echo -e "${CYAN}[SISTEMA] Despertando módulos de BMO...${RESET}"

# Iniciar Audio y Cerebro PRIMERO (en background)
python3 -u BmoAudio.py 2>&1 | sed "s/^/${CYAN}[AUDIO] ${RESET} /" &
python3 -u BmoBrain.py 2>&1 | sed "s/^/${GREEN}[BRAIN] ${RESET} /" &

# Esperar a que los sockets estén listos
echo -e "${BLUE}[SISTEMA] Esperando módulos...${RESET}"
while [ ! -S /tmp/bmo_brain.sock ]; do sleep 0.5; done
while [ ! -S /tmp/bmo_audio.sock ]; do sleep 0.5; done

# Enviar saludo robotizado
echo -e "${CYAN}[AUDIO] Enviando saludo inicial...${RESET}"
python3 -c 'import socket; s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect("/tmp/bmo_audio.sock"); s.sendall("robot|El cyberchest te escucha.".encode("utf-8")); s.close()'
sleep 3

# Preguntar modo de operación
echo -e "${BLUE}[MODO] Preguntando modo de operación...${RESET}"
python3 -c 'import socket; s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect("/tmp/bmo_audio.sock"); s.sendall("normal|¿Quieres seleccionar modo normal o superior?".encode("utf-8")); s.close()'
sleep 4

# El cerebro interceptará la respuesta automáticamente
echo -e "${YELLOW}[SISTEMA] Esperando selección de modo...${RESET}"

while true; do
    echo -e "\n${GREEN}==========================================${RESET}"
    echo -e "${GREEN}      BMO AGRO-IA v10.5 (COLOR SYNC)      ${RESET}"
    echo -e "${GREEN}==========================================${RESET}"

    soft_cleanup
    
    echo -e "${YELLOW}[OÍDO]  Escuchando...${RESET}"
    # Oído corre en primer plano y se cierra al detectar voz
    python3 -u BmoEar.py 2>&1 | sed "s/^/${YELLOW}[OÍDO]  ${RESET} /"
    
    # Verificamos si el Oído cerró por detección (si no hay socket de cerebro, algo falló)
    if [ ! -S /tmp/bmo_brain.sock ]; then
        echo -e "${RED}[ERROR] El Cerebro se desconectó. Reintentando...${RESET}"
        python3 -u BmoBrain.py 2>&1 | sed "s/^/${GREEN}[BRAIN] ${RESET} /" &
        sleep 2
    fi

    echo -e "${BLUE}[ESPERA] Procesando en LLM...${RESET}"
    echo "pensar" > /tmp/bmo_pipe
    echo "normal" > /tmp/bmo_pipe
    while [ ! -f /tmp/brain_done ]; do
        sleep 0.1
    done

    echo -e "${CYAN}[AUDIO] Reproduciendo respuesta...${RESET}"
    # 1. Forzamos el inicio de la animación
    echo "hablar" > /tmp/bmo_pipe 2>/dev/null
    
    counter=0
    while [ -f /tmp/bmo_speaking ]; do
        sleep 0.1
        counter=$((counter + 1))
        
        # 2. Cada 0.8 segundos (8 ciclos de 0.1s) volvemos a enviar "hablar"
        # para mantener la boca moviéndose mientras el archivo exista
        if [ "$counter" -ge 8 ]; then
            echo "hablar" > /tmp/bmo_pipe 2>/dev/null
            counter=0
        fi
    done
    
    # 3. Al terminar el audio, forzamos el cierre de boca
    echo "normal" > /tmp/bmo_pipe 2>/dev/null

    echo -e "${GREEN}[LISTO] Ciclo completado. Reiniciando...${RESET}"
    sleep 0.2
done
