#!/bin/bash

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
sleep 1

echo -e "${CYAN}[SISTEMA] Despertando módulos de BMO...${RESET}"

# Iniciar Audio y Cerebro con tus filtros de colores originales
python3 -u BmoAudio.py 2>&1 | sed "s/^/${CYAN}[AUDIO] ${RESET} /" &
python3 -u BmoBrain.py 2>&1 | sed "s/^/${GREEN}[BRAIN] ${RESET} /" &

# Esperar a que el Cerebro esté listo
while [ ! -S /tmp/bmo_brain.sock ]; do sleep 0.5; done

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
    while [ ! -f /tmp/brain_done ]; do
        sleep 0.1
    done
    
    echo -e "${CYAN}[AUDIO] Reproduciendo respuesta...${RESET}"
    sleep 1.5 # Tiempo para que empiece a sonar
    while [ -f /tmp/bmo_speaking ]; do
        sleep 0.1
    done

    echo -e "${GREEN}[LISTO] Ciclo completado. Reiniciando...${RESET}"
    sleep 0.2
done
