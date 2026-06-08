import time
from periphery import GPIO, SPI

class BMODisplay:
    def __init__(self):
        # --- CONFIGURACIÓN HARDWARE ---
        self.dc = GPIO("/dev/gpiochip0", 313, "out")
        self.rst = GPIO("/dev/gpiochip1", 10,  "out")
        self.spi = SPI("/dev/spidev1.0", 0, 16000000)
        
        self.VERDE_BMO = 0x96B2 
        self.NEGRO = 0x0000
        self.sorprendido = False

    def _write_cmd(self, cmd):
        self.dc.write(False)
        self.spi.transfer([0x00, cmd])

    def _write_data_16(self, val):
        self.dc.write(True)
        self.spi.transfer([0x00, val])

    def init_display(self):
        self.rst.write(False); time.sleep(0.1); self.rst.write(True); time.sleep(0.1)
        self._write_cmd(0x11); time.sleep(0.1)
        self._write_cmd(0x3A); self._write_data_16(0x55)
        self._write_cmd(0x36); self._write_data_16(0x28)
        self._write_cmd(0x20) 
        self._write_cmd(0x29)

    def draw_rect(self, x, y, w, h, color):
        self._write_cmd(0x2A)
        self._write_data_16(x >> 8); self._write_data_16(x & 0xFF)
        self._write_data_16((x+w-1) >> 8); self._write_data_16((x+w-1) & 0xFF)
        self._write_cmd(0x2B)
        self._write_data_16(y >> 8); self._write_data_16(y & 0xFF)
        self._write_data_16((y+h-1) >> 8); self._write_data_16((y+h-1) & 0xFF)
        self._write_cmd(0x2C)
        self.dc.write(True)
        line = bytearray([(color >> 8) & 0xFF, color & 0xFF] * w)
        for _ in range(h):
            self.spi.transfer(line)

    def cara_normal(self):
        self.draw_rect(0, 0, 480, 320, self.VERDE_BMO)
        self.draw_rect(150, 80, 30, 70, self.NEGRO)  # Ojo L
        self.draw_rect(300, 80, 30, 70, self.NEGRO)  # Ojo R
        self.draw_rect(210, 220, 60, 15, self.NEGRO) # Boca

    def cara_sorpresa(self):
        self.draw_rect(140, 70, 50, 90, self.NEGRO)   # Ojo L grande
        self.draw_rect(290, 70, 50, 90, self.NEGRO)   # Ojo R grande
        self.draw_rect(215, 200, 50, 50, self.NEGRO)  # Boca circular
        
    def cerrar(self):
        self.spi.close()
        self.dc.close()
        self.rst.close()
