# 🔊 Activar ruta de audífonos COMPLETA
amixer -c 1 sset 'HPOUT' on
amixer -c 1 sset 'HPOUT Gain' 7

# 🔊 Activar salida de línea (a veces necesaria internamente)
amixer -c 1 sset 'LINEOUTL' on
amixer -c 1 sset 'LINEOUTR' on

# 🔊 Activar speaker path (muchos codecs lo requieren aunque uses jack)
amixer -c 1 sset 'SPK' on

# 🔊 Ganancia analógica global
amixer -c 1 sset 'DAC Gain' 7

# 🔊 Volumen digital
amixer -c 1 sset 'DACL' 255
amixer -c 1 sset 'DACR' 255
