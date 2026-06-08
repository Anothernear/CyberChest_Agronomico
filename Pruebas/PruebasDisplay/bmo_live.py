import time
import random
import threading
from bmo_hardware import BMODisplay
from bmo_input import buscar_touch, detectar_touch_loop

def iniciar_bmo():
    bmo = BMODisplay()
    
    try:
        # 1. Inicializar hardware
        bmo.init_display()
        bmo.cara_normal()
        
        # 2. Configurar Touch
        touch_dev = buscar_touch()
        if touch_dev:
            # Lanzamos el hilo para que el touch no detenga el parpadeo
            t = threading.Thread(target=detectar_touch_loop, args=(bmo, touch_dev), daemon=True)
            t.start()
        else:
            print("Advertencia: No se detectó panel táctil. BMO solo parpadeará.")

        print("¡BMO ha despertado! (Presiona Ctrl+C para apagar)")
        
        # 3. Bucle de Personalidad (Parpadeo)
        while True:
            if not bmo.sorprendido:
                # Tiempo aleatorio entre parpadeos
                time.sleep(random.uniform(3, 6))
                
                # Doble check antes de dibujar (por si lo tocaron justo ahora)
                if not bmo.sorprendido:
                    # Dibujar ojos cerrados
                    bmo.draw_rect(150, 80, 30, 70, bmo.VERDE_BMO)
                    bmo.draw_rect(300, 80, 30, 70, bmo.VERDE_BMO)
                    bmo.draw_rect(150, 110, 30, 10, bmo.NEGRO)
                    bmo.draw_rect(300, 110, 30, 10, bmo.NEGRO)
                    
                    time.sleep(0.15)
                    
                    # Volver a ojos normales
                    if not bmo.sorprendido:
                        bmo.draw_rect(150, 80, 30, 70, bmo.NEGRO)
                        bmo.draw_rect(300, 80, 30, 70, bmo.NEGRO)
            else:
                # Si está sorprendido, esperamos un poco para no saturar el CPU
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nApagando a BMO... ¡Adiós!")
    finally:
        bmo.cerrar()

if __name__ == "__main__":
    iniciar_bmo()
