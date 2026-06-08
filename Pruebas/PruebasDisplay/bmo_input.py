from evdev import InputDevice, ecodes, list_devices

def buscar_touch():
    """Busca dinámicamente el dispositivo ADS7846/Touchscreen"""
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        if "touchscreen" in device.name.lower() or "ads7846" in device.name.lower():
            return device
    return None

def detectar_touch_loop(bmo, touch_dev):
    """Bucle que escucha los eventos del touch"""
    print(f"BMO escuchando tacto en: {touch_dev.name}")
    try:
        for event in touch_dev.read_loop():
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                if event.value == 1: # Presionado
                    bmo.sorprendido = True
                    bmo.cara_sorpresa()
                else: # Soltado
                    bmo.sorprendido = False
                    bmo.cara_normal()
    except Exception as e:
        print(f"Conexión con el touch perdida: {e}")
