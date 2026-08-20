import sys
import os
import random
import time
import json
import subprocess
import threading
import psutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QScrollArea
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPolygon
from PyQt5.QtCore import Qt, QPoint, QTimer
from google import genai

# --- CONFIGURACIÓN DE API KEY ---
API_KEY = "TU_API_KEY_AQUI"

class GloboTexto(QWidget):
    """
    Contenedor estilo globo de diálogo
    con fondo #1e1e2e, borde #b4befe y pico apuntando hacia abajo.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.color_fondo = QColor(30, 30, 46, 240)
        self.color_borde = QColor(180, 190, 254)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 18)
        self.setLayout(layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ancho = self.width()
        alto = self.height() - 12

        painter.setBrush(self.color_fondo)
        painter.setPen(self.color_borde)
        painter.drawRoundedRect(2, 2, ancho - 4, alto - 4, 12, 12)

        pico_centro = ancho // 2
        pico = QPolygon([
            QPoint(pico_centro - 10, alto - 2),
            QPoint(pico_centro + 10, alto - 2),
            QPoint(pico_centro, alto + 10)
        ])
        
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(pico)

        painter.setPen(self.color_borde)
        painter.drawLine(pico_centro - 10, alto - 2, pico_centro, alto + 10)
        painter.drawLine(pico_centro + 10, alto - 2, pico_centro, alto + 10)

class MascotaDesktop(QWidget):
    def __init__(self):
        super().__init__()

        self.posicion_fijada = False  # Estado de bloqueo de posición
        self.arrastrando = False     # Control de arrastre con Shift

        # --- DETECCIÓN DE MÚSICA (MPRIS) ---
        self.current_song = ""
        self.is_playing_music = False
        self.is_talking = False

        # --- MÁQUINA DE ESCRIBIR (TYPING EFFECT 20 ms) ---
        self.texto_completo_animacion = ""
        self.indice_caracter_animacion = 0
        self.timer_escritura = QTimer(self)
        self.timer_escritura.setInterval(20)
        self.timer_escritura.timeout.connect(self._paso_maquina_escribir)

        # Obtiene la carpeta raíz donde reside el script
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        # --- Rutas
        self.rutas_imagenes = {
            "normal": os.path.join(BASE_DIR, "assets", "mascota.png"),
            "pensando": os.path.join(BASE_DIR, "assets", "pensando.png"),
            "feliz": os.path.join(BASE_DIR, "assets", "feliz.png"),
            "durmiendo": os.path.join(BASE_DIR, "assets", "durmiendo.png"),
            "sonrojada": os.path.join(BASE_DIR, "assets", "sonrojada.png"),
            "enojada": os.path.join(BASE_DIR, "assets", "enojada.png"),
            "triste": os.path.join(BASE_DIR, "assets", "triste.png"),
            "bailando": os.path.join(BASE_DIR, "assets", "bailando.png")
        }
        
        self.looks_alternativos = [
            os.path.join(BASE_DIR, "assets", "mascota.png"),
            os.path.join(BASE_DIR, "assets", "look1.png"),
            os.path.join(BASE_DIR, "assets", "look2.png"),
            os.path.join(BASE_DIR, "assets", "look3.png"),
            os.path.join(BASE_DIR, "assets", "look4.png")
        ]
        
        self.indice_look_actual = 0
        self.bloqueo_look = False
        self.inactivo = False

        # Configuración del modelo IA de asistencia
        self.system_instruction = (
            "Eres un asistente virtual llamada Sona de escritorio profesional, formal y eficiente."
            "Tu prioridad es responder a las preguntas del usuario de forma clara, concisa, respetuosa, precisa y con alegria."
        )
        self._inicializar_chat()

        self.oldPos = QPoint()
        self.initUI()
        self.cargar_atajos_custom()

        # Temporizador de inactividad (60 segundos)
        self.timer_inactividad = QTimer(self)
        self.timer_inactividad.setInterval(60000)
        self.timer_inactividad.timeout.connect(self.activar_modo_sueno)
        self.timer_inactividad.start()

        # Temporizador para detección de música vía MPRIS (cada 1.5s)
        self.music_timer = QTimer(self)
        self.music_timer.setInterval(1500)
        self.music_timer.timeout.connect(self.check_mpris_music)
        self.music_timer.start()

        self.comprobar_modo_noche()

    def _inicializar_chat(self):
        if not API_KEY or API_KEY == "TU_API_KEY_AQUI":
            self.chat = None
            return

        try:
            self.client = genai.Client(api_key=API_KEY)
            self.chat = self.client.chats.create(
                model="gemini-3.1-flash-lite",
                config={
                    "system_instruction": self.system_instruction,
                    "max_output_tokens": 300
                }
            )
        except Exception as e:
            print(f"[ERROR INICIALIZACIÓN API] {e}")
            self.chat = None

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.globo = GloboTexto(self)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedWidth(210)
        self.scroll_area.setMaximumHeight(200)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { border: none; background: transparent; width: 4px; margin: 2px 0px 2px 0px; }
            QScrollBar::handle:vertical { background: #585b70; min-height: 15px; border-radius: 2px; }
            QScrollBar::handle:vertical:hover { background: #89b4fa; }
        """)

        self.dialogo_label = QLabel("Saludos. ¿En qué le puedo asistir el día de hoy?", self)
        self.dialogo_label.setStyleSheet("""
            QLabel { background-color: transparent; color: #cdd6f4; font-size: 12px; font-weight: 500; }
        """)
        self.dialogo_label.setWordWrap(True)
        self.dialogo_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.scroll_area.setWidget(self.dialogo_label)

        globo_interno = QHBoxLayout()
        globo_interno.setContentsMargins(0, 0, 0, 0)
        globo_interno.addWidget(self.scroll_area)

        self.globo.layout().addLayout(globo_interno)

        self.avatar_label = QLabel(self)
        self.cambiar_estado("normal")

        self.input_text = QLineEdit(self)
        self.input_text.setFixedWidth(230)
        self.input_text.setPlaceholderText("Escriba un comando...")
        self.input_text.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 46, 0.95); color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 8px;
                padding: 5px 10px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #89b4fa; }
        """)
        self.input_text.returnPressed.connect(self.enviar_mensaje)

        layout.addWidget(self.globo, alignment=Qt.AlignCenter)
        layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.input_text, alignment=Qt.AlignCenter)
        self.setLayout(layout)

        self.move(100, 100)

    # --- CONSULTA MPRIS / PLAYERCTL ---
    def check_mpris_music(self):
        if self.timer_escritura.isActive():
            return

        try:
            cmd = ["playerctl", "metadata", "--format", "{{status}}::{{title}} - {{artist}}"]
            res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()

            if "::" in res:
                status, track_info = res.split("::", 1)
                if status.lower() == "playing":
                    clean_title = track_info.strip()
                    if not self.is_playing_music or self.current_song != clean_title:
                        self.is_playing_music = True
                        self.current_song = clean_title
                        self.bloqueo_look = False
                        self.cambiar_estado("feliz")
                        self.mostrar_texto_animado(f"♫ Reproduciendo: {self.current_song[:32]}...")
                    
                    self.timer_inactividad.start()
                    return
        except Exception:
            pass

        if self.is_playing_music:
            self.is_playing_music = False
            self.current_song = ""
            self.bloqueo_look = False
            self.cambiar_estado("normal")
            self.timer_inactividad.start()

    def ejecutar_cambio_de_look(self):
        self.indice_look_actual = (self.indice_look_actual + 1) % len(self.looks_alternativos)
        nueva_ruta = self.looks_alternativos[self.indice_look_actual]

        if not os.path.exists(nueva_ruta):
            return f"No se encontró la imagen en la ruta: {nueva_ruta}"

        pixmap = QPixmap(nueva_ruta)
        if not pixmap.isNull():
            self.bloqueo_look = True
            pixmap_escalado = pixmap.scaledToWidth(180, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pixmap_escalado)
            self.avatar_label.repaint()
            return "Apariencia actualizada correctamente."

        return "Ocurrió un error al cargar la nueva imagen."

    def cargar_atajos_custom(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ruta_json = os.path.join(BASE_DIR, "atajos.json")
        if not os.path.exists(ruta_json):
            ejemplo = {"modo estudio": "kitty", "abrir notas": "xed"}
            try:
                os.makedirs(os.path.dirname(ruta_json), exist_ok=True)
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(ejemplo, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                self.atajos_custom = json.load(f)
        except Exception:
            self.atajos_custom = {}

    def crear_recordatorio(self, minutos, mensaje):
        ms = int(minutos * 60 * 1000)

        def _notificar():
            texto_alerta = f"Recordatorio programado: {mensaje}"
            self.cambiar_estado("feliz")
            self.mostrar_texto_animado(texto_alerta)
            self.hablar_en_hilo(f"Recordatorio: {mensaje}.")

        QTimer.singleShot(ms, _notificar)
        return f"Recordatorio establecido. Te notificaré en {minutos} minutos sobre '{mensaje}'."

    def cambiar_estado(self, estado):
        if self.bloqueo_look:
            return

        ruta = self.rutas_imagenes.get(estado, self.rutas_imagenes["normal"])
        if os.path.exists(ruta):
            pixmap = QPixmap(ruta)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(180, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(pixmap)
                return
        self.avatar_label.setText(f"[{estado.capitalize()}]")

    def activar_modo_sueno(self):
        if self.is_playing_music or self.is_talking or self.timer_escritura.isActive():
            self.timer_inactividad.start()
            return

        self.bloqueo_look = False
        self.cambiar_estado("durmiendo")
        self.bloqueo_look = True
        self.mostrar_texto_animado("Sistema en modo de reposo por inactividad.")

    def mostrar_texto_animado(self, texto):
        self.timer_escritura.stop()
        self.texto_completo_animacion = texto
        self.indice_caracter_animacion = 0
        self.dialogo_label.setText("")
        self.timer_escritura.start()

    def _paso_maquina_escribir(self):
        if self.indice_caracter_animacion <= len(self.texto_completo_animacion):
            texto_parcial = self.texto_completo_animacion[:self.indice_caracter_animacion]
            self.dialogo_label.setText(texto_parcial)
            self.dialogo_label.repaint()
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())
            self.indice_caracter_animacion += 1
        else:
            self.timer_escritura.stop()

    def comprobar_modo_noche(self):
        hora_actual = time.localtime().tm_hour
        if hora_actual >= 22 or hora_actual < 6:
            self.cambiar_estado("durmiendo")
            self.mostrar_texto_animado("Horario nocturno detectado. El asistente se encuentra en modo reposo.")

    def hablar_en_hilo(self, texto):
        def _hablar():
            self.is_talking = True
            try:
                import asyncio
                import edge_tts
                import pygame

                VOZ = "es-MX-DaliaNeural"

                async def _generar_audio():
                    communicate = edge_tts.Communicate(texto, VOZ, rate="+0%", pitch="+0Hz")
                    await communicate.save("/tmp/mascota_voz.mp3")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_generar_audio())
                loop.close()

                if os.path.exists("/tmp/mascota_voz.mp3"):
                    pygame.mixer.init()
                    pygame.mixer.music.load("/tmp/mascota_voz.mp3")
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    pygame.mixer.quit()
            except Exception as e:
                print(f"Error en síntesis de voz: {e}")
            finally:
                self.is_talking = False

        threading.Thread(target=_hablar, daemon=True).start()

    # --- EVENTOS DE RATÓN (REQUISITO: SHIFT + CLIC IZQUIERDO PARA MOVER) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            self.arrastrando = True
            self.oldPos = event.globalPos()
        else:
            self.arrastrando = False

    def mouseMoveEvent(self, event):
        if self.arrastrando and (event.buttons() & Qt.LeftButton):
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.arrastrando = False

    def _gestionar_procesos(self, cmd):
        claves_ram = [
            "que consume tanta ram",
            "dime el consumo de recursos",
            "procesos pesados",
            "top ram",
            "quien consume ram"
        ]
        
        if any(k in cmd for k in claves_ram):
            self.cambiar_estado("pensando")
            procesos = []
            for p in psutil.process_iter(['name', 'memory_percent']):
                try:
                    procesos.append((p.info['name'], p.info['memory_percent']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procesos = sorted(procesos, key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join([f"{n} ({m:.1f}%)" for n, m in procesos])
            return f"Los 3 procesos con mayor consumo de RAM son: {top_str}."

        elif cmd.startswith("cierra ") or cmd.startswith("mata ") or cmd.startswith("matar "):
            self.cambiar_estado("feliz")
            objetivo = cmd.replace("cierra", "").replace("matar", "").replace("mata", "").strip()
            cerrados = 0
            for p in psutil.process_iter(['name']):
                try:
                    if objetivo in p.info['name'].lower():
                        p.terminate()
                        cerrados += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if cerrados > 0:
                return f"Se cerraron {cerrados} proceso(s) coincidentes con '{objetivo}'."
            return f"No se encontró ningún proceso activo que coincida con '{objetivo}'."

        return None

    def _gestionar_pendientes(self, cmd):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ruta_json = os.path.join(BASE_DIR, "pendientes.json")

        pendientes = []
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    pendientes = json.load(f)
            except Exception:
                pendientes = []

        if "anota" in cmd or "agregar pendiente:" in cmd:
            self.cambiar_estado("feliz")
            tarea = cmd.split(":", 1)[1].strip()
            if tarea:
                pendientes.append(tarea)
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(pendientes, f, indent=4, ensure_ascii=False)
                return f"Tarea registrada: '{tarea}'."

        elif any(k in cmd for k in ["mis pendientes", "que tengo pendiente", "ver pendientes"]):
            self.cambiar_estado("feliz")
            if not pendientes:
                return "No tiene tareas pendientes registradas en este momento."
            lista = "\n• " + "\n• ".join(pendientes)
            return f"Tareas pendientes actuales:{lista}"

        elif any(k in cmd for k in ["limpiar pendientes", "borrar pendientes", "vaciar pendientes"]):
            self.cambiar_estado("feliz")
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump([], f)
            return "Se han eliminado todas las tareas pendientes."

        return None    

    def procesar_comando_sistema(self, prompt):
        cmd = prompt.lower().strip()

        # Revisar Procesos y RAM
        res_proceso = self._gestionar_procesos(cmd)
        if res_proceso:
            return res_proceso

        # Revisar Pendientes
        res_pendiente = self._gestionar_pendientes(cmd)
        if res_pendiente:
            return res_pendiente
        
        # Comandos para fijar / desbloquear posición
        if any(k in cmd for k in ["fijar", "bloquear posicion", "no te muevas", "quedate ahi"]):
            self.posicion_fijada = True
            return "Posición fijada. Utilice 'desbloquear' para mover la ventana de nuevo."

        elif any(k in cmd for k in ["desbloquear", "desfijar", "muevete", "muévete", "desbloquear posicion"]):
            self.posicion_fijada = False
            return "Posición desbloqueada. Puede arrastrar la ventana libremente."

        # Comandos de ejecución directa de aplicaciones
        if "abre la terminal" in cmd or "abrir terminal" in cmd:
            self.cambiar_estado("feliz") 
            subprocess.Popen(["kitty"])
            return "Ejecutando la aplicación de terminal..."

        elif "abre el navegador" in cmd or "abrir navegador" in cmd:
            self.cambiar_estado("feliz") 
            subprocess.Popen(["xdg-open", "https://google.com"])
            return "Abriendo el navegador web..."

        for alias, ejecutable in self.atajos_custom.items():
            if alias in cmd:
                try:
                    self.cambiar_estado("feliz")
                    subprocess.Popen(ejecutable.split())
                    return f"Iniciando la aplicación: {alias}."
                except Exception as e:
                    self.cambiar_estado("triste")
                    return f"No se pudo iniciar '{alias}': {e}"

        # Conversaciones normales / Saludos
        saludos = ["holis", "olis", "hola", "buenas", "que tal", "qué tal", "konnichiwa", "ohayo", "buenos dias", "buenas tardes", "buenas noches"]
        if any(cmd == s for s in saludos) or any(cmd.startswith(s + " ") for s in saludos):
            self.cambiar_estado("feliz")
            return random.choice([
                "Saludos. ¿En qué le puedo asistir el día de hoy?",
                "Hola. Estoy a su disposición para colaborar en sus tareas.",
                "Buenos días. ¿Qué comando requiere ejecutar?"
            ])

        estado_preguntas = ["como estas", "cómo estás", "como te sientes", "cómo te sientes", "que tal estas"]
        if any(k in cmd for k in estado_preguntas):
            self.cambiar_estado("feliz") 
            return "El sistema se encuentra funcionando al 100% de su capacidad. ¿En qué puedo ayudarle?"

        agradecimientos = ["gracias", "muchas gracias", "arigato", "arigatou", "te lo agradezco"]
        if any(k in cmd for k in agradecimientos):
            self.cambiar_estado("feliz")
            return "Es un placer asistirle. Quedo a la espera de sus instrucciones."

        despedidas = ["chao", "adios", "adiós", "hasta luego", "nos vemos", "sayonara, bye"]
        if any(cmd == d for d in despedidas):
            self.cambiar_estado("durmiendo")
            return "Hasta luego. Que tenga una excelente jornada."

        if any(k in cmd for k in ["linda", "bonita", "tierna", "buena asistente", "kawaii", "te quiero"]):
            self.cambiar_estado("sonrojada")
            return "Agradezco sus comentarios. Trabajaré para seguir brindando un servicio óptimo."

        if "cambio de look" in cmd or "cambia de ropa" in cmd or "cambiar de look" in cmd:
            return self.ejecutar_cambio_de_look()

        elif any(k in cmd for k in ["captura de pantalla", "toma una captura", "haz una captura", "screenshot"]):
            self.cambiar_estado("feliz")
            ruta_img = os.path.expanduser("~/Imágenes")
            os.makedirs(ruta_img, exist_ok=True)
            nombre_archivo = time.strftime("captura_%Y%m%d_%H%M%S.png")
            destino = os.path.join(ruta_img, nombre_archivo)
            
            screen = QApplication.primaryScreen()
            if screen:
                captura = screen.grabWindow(0)
                captura.save(destino, "PNG")
                return "Captura de pantalla guardada exitosamente en la carpeta Imágenes."
            else:
                return "No se pudo obtener acceso a la pantalla para realizar la captura."

        elif "recuerdame en" in cmd or "recuérdame en" in cmd:
            self.cambiar_estado("feliz")
            try:
                clave = "recuerdame en" if "recuerdame en" in cmd else "recuérdame en"
                partes = cmd.split(clave)[1].strip()
                if "minuto" in partes:
                    tiempo_str, mensaje = partes.split("minuto", 1)
                    if mensaje.startswith("s"):
                        mensaje = mensaje[1:]
                    return self.crear_recordatorio(float(tiempo_str.strip()), mensaje.strip() or "su asunto pendiente")
            except Exception:
                self.cambiar_estado("triste")
                return "Sintaxis no reconocida. Por ejemplo, escriba: 'recuérdame en 5 minutos estudiar'."

        elif "estado del sistema" in cmd or "cómo está el sistema" in cmd or "uso de ram" in cmd:
            self.cambiar_estado("pensando")
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            return f"Uso actual del procesador: {cpu}% | Uso de memoria RAM: {ram.percent}%."

        elif "que hora es" in cmd or "qué hora es" in cmd:
            self.cambiar_estado("feliz")
            return f"La hora actual es: {time.strftime('%I:%M %p')}."

        elif "que fecha es" in cmd or "qué fecha es" in cmd:
            self.cambiar_estado("feliz")
            return f"La fecha de hoy es: {time.strftime('%A, %d de %B del %Y')}."

        return None

    def enviar_mensaje(self):
        prompt = self.input_text.text().strip()
        if not prompt:
            return

        self.bloqueo_look = False
        self.cambiar_estado("feliz")
        self.timer_inactividad.start()
        self.input_text.clear()

        # 1. Filtro local
        respuesta_local = self.procesar_comando_sistema(prompt)
        if respuesta_local:
            print(f"[LOCAL] Comando procesado: '{prompt}'")
            self.mostrar_texto_animado(respuesta_local)
            self.hablar_en_hilo(respuesta_local)
            return

        # 2. Envío a la API
        print(f"[API GEMINI] Consultando: '{prompt}'")
        self.cambiar_estado("pensando")
        self.input_text.setEnabled(False)
        self.mostrar_texto_animado("Procesando consulta...")

        try:
            if not self.chat:
                raise Exception("La API Key no está configurada o es inválida.")

            response = self.chat.send_message(prompt)
            texto_respuesta = response.text

            print("[API GEMINI] Respuesta recibida correctamente.")
            self.cambiar_estado("feliz")
            self.mostrar_texto_animado(texto_respuesta)
            self.hablar_en_hilo(texto_respuesta)

        except Exception as e:
            print(f"[ERROR API] {e}")
            self.cambiar_estado("normal")
            self.mostrar_texto_animado("Ocurrió un error al establecer comunicación con el servicio de IA.")

        finally:
            self.input_text.setEnabled(True)
            self.input_text.setFocus()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mascota = MascotaDesktop()
    mascota.show()
    sys.exit(app.exec_())
