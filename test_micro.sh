#!/bin/bash

# ID de la tarjeta de sonido de la Radxa (Allwinner A733)
DEV_ID="1"

limpiar_pantalla() {
    clear
}

# Forzar liberación del hardware por si acaso antes de empezar
sudo fuser -k /dev/snd/pcmC1D0c > /dev/null 2>&1
sleep 0.1

limpiar_pantalla
echo "=================================================="
echo -e "\e[36m        🎤 MONITOREO DE MICRÓFONO (BASH)         \e[0m"
echo "=================================================="
echo "📢 Habla fuerte para ver la barra moverse en vivo."
echo -e "\e[31m🛑 Presiona [Ctrl + C] para DETENER el monitoreo.\e[0m"
echo "=================================================="
echo ""

# Lanzamos arecord configurado en Mono (-c 1) a 16000Hz (como tu Vosk)
# La bandera --vumeter=mono dibuja la barra nativa de porcentaje en la terminal
# Mandamos el flujo de audio a /dev/null porque solo nos interesa ver el vúmetro
arecord -D hw:$DEV_ID,0 -c 1 -r 16000 -f S16_LE --vumeter=mono /dev/null

# Al presionar Ctrl+C, arecord muere limpiamente y el script cae aquí de inmediato
echo -e "\n\n\e[32m🛑 [SISTEMA] Monitoreo detenido.\e[0m"
echo "--------------------------------------------------"
read -p "⌨️  Presiona [ENTER] para salir..."
