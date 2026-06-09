#!/bin/bash

# ID de la tarjeta de sonido de la Radxa (Allwinner A733)
DEV_ID="1"

limpiar_pantalla() {
    clear
}

menu_principal() {
    while true; do
        limpiar_pantalla
        echo "=================================================="
        echo -e "\e[36m          🎛️  MENÚ DE AUDIO BMO (BASH)             \e[0m"
        echo "=================================================="
        echo "1) Probar canal: LEFT (Izquierdo - Voz Continua)"
        echo "2) Probar canal: RIGHT (Derecho - Voz Continua)"
        echo "3) Salir"
        echo "--------------------------------------------------"
        read -p "Selecciona una opción [1-3]: " opcion

        case $opcion in
            1)
                limpiar_pantalla
                echo "=================================================="
                echo -e "\e[34m🔊 EJECUTANDO: speaker-test -c 1 -D hw:$DEV_ID,0 -t wav\e[0m"
                echo "=================================================="
                echo -e "\e[31m🛑 Presiona [Ctrl + C] para DETENER el audio.\e[0m"
                echo "=================================================="
                echo ""
                
                # Tu comando exacto. Al ser '-c 1' ALSA lo cicla infinitamente por defecto
                speaker-test -c 1 -D hw:$DEV_ID,0 -t wav > /dev/null 2>&1
                
                echo -e "\n\e[32m🛑 [SISTEMA] Audio detenido.\e[0m"
                echo "--------------------------------------------------"
                read -p "⌨️  Presiona [ENTER] para regresar al menú..."
                ;;
            2)
                limpiar_pantalla
                echo "=================================================="
                echo -e "\e[34m🔊 EJECUTANDO: speaker-test -c 2 -D hw:$DEV_ID,0 -t wav\e[0m"
                echo "=================================================="
                echo -e "\e[31m🛑 Presiona [Ctrl + C] para DETENER el audio.\e[0m"
                echo "=================================================="
                echo ""
                
                # Para el derecho usamos '-c 2'. Va a alternar entre Left y Right de forma nativa y continua
                speaker-test -c 2 -D hw:$DEV_ID,0 -t wav > /dev/null 2>&1
                
                echo -e "\n\e[32m🛑 [SISTEMA] Audio detenido.\e[0m"
                echo "--------------------------------------------------"
                read -p "⌨️  Presiona [ENTER] para regresar al menú..."
                ;;
            3)
                echo -e "\nSaliendo."
                exit 0
                ;;
            *)
                echo -e "\e[31mOpción no válida.\e[0m"
                sleep 1
                ;;
        esac
    done
}

# Liberar hardware antes de arrancar
sudo fuser -k /dev/snd/pcmC1D0c > /dev/null 2>&1
sleep 0.1

menu_principal
