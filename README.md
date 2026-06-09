
# BMO - CyberChest Agronómico

Este módulo contiene la lógica central, el procesamiento de audio, la síntesis de voz y el control de hardware para el robot BMO, ejecutado sobre el hardware embebido **Radxa Cubie A7A**.

---

## 📋 Requisitos del Sistema

* **Hardware:** Radxa Cubie A7A (Allwinner A733).
* **Periféricos:** Pantalla SPI ILI9486, micrófono/altavoz USB o HAT de audio.
* **Sistemas Operativos:** Distribuciones Linux optimizadas para arquitectura ARM (ej. Parrot OS / Debian).
* **Dependencias Principales:** Python 3.10+, Virtualenv.

---

## ⚙️ Instalación y Configuración del Entorno

Para desplegar y ejecutar este proyecto localmente en la placa, sigue estos pasos:

1. **Clonar el repositorio y acceder al directorio:**
   ```bash
   git clone [https://github.com/Anothernear/CyberChest_Agronomico.git](https://github.com/Anothernear/CyberChest_Agronomico.git)
   cd CyberChest_Agronomico

```

---

## 🪵 Arquitectura del Orquestador (`lanzador.sh`)

El ciclo de vida y la sincronización de los módulos de BMO son gestionados por el script `lanzador.sh`. En lugar de utilizar un único proceso monolítico, el sistema implementa una **arquitectura desacoplada basada en Sockets UNIX y Banderas Temporales (`/tmp`)**, optimizando el uso de recursos en el hardware embebido (Allwinner A733).

### 🔄 Flujo de Trabajo y Ciclo de Vida

El orquestador divide la ejecución en dos capas:

* **Servicios Asíncronos:** Siempre activos en segundo plano.
* **Bucle de Interacción Síncrono:** Secuencia clásica de *Escuchar-Pensar-Hablar*.

```text
       [ Lanzador.sh ] ──> Levanta en Background ──> BmoAudio.py & BmoBrain.py
             │
             ▼ (Bucle Infinito)
    ┌───────────────────┐
    │   1. BmoEar.py    │ <── (Filtro Oído: Corre en primer plano)
    └─────────┬─────────┘
              │ (Cierra al detectar silencio / fin de voz)
              ▼
    ┌───────────────────┐
    │    Espere LLM     │ <── (Bloqueado hasta que aparece /tmp/brain_done)
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ Reproducción TTS  │ <── (Bloqueado mientras exista /tmp/bmo_speaking)
    └─────────┬─────────┘
              │
              ▼ ( soft_cleanup(): Libera /dev/snd/pcmC1D0c )
       [ Reinicia Ciclo ]

```
