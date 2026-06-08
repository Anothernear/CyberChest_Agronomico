use spidev::{Spidev, SpidevOptions, SpiModeFlags};
use input_linux::{EvdevHandle};
use gpiod::{Chip, Options, Output, Lines};
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Write};
use std::time::{Duration, Instant};
use std::thread;
use std::sync::{Arc, Mutex};
use std::os::unix::fs::FileTypeExt;

const WIDTH: u16 = 480;
const HEIGHT: u16 = 320;
const VERDE_BMO: u16 = 0x96B2; 
const NEGRO: u16 = 0x0000;

struct BMO {
    spi: Spidev,
    dc: Lines<Output>,
    rst: Lines<Output>,
}

impl BMO {
    fn new() -> Self {
        let mut spi = Spidev::open("/dev/spidev1.0").expect("Error SPI");
        let options = SpidevOptions::new()
            .bits_per_word(8)
            .max_speed_hz(16_000_000) 
            .mode(SpiModeFlags::SPI_MODE_0)
            .build();
        spi.configure(&options).unwrap();

        let chip0 = Chip::new("/dev/gpiochip0").unwrap();
        let dc = chip0.request_lines(Options::output([313]).consumer("bmo_dc")).unwrap();
        
        let chip1 = Chip::new("/dev/gpiochip1").unwrap();
        let rst = chip1.request_lines(Options::output([10]).consumer("bmo_rst")).unwrap();

        let mut bmo = BMO { spi, dc, rst };
        bmo.init_display();
        bmo
    }

    fn write_cmd(&mut self, cmd: u8) {
        self.dc.set_values([false]).unwrap();
        let _ = self.spi.write_all(&[0x00, cmd]); 
    }

    fn write_data_16(&mut self, val: u8) {
        self.dc.set_values([true]).unwrap();
        let _ = self.spi.write_all(&[0x00, val]);
    }

    fn init_display(&mut self) {
        self.rst.set_values([false]).unwrap();
        thread::sleep(Duration::from_millis(100));
        self.rst.set_values([true]).unwrap();
        thread::sleep(Duration::from_millis(100));
        self.write_cmd(0x11);
        thread::sleep(Duration::from_millis(100));
        self.write_cmd(0x3A); self.write_data_16(0x55);
        self.write_cmd(0x36); self.write_data_16(0x28);
        self.write_cmd(0x20);
        self.write_cmd(0x29);
        thread::sleep(Duration::from_millis(50));
    }

    fn draw_rect(&mut self, x: u16, y: u16, w: u16, h: u16, color: u16) {
        let x2 = x + w - 1;
        let y2 = y + h - 1;
        self.write_cmd(0x2A);
        self.write_data_16((x >> 8) as u8); self.write_data_16((x & 0xFF) as u8);
        self.write_data_16((x2 >> 8) as u8); self.write_data_16((x2 & 0xFF) as u8);
        self.write_cmd(0x2B);
        self.write_data_16((y >> 8) as u8); self.write_data_16((y & 0xFF) as u8);
        self.write_data_16((y2 >> 8) as u8); self.write_data_16((y2 & 0xFF) as u8);
        self.write_cmd(0x2C);
        self.dc.set_values([true]).unwrap();
        let c_high = (color >> 8) as u8;
        let c_low = (color & 0xFF) as u8;
        let mut line = Vec::with_capacity(w as usize * 2);
        for _ in 0..w { line.push(c_high); line.push(c_low); }
        for _ in 0..h { let _ = self.spi.write_all(&line); }
    }

    fn cara_normal(&mut self) {
        self.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
        self.draw_rect(150, 80, 30, 70, NEGRO);
        self.draw_rect(300, 80, 30, 70, NEGRO);
        self.draw_rect(210, 220, 60, 15, NEGRO);
    }

    fn cara_sorpresa(&mut self) {
        self.draw_rect(140, 70, 50, 90, NEGRO);
        self.draw_rect(290, 70, 50, 90, NEGRO);
        self.draw_rect(215, 200, 50, 50, NEGRO);
    }
}

fn main() {
    let sorprendido = Arc::new(Mutex::new(false));
    let sorprendido_thread = Arc::clone(&sorprendido);

    // 1. Hilo del Touch
    thread::spawn(move || {
        let touch_file = fs::OpenOptions::new().read(true).open("/dev/input/event11").unwrap();
        let touch = EvdevHandle::new(touch_file);
        loop {
            let mut events = [input_linux::sys::input_event {
                time: input_linux::sys::timeval { tv_sec: 0, tv_usec: 0 },
                type_: 0, code: 0, value: 0,
            }; 16];
            if let Ok(count) = touch.read(&mut events) {
                for i in 0..count {
                    if events[i].code == 330 {
                        let mut s = sorprendido_thread.lock().unwrap();
                        *s = events[i].value == 1;
                    }
                }
            }
        }
    });

    // 2. Crear Pipe FIFO
    let pipe_path = "/tmp/bmo_pipe";
    if !fs::metadata(pipe_path).map(|m| m.file_type().is_fifo()).unwrap_or(false) {
        let _ = std::process::Command::new("mkfifo").arg(pipe_path).status();
    }

    let bmo = BMO::new();
    let bmo_arc = Arc::new(Mutex::new(bmo));
    {
        let mut b = bmo_arc.lock().unwrap();
        b.cara_normal();
    }

    let bmo_cmd = Arc::clone(&bmo_arc);
    let mut ultimo_blink = Instant::now();
    let mut estado_actual = false;

    // 3. Hilo para comandos de Python (Expresiones)
    thread::spawn(move || {
        loop {
            if let Ok(file) = File::open("/tmp/bmo_pipe") {
                let reader = BufReader::new(file);
                for line in reader.lines() {
                    if let Ok(cmd) = line {
                        let mut b = bmo_cmd.lock().unwrap();
                        match cmd.as_str() {
                            "normal" => b.cara_normal(),
                            "sorpresa" => b.cara_sorpresa(),
                            
                            "hablar" => {
                                for _ in 0..3 {
                                    b.draw_rect(210, 220, 60, 20, NEGRO); // Abre
                                    thread::sleep(Duration::from_millis(100));
                                    b.draw_rect(210, 220, 60, 20, VERDE_BMO); // Cierra
                                    b.draw_rect(210, 225, 60, 5, NEGRO); 
                                    thread::sleep(Duration::from_millis(100));
                                }
                                b.cara_normal();
                            },
                        
                            "pensar" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                b.draw_rect(150, 60, 30, 40, NEGRO); // Ojos arriba
                                b.draw_rect(300, 60, 30, 40, NEGRO);
                                b.draw_rect(210, 220, 40, 5, NEGRO); // Boca pequeña
                            },
                        
                            "enojado" => {
                                b.cara_normal();
                                // Cejas enojadas tapando la parte superior del ojo
                                b.draw_rect(140, 70, 60, 25, VERDE_BMO); 
                                b.draw_rect(280, 70, 60, 25, VERDE_BMO);
                                b.draw_rect(210, 220, 60, 8, NEGRO); // Boca seria
                            },
                        
                            "triste" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                b.draw_rect(150, 100, 30, 40, NEGRO);
                                b.draw_rect(300, 100, 30, 40, NEGRO);
                                // Boca triste (forma de U invertida)
                                b.draw_rect(210, 230, 60, 5, NEGRO);
                                b.draw_rect(210, 230, 5, 15, NEGRO);
                                b.draw_rect(265, 230, 5, 15, NEGRO);
                            },
                        
                            "feliz" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                // Ojos de "paréntesis" (^)
                                b.draw_rect(150, 90, 30, 10, NEGRO);
                                b.draw_rect(300, 90, 30, 10, NEGRO);
                                // Gran sonrisa
                                b.draw_rect(200, 210, 80, 5, NEGRO);
                                b.draw_rect(200, 210, 5, 20, NEGRO);
                                b.draw_rect(275, 210, 5, 20, NEGRO);
                                b.draw_rect(200, 230, 80, 5, NEGRO);
                            },
                        
                            "dormido" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                // Ojos cerrados (líneas horizontales)
                                b.draw_rect(150, 120, 40, 5, NEGRO);
                                b.draw_rect(290, 120, 40, 5, NEGRO);
                                // Boca pequeña de sueño
                                b.draw_rect(230, 220, 20, 10, NEGRO);
                            },
                        
                            "guiño" => {
                                b.cara_normal();
                                b.draw_rect(300, 80, 30, 70, VERDE_BMO); // Borra ojo derecho
                                b.draw_rect(300, 115, 40, 8, NEGRO); // Línea de guiño
                                thread::sleep(Duration::from_secs(1));
                                b.cara_normal();
                            },
                        
                            "sonrojado" => {
                                b.cara_normal();
                                // Chapitas rosadas (si tu pantalla es color, usa un color rosado 0xF812)
                                // Usaremos NEGRO con patron para simular si no tienes colores definidos
                                b.draw_rect(100, 160, 40, 20, NEGRO); 
                                b.draw_rect(340, 160, 40, 20, NEGRO);
                            },
                        
                            "llorar" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                b.draw_rect(150, 90, 30, 40, NEGRO);
                                b.draw_rect(300, 90, 30, 40, NEGRO);
                                // Lagrimas cayendo
                                for i in 0..5 {
                                    b.draw_rect(160, 140 + (i*15), 10, 10, NEGRO);
                                    b.draw_rect(310, 140 + (i*15), 10, 10, NEGRO);
                                    thread::sleep(Duration::from_millis(100));
                                }
                                b.cara_normal();
                            },
                        
                            "muerto" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, NEGRO); // Pantalla negra
                                // Ojos de X
                                b.draw_rect(150, 100, 40, 5, VERDE_BMO);
                                b.draw_rect(300, 100, 40, 5, VERDE_BMO);
                                // Boca de X o plana
                                b.draw_rect(210, 220, 60, 2, VERDE_BMO);
                            },
                        
                            "loading" => {
                                b.draw_rect(0, 0, WIDTH, HEIGHT, VERDE_BMO);
                                // Un cuadradito que gira (animación simple)
                                for i in 0..4 {
                                    let pos = [(200,100), (250,150), (200,200), (150,150)];
                                    b.draw_rect(pos[i].0, pos[i].1, 30, 30, NEGRO);
                                    thread::sleep(Duration::from_millis(200));
                                    b.draw_rect(pos[i].0, pos[i].1, 30, 30, VERDE_BMO);
                                }
                                b.cara_normal();
                            },
                        
                            _ => ()
                        }
                    }
                }
            }
        }
    });

    // Loop Principal: Parpadeo y Sincronización
    loop {
        let esta_sorprendido = { *sorprendido.lock().unwrap() };

        if esta_sorprendido != estado_actual {
            let mut b = bmo_arc.lock().unwrap();
            if esta_sorprendido { b.cara_sorpresa(); }
            else { b.cara_normal(); ultimo_blink = Instant::now(); }
            estado_actual = esta_sorprendido;
        }

        if !esta_sorprendido && ultimo_blink.elapsed() > Duration::from_secs(5) {
            let mut b = bmo_arc.lock().unwrap();
            b.draw_rect(150, 80, 30, 70, VERDE_BMO);
            b.draw_rect(300, 80, 30, 70, VERDE_BMO);
            b.draw_rect(150, 110, 30, 10, NEGRO);
            b.draw_rect(300, 110, 30, 10, NEGRO);
            thread::sleep(Duration::from_millis(150));
            b.draw_rect(150, 110, 30, 10, VERDE_BMO);
            b.draw_rect(300, 110, 30, 10, VERDE_BMO);
            b.draw_rect(150, 80, 30, 70, NEGRO);
            b.draw_rect(300, 80, 30, 70, NEGRO);
            ultimo_blink = Instant::now();
        }
        thread::sleep(Duration::from_millis(50));
    }
}
