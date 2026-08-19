<div align="center">

  # Asistente Virtual de Escritorio (Desktop Assistant)

  <!-- Badges de Tecnologías -->
  <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PyQt5-41CD52?style=for-the-badge&logo=qt&logoColor=white" />

  <p><i>Asistente flotante interactiva multiplataforma con personalidad Tsundere, integrada con Gemini 2.5 Flash, TTS neuronal, control multimedia MPRIS y monitoreo de sistema.</i></p>

</div>

## ✨ Características Principales

**Mover la de lugar: alt + click izquierdo**
* 🧠 **IA Integrada (Gemini 2.5 Flash):** Respuestas avanzadas con personalidad Tsundere.
* 🎧 **Detección de Música en Vivo (MPRIS / `playerctl`):** Muestra automáticamente la canción en reproducción (`♫ título - artista ♪`), cambia el estado a *feliz* y desactiva el modo sueño mientras suena música.
* 🗣️ **Voz Neuronal Anime (`edge-tts` + `pygame`):** Síntesis de voz en tiempo real con la voz `es-MX-DaliaNeural` ejecutada en hilos secundarios para no congelar la interfaz gráfica.
* 💬 **Globo Manga con Efecto Máquina de Escribir:** Interfaz con renderizado personalizado tipo cómic/anime (`GloboTexto`) y animación de mecanografía a 20 ms.
* 🎭 **Expresiones Dinámicas y Outfits:** 8 estados emocionales (*normal*, *pensando*, *feliz*, *durmiendo*, *sonrojada*, *enojada*, *triste*, *bailando*) y alternancia de vestimentas (*looks* alternativos).
* ⚡ **Control del Sistema y Procesos:**
  * **Monitor de RAM y Matador de Procesos:** Identificación del Top 3 de consumo de memoria y finalización de procesos por nombre (`"cierra firefox"`).
  * **Lanzador Personalizado (`atajos.json`):** Ejecución de programas del sistema (terminales, navegadores, etc.).
  * **Captura de Pantalla:** Integración con utilidades del sistema (`xfce4-screenshooter`).
  * **Fijación de Posición:** Comandos locales para bloquear/desbloquear la ventana en la pantalla (`"fijar"`, `"desbloquear"`).
* 📝 **Gestión de Pendientes y Recordatorios:**
  * Persistencia de tareas pendientes almacenadas en `pendientes.json`.
  * Temporizador de recordatorios programables (`"recuérdame en X minutos..."`).
* 🌙 **Modo Noche e Inactividad Inteligente:** Activación automática de estado de reposo en horario nocturno (22:00 a 06:00) o tras 60 segundos de inactividad (pausado si hay música en curso).

---

## 🛠️ Requisitos e Instalación

### 1. Dependencias del Sistema

**Linux (Debian / Ubuntu / Mint):**
```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev xfce4-screenshooter playerctl
