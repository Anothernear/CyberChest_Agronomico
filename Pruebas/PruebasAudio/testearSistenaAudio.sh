#!/bin/bash

# Script de prueba de audio para Radxa/Debian
echo "--- MENÚ DE TEST DE AUDIO ---"
echo "1) Bucle Micrófono -> Altavoz (alsaloop)"
echo "2) Visualizador de niveles de Mic (arecord)"
echo "3) Test de Altavoces: Ruido Rosa (speaker-test)"
echo "4) Test de Altavoces: Voz 'Front Left/Right' (speaker-test wav)"
echo "5) Salir"

read -p "Seleccione una opción [1-5]: " opcion

case $opcion in
    1)
        echo "Iniciando bucle. Presiona Ctrl+C para salir..."
        alsaloop -C hw:1,0 -P hw:1,0 -t 50000
        ;;
    2)
        echo "Monitoreando micrófono (escala visual). Presiona Ctrl+C para salir..."
        arecord -D pulse -d 0 -V mono /dev/null
        ;;
    3)
        echo "Iniciando ruido rosa (Pink Noise)..."
        # -c 2 para estéreo, -l 3 para tres repeticiones
        speaker-test -t pink -c 2 -l 3
        ;;
    4)
        echo "Reproduciendo voces de prueba por canales..."
        # -t wav reproduce archivos de voz predefinidos en /usr/share/sounds/alsa/
        speaker-test -t wav -c 2 -l 2
        ;;
    5)
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo "Opción inválida."
        ;;
esac
