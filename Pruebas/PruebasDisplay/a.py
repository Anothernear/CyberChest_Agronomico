import time
from periphery import GPIO, SPI

# Configuración Radxa
dc = GPIO("/dev/gpiochip0", 313, "out")
rst = GPIO("/dev/gpiochip1", 10,  "out")
spi = SPI("/dev/spidev1.0", 0, 16000000) # 16MHz es seguro

def write_cmd(cmd):
    dc.write(False)
    # CMD en 16 bits: [0x00, CMD]
    spi.transfer([0x00, cmd])

def write_data_16(val):
    dc.write(True)
    # PARÁMETROS en 16 bits: [0x00, VAL]
    # Esto es vital si regwidth=16 está activo en el hardware
    spi.transfer([0x00, val])

def init_display():
    print("Reset...")
    rst.write(False); time.sleep(0.1); rst.write(True); time.sleep(0.2)
    
    write_cmd(0x11); time.sleep(0.15) # Sleep Out
    
    # Interface Pixel Format
    write_cmd(0x3A); write_data_16(0x55) # 16-bit
    
    # MADCTL: Probemos 0x28 (Landscape BGR)
    write_cmd(0x36); write_data_16(0x28) 
    
    write_cmd(0x11); time.sleep(0.1)
    write_cmd(0x29); time.sleep(0.1) # Display ON
    print("Display ON enviado.")

def draw_test(color):
    w, h = 480, 320
    
    # Columnas: Enviar cada byte como parámetro de 16 bits
    write_cmd(0x2A)
    write_data_16(0x00); write_data_16(0x00); # Start 0
    write_data_16((w-1) >> 8); write_data_16((w-1) & 0xFF); # End 479
    
    # Filas
    write_cmd(0x2B)
    write_data_16(0x00); write_data_16(0x00); # Start 0
    write_data_16((h-1) >> 8); write_data_16((h-1) & 0xFF); # End 319
    
    write_cmd(0x2C) # RAM Write
    dc.write(True)
    
    # Los PIXELES se envían como ráfaga de 8 bits (2 bytes por pixel)
    high, low = (color >> 8) & 0xFF, color & 0xFF
    # Buffer de una línea (480 px)
    linea = bytearray([high, low] * w)
    
    for _ in range(h):
        spi.transfer(linea)

try:
    init_display()
    print("Pintando Rojo...")
    draw_test(0xF800) 
    print("Fin.")
finally:
    spi.close(); dc.close(); rst.close()

