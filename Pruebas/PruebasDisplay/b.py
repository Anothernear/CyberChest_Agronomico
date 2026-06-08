import time
from periphery import GPIO, SPI

# Configuración Radxa Cubie A7A
dc = GPIO("/dev/gpiochip0", 313, "out")
rst = GPIO("/dev/gpiochip1", 10,  "out")
spi = SPI("/dev/spidev1.0", 0, 16000000)

def write_cmd(cmd):
    dc.write(False)
    spi.transfer([0x00, cmd])

def write_data_16(val):
    dc.write(True)
    spi.transfer([0x00, val])

def init_display():
    print("Iniciando secuencia BMO...")
    rst.write(False); time.sleep(0.2)
    rst.write(True);  time.sleep(0.2)

    write_cmd(0x11); time.sleep(0.2)    # Sleep Out
    write_cmd(0x3A); write_data_16(0x55) # 16-bit
    write_cmd(0x36); write_data_16(0x28) # Landscape BGR
    
    # --- AJUSTE DE COLOR ---
    # Si se ve rosa, es que necesitamos desactivar o activar la inversión.
    # Prueba con 0x20 si 0x21 sigue dando rosa.
    write_cmd(0x20) 
    
    write_cmd(0x29); time.sleep(0.1)    # Display ON

def draw_block(x, y, w, h, color):
    write_cmd(0x2A)
    write_data_16(x >> 8); write_data_16(x & 0xFF)
    write_data_16((x+w-1) >> 8); write_data_16((x+w-1) & 0xFF)
    
    write_cmd(0x2B)
    write_data_16(y >> 8); write_data_16(y & 0xFF)
    write_data_16((y+h-1) >> 8); write_data_16((y+h-1) & 0xFF)
    
    write_cmd(0x2C)
    dc.write(True)
    
    high, low = (color >> 8) & 0xFF, color & 0xFF
    line_buffer = bytearray([high, low] * w)
    
    for _ in range(h):
        spi.transfer(line_buffer)

try:
    init_display()
    
    # Colores corregidos
    VERDE_BMO = 0x96B2  # Un tono más preciso de BMO
    NEGRO = 0x0000
    
    print("Pintando cara...")
    # Fondo
    draw_block(0, 0, 480, 320, VERDE_BMO)
    
    # Ojos (un poco más estilizados)
    draw_block(150, 80, 30, 70, NEGRO)  # Ojo Izq
    draw_block(300, 80, 30, 70, NEGRO)  # Ojo Der
    
    # Boca
    draw_block(210, 200, 60, 15, NEGRO)
    
    print("¡BMO Configurado!")

finally:
    spi.close(); dc.close(); rst.close()
