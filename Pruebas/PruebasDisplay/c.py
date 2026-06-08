import radxa_display
import time

# SPI 1.0, DC 313, RST 10, 480x320
disp = radxa_display.Display("/dev/spidev1.0", 313, 10, 480, 320)

def paint_red():
    # ROJO PURO: 0xF800
    high = 0xF8
    low = 0x00
    
    # OPCIÓN 1: Si sale amarillo con esta, prueba la OPCIÓN 2
    
    # OPCIÓN 2 (Desfase):
    pixel = bytes([high, 0x00, low, 0x00])
    
    buffer = pixel * (480 * 320)
    disp.send_raw(buffer)

print("Pintando...")
paint_red()
