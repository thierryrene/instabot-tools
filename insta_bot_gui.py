#!/usr/bin/env python3
import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox, QProgressBar, QSpinBox, 
                             QDoubleSpinBox, QTabWidget, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor

import os
import time
import random
import xml.etree.ElementTree as ET
import subprocess
from datetime import timedelta

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from database_manager import DatabaseManager
from insights_engine import InsightsEngine
from exporter import DataExporter
from price_tracker import PriceTracker
from text_analyzer import TextAnalyzer
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class BotWorker(QThread):
    """Thread para executar o bot sem travar a GUI"""
    log_signal = pyqtSignal(str, str)  # mensagem, tipo (info/success/warning/error)
    progress_signal = pyqtSignal(dict)  # dados completos em tempo real
    finished_signal = pyqtSignal(dict)  # relatório final
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.db = DatabaseManager()
        self.price_tracker = PriceTracker()
        
    def run_adb_cmd(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except:
            return ""
    
    def tap(self, x, y, randomize=True, duration=None):
        if randomize:
            x += random.randint(-5, 5)
            y += random.randint(-5, 5)
        
        # Se duration não for passado, tenta pegar da config, se não, padrão 0
        if duration is None:
            duration = self.config.get('click_duration', 0)

        if duration > 0:
            # Swipe no mesmo lugar simula um click longo (pressão)
            os.system(f"adb shell input swipe {x} {y} {x} {y} {duration}")
        else:
            os.system(f"adb shell input tap {x} {y}")
    
    def swipe(self, x1, y1, x2, y2, duration=300):
        os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} {duration}")
    
    def like_current_story(self):
        try:
            os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
            xml_content = self.run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
            
            if not xml_content:
                raise Exception("XML vazio")
                
            root = ET.fromstring(xml_content)
            found = False
            for node in root.iter():
                desc = node.attrib.get('content-desc', '')
                res_id = node.attrib.get('resource-id', '')
                if 'toolbar_like_button' in res_id or 'Curtir' in desc:
                    bounds = node.attrib.get('bounds', '')
                    import re
                    matches = re.findall(r'\d+', bounds)
                    if len(matches) == 4:
                        cx = (int(matches[0]) + int(matches[2])) // 2
                        cy = (int(matches[1]) + int(matches[3])) // 2
                        self.tap(cx, cy, randomize=True)
                        found = True
                        break
            if not found: 
                self.tap(self.config['heart_x'], self.config['heart_y'], randomize=True)
        except Exception as e:
            self.log_signal.emit(f"Erro ao dar like: {e}", "warning")
            self.tap(self.config['heart_x'], self.config['heart_y'], randomize=True)
        time.sleep(0.5)
    
    def get_screen_details(self):
        try:
            os.system("adb shell uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1")
            xml_content = self.run_adb_cmd("adb shell cat /data/local/tmp/uidump.xml")
            
            if not xml_content or 'resource-id="com.instagram.android:id/tab_bar"' in xml_content or 'content-desc="Início"' in xml_content:
                 return {"screen_type": "feed", "username": None, "is_ad": False, "is_live": False, "full_text": ""}

            root = ET.fromstring(xml_content)
            found_username = "Desconhecido"
            is_sponsored = False
            is_live = False
            all_text_content = []

            ad_keywords = ["patrocinado", "sponsored", "publicidade", "saiba mais", "install now", "instalar agora", "sign up", "cadastre-se", "comprar agora", "shop now", "watch more", "assistir mais"]
            live_keywords = ["ao vivo", "live", "transmissão ao vivo"]

            for node in root.iter():
                text = node.attrib.get('text', '').lower()
                desc = node.attrib.get('content-desc', '').lower()
                res_id = node.attrib.get('resource-id', '')
                
                content_to_check = f"{text} {desc}"

                if any(kw in content_to_check for kw in ad_keywords):
                    is_sponsored = True
                
                if any(kw in content_to_check for kw in live_keywords):
                    if "espectadores" in content_to_check or text == "ao vivo" or text == "live":
                        is_live = True

                if 'reel_viewer_title' in res_id or 'row_feed_photo_profile_name' in res_id:
                    original_text = node.attrib.get('text', '')
                    if original_text: found_username = original_text
                
                if len(text) >= 3:
                     all_text_content.append(text)
            
            # 2.2 OCR VISUAL (ROADMAP v1.3.0)
            ocr_text = ""
            if OCR_AVAILABLE:
                try:
                    screenshot_path = "ocr_temp.png"
                    self.run_adb_cmd(f"adb shell screencap -p /sdcard/{screenshot_path}")
                    self.run_adb_cmd(f"adb pull /sdcard/{screenshot_path} {screenshot_path}")
                    
                    if os.path.exists(screenshot_path):
                        img = Image.open(screenshot_path)
                        img = img.convert('L') # Greyscale for better OCR
                        ocr_text = pytesseract.image_to_string(img, lang='por+eng')
                        os.remove(screenshot_path)
                        self.run_adb_cmd(f"adb shell rm /sdcard/{screenshot_path}")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ Erro no OCR: {str(e)[:50]}...", "warning")

            full_text = " || ".join(all_text_content)
            if ocr_text.strip():
                full_text += " || [OCR]: " + ocr_text.strip().replace("\n", " ")

            return {
                "screen_type": "story",
                "username": found_username,
                "is_ad": is_sponsored,
                "is_live": is_live,
                "full_text": full_text
            }
        except Exception:
            return {"screen_type": "story", "username": "Desconhecido", "is_ad": False, "is_live": False, "full_text": ""}
    
    def wake_and_unlock(self):
        dump = self.run_adb_cmd("adb shell dumpsys window | grep mWakefulness")
        if "Awake" not in dump:
            os.system("adb shell input keyevent KEYCODE_WAKEUP")
            time.sleep(1)
            self.swipe(500, 2000, 500, 500)
        os.system("adb shell input keyevent 82")
    
    def start_instagram(self):
        self.log_signal.emit("🚀 Iniciando Instagram...", "info")
        self.wake_and_unlock()
        os.system(f"adb shell am force-stop {self.config['package']}")
        os.system(f"adb shell monkey -p {self.config['package']} -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1")
        time.sleep(6)
        self.log_signal.emit("✅ Instagram aberto", "success")
    
    def run(self):
        analyzer = TextAnalyzer() # Analisador de Texto
        total_stories = 0
        total_ads = 0
        liked_count = 0
        profile_map = {}
        last_user = None
        real_stories = 0
        session_start = time.time()

        try:
            self.start_instagram()
            self.tap(self.config['story_x'], self.config['story_y'], randomize=False)
            time.sleep(2)
            
            self.log_signal.emit(f"⚡ Bot ativo | Alvo: @{self.config['target_profile']}", "info")
            
            # Inicia Sessão no DB
            self.db.start_session(self.config['target_profile'])
            
            while self.running:
                # MODO TURBO: Pula verificação de tela para velocidade máxima
                if self.config.get('turbo_mode', False):
                    screen_type = "story"
                    username = "TurboMode"
                    is_ad = False
                    is_live = False
                    full_text = ""
                else:
                    details = self.get_screen_details()
                    screen_type = details['screen_type']
                    username = details['username']
                    is_ad = details['is_ad']
                    is_live = details['is_live']
                    full_text = details['full_text']
                
                if screen_type == "feed":
                    self.log_signal.emit("✅ Fim da fila de stories", "success")
                    break
                
                total_stories += 1
                
                display_name = username
                emoji = "✨"
                
                if is_live:
                    # Trata Live como algo a pular rápido ou logar diferente
                    display_name = f"{username} (LIVE 🔴)"
                    self.log_signal.emit(f"🔴 LIVE detectada: @{username}", "warning")
                    # Lives não contam como ads nas stats, mas queremos saber
                elif is_ad:
                    total_ads += 1
                    display_name = f"{username} (Ad)"
                    emoji = "💸"
                    self.log_signal.emit(f"{emoji} @{display_name}", "warning")
                
                # 2.3 RASTREADOR DE PREÇOS (v1.5.0)
                if not is_ad and full_text:
                    price_pattern = r'(?:R\$|US\$|€)\s?(\d+(?:[\.,]\d+)?)'
                    pm = re.search(price_pattern, full_text, re.IGNORECASE)
                    if pm:
                        try:
                            price_val = float(pm.group(1).replace(',', '.'))
                            currency = "R$" if "R$" in pm.group(0) else "$" # Simplificado
                            item_id = f"{username}_spotted" # Melhoraria com detecção de produto
                            variation = self.price_tracker.update_price(item_id, price_val, currency, username)
                            if variation:
                                self.log_signal.emit(f"💰 VARIÇÃO DE PREÇO em @{username}: {variation} ({currency}{price_val})", "info")
                        except: pass
                
                # Log movido para o final do loop para pegar duração
                if username != "Desconhecido" and username != "TurboMode":
                    profile_map[username] = profile_map.get(username, 0) + 1
                
                # Só loga cada usuário novo se não estiver no modo turbo
                if username != last_user and not self.config.get('turbo_mode', False):
                    self.log_signal.emit(f"{emoji} @{display_name}", "info")
                    last_user = username
                
                # Log movido para o final do loop para pegar duração
                
                # Atualiza progresso com dados completos
                # liked_count_start é usado para determinar se houve like no ciclo atual para o log correto
                liked_count_start = liked_count
                
                # Like VIP (Ignora se for Ad, Live ou Turbo Mode)
                if not self.config.get('turbo_mode', False) and not is_ad and not is_live:
                    if username.lower() == self.config['target_profile'].lower():
                        self.like_current_story()
                        liked_count += 1
                        self.log_signal.emit(f"   💖 LIKE em story de @{username}", "success")
                        # Log movido para o final do loop
                
                # Atualiza progresso com dados completos
                elapsed = time.time() - session_start
                real_stories = total_stories - total_ads
                speed = (total_stories / (elapsed / 60)) if elapsed > 0 else 0
                ad_percentage = (total_ads / total_stories * 100) if total_stories > 0 else 0
                
                progress_data = {
                    'total_stories': total_stories,
                    'total_ads': total_ads,
                    'real_stories': real_stories,
                    'liked_count': liked_count,
                    'unique_profiles': len(profile_map),
                    'profile_map': dict(profile_map),
                    'elapsed_time': elapsed,
                    'speed': speed,
                    'ad_percentage': ad_percentage
                }
                self.progress_signal.emit(progress_data)
                
                # Rate limiting
                if total_stories % 50 == 0:
                    pause_time = random.uniform(10, 30)
                    self.log_signal.emit(f"⏸️ Pausa estratégica ({pause_time:.1f}s)", "info")
                    time.sleep(pause_time)
                
                # Timing humanizado configurável
                min_delay = self.config.get('min_delay', 0.8)
                max_delay = self.config.get('max_delay', 2.5)
                view_time = random.uniform(min_delay, max_delay)
                
                # Garante que não seja negativo
                if view_time < 0.1: view_time = 0.1
                
                time.sleep(view_time)
                
                # LOGA AGORA QUE SABEMOS O TEMPO DE VISUALIZAÇÃO
                # O log foi movido para cá para capturar o `view_time` real
                
                # Determina ação
                action = "view"
                if liked_count_start < liked_count: action = "like" # Simplificação: se like count mudou no loop, foi like
                
                story_id = self.db.log_story(username, is_ad=is_ad, is_live=is_live, action_taken=action, full_text=full_text, view_duration=view_time)
                
                # PERSISTÊNCIA DE ENTIDADES (v1.6.0)
                if story_id and full_text:
                    analysis = analyzer.analyze(full_text)
                    self.db.save_entities(story_id, analysis['entities'])

                self.tap(self.config['next_x'], self.config['next_y'])
                time.sleep(0.5)
            
            # Relatório final
            duration = time.time() - session_start
            real_stories = total_stories - total_ads
            report = {
                'total_stories': total_stories,
                'total_ads': total_ads,
                'liked_count': liked_count,
                'profile_map': profile_map,
                'duration': duration,
                'real_stories': real_stories
            }
            self.finished_signal.emit(report)
            
        except Exception as e:
            self.log_signal.emit(f"⚠️ Erro: {e}", "error")
            self.finished_signal.emit({})
        finally:
            self.db.end_session(total_stories, total_ads, liked_count, len(profile_map), time.time() - session_start)
    
    def stop(self):
        self.running = False


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#1a1a2e')
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#0f0f1e')
        super(MplCanvas, self).__init__(self.fig)


class InstaBotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.current_data = {}
        self.insights = InsightsEngine() # Motor de análise
        self.exporter = DataExporter()   # Exportador de relatórios
        self.price_tracker = PriceTracker() # Rastreador de preços
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Instagram Stories Bot - Professional Edition")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1e, stop:1 #1a1a2e);
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #6c5ce7;
                border-radius: 10px;
                margin-top: 15px;
                font-weight: bold;
                font-size: 13px;
                padding-top: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(108, 92, 231, 0.1), stop:1 rgba(0, 0, 0, 0.2));
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #a29bfe;
            }
            QLabel {
                color: #dfe6e9;
                font-size: 12px;
            }
            QLineEdit, QSpinBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3436, stop:1 #1e272e);
                color: #ffffff;
                border: 2px solid #636e72;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                selection-background-color: #6c5ce7;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid #6c5ce7;
                background: #2d3436;
            }
            QLineEdit:hover, QSpinBox:hover {
                border: 2px solid #a29bfe;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c5ce7, stop:1 #a29bfe);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 13px;
                text-transform: uppercase;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5f4dd1, stop:1 #8b7fe8);
                padding: 12px 22px;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a3cb3, stop:1 #7467d4);
            }
            QPushButton:disabled {
                background: #2d3436;
                color: #636e72;
            }
            QTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0a0a, stop:1 #1a1a1a);
                color: #00ff88;
                border: 2px solid #636e72;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                padding: 8px;
            }
            QProgressBar {
                border: 2px solid #636e72;
                border-radius: 8px;
                text-align: center;
                color: #ffffff;
                background: #1e272e;
                height: 25px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00b894, stop:0.5 #00cec9, stop:1 #0984e3);
                border-radius: 6px;
            }
            QTabWidget::pane {
                border: 2px solid #6c5ce7;
                border-radius: 8px;
                background: rgba(0, 0, 0, 0.3);
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3436, stop:1 #1e272e);
                color: #b2bec3;
                padding: 10px 20px;
                border: 2px solid #636e72;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c5ce7, stop:1 #5f4dd1);
                color: #ffffff;
                border-color: #6c5ce7;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d3d5c, stop:1 #2d2d4a);
                color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #6c5ce7;
                border-radius: 3px;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #a29bfe;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Layout esquerdo (controles)
        left_layout = QVBoxLayout()
        
        # Layout direito (monitoramento)
        right_layout = QVBoxLayout()
        
        # === CONFIGURAÇÕES ===
        config_group = QGroupBox("⚙️ Configurações")
        config_layout = QVBoxLayout()
        
        # Perfil VIP
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Perfil VIP:"))
        self.target_profile_input = QLineEdit("stealthelook")
        profile_layout.addWidget(self.target_profile_input)
        config_layout.addLayout(profile_layout)
        
        # Coordenadas Story
        story_coords_layout = QHBoxLayout()
        story_coords_layout.addWidget(QLabel("Story X:"))
        self.story_x_input = QSpinBox()
        self.story_x_input.setRange(0, 2000)
        self.story_x_input.setValue(745)
        story_coords_layout.addWidget(self.story_x_input)
        story_coords_layout.addWidget(QLabel("Y:"))
        self.story_y_input = QSpinBox()
        self.story_y_input.setRange(0, 3000)
        self.story_y_input.setValue(400)
        story_coords_layout.addWidget(self.story_y_input)
        config_layout.addLayout(story_coords_layout)
        
        # Coordenadas Next
        next_coords_layout = QHBoxLayout()
        next_coords_layout.addWidget(QLabel("Next X:"))
        self.next_x_input = QSpinBox()
        self.next_x_input.setRange(0, 2000)
        self.next_x_input.setValue(980)
        next_coords_layout.addWidget(self.next_x_input)
        next_coords_layout.addWidget(QLabel("Y:"))
        self.next_y_input = QSpinBox()
        self.next_y_input.setRange(0, 3000)
        self.next_y_input.setValue(1000)
        next_coords_layout.addWidget(self.next_y_input)
        config_layout.addLayout(next_coords_layout)
        
        # Coordenadas Heart
        heart_coords_layout = QHBoxLayout()
        heart_coords_layout.addWidget(QLabel("Heart X:"))
        self.heart_x_input = QSpinBox()
        self.heart_x_input.setRange(0, 2000)
        self.heart_x_input.setValue(950)
        heart_coords_layout.addWidget(self.heart_x_input)
        heart_coords_layout.addWidget(QLabel("Y:"))
        self.heart_y_input = QSpinBox()
        self.heart_y_input.setRange(0, 3000)
        self.heart_y_input.setValue(2150)
        heart_coords_layout.addWidget(self.heart_y_input)
        config_layout.addLayout(heart_coords_layout)

        # Tempo de Visualização (Configurável em tempo real)
        # ÁREA DE ALERTAS (ROADMAP v1.5.0)
        self.alert_banner = QLabel("🚀 Monitorando picos virais e tendências...")
        self.alert_banner.setStyleSheet("background: #3d3d5c; color: #a29bfe; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.alert_banner.hide()
        right_layout.addWidget(self.alert_banner)

        # Tab Widget para Gráficos
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Tempo (s): Min"))
        self.min_time_input = QDoubleSpinBox()
        self.min_time_input.setRange(0.1, 60.0)
        self.min_time_input.setSingleStep(0.1)
        self.min_time_input.setValue(0.8)
        self.min_time_input.valueChanged.connect(self.update_realtime_config)
        time_layout.addWidget(self.min_time_input)
        
        time_layout.addWidget(QLabel("Máx"))
        self.max_time_input = QDoubleSpinBox()
        self.max_time_input.setRange(0.1, 60.0)
        self.max_time_input.setSingleStep(0.1)
        self.max_time_input.setValue(2.5)
        self.max_time_input.valueChanged.connect(self.update_realtime_config)
        time_layout.addWidget(self.max_time_input)
        config_layout.addLayout(time_layout)

        # Duração do Toque (Click Duration)
        click_duration_layout = QHBoxLayout()
        click_duration_layout.addWidget(QLabel("Duração do Click (ms):"))
        self.click_duration_input = QSpinBox()
        self.click_duration_input.setRange(0, 5000) # 0 a 5 segundos
        self.click_duration_input.setValue(50) # Padrão rápido
        self.click_duration_input.setSingleStep(10)
        self.click_duration_input.valueChanged.connect(self.update_realtime_config)
        click_duration_layout.addWidget(self.click_duration_input)
        config_layout.addLayout(click_duration_layout)

        # Modo Turbo (Ignorar verificação para velocidade)
        self.turbo_mode_check = QCheckBox("🚀 MODO TURBO (Ignorar Anúncios = +Velocidade)")
        self.turbo_mode_check.setStyleSheet("QCheckBox { color: #00ff88; font-weight: bold; }")
        self.turbo_mode_check.setToolTip("Se marcado, não verifica a tela (não detecta anúncios/nomes), mas é MUITO mais rápido.")
        self.turbo_mode_check.stateChanged.connect(self.update_realtime_config)
        config_layout.addWidget(self.turbo_mode_check)
        
        config_group.setLayout(config_layout)
        left_layout.addWidget(config_group, 0)  # Não cresce
        
        # === CONTROLES ===
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ INICIAR BOT")
        self.start_btn.clicked.connect(self.start_bot)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ PARAR")
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(control_layout)
        
        # === ESTATÍSTICAS ===
        stats_group = QGroupBox("📊 Estatísticas em Tempo Real")
        stats_layout = QHBoxLayout()
        
        # Cards de estatísticas com estilo moderno
        self.stories_label = QLabel("Stories\n0")
        self.stories_label.setAlignment(Qt.AlignCenter)
        self.stories_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.stories_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0984e3, stop:1 #74b9ff);
                border-radius: 10px;
                padding: 15px;
                color: white;
            }
        """)
        stats_layout.addWidget(self.stories_label)
        
        self.ads_label = QLabel("Anúncios\n0")
        self.ads_label.setAlignment(Qt.AlignCenter)
        self.ads_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.ads_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d63031, stop:1 #ff7675);
                border-radius: 10px;
                padding: 15px;
                color: white;
            }
        """)
        stats_layout.addWidget(self.ads_label)
        
        self.likes_label = QLabel("Likes\n0")
        self.likes_label.setAlignment(Qt.AlignCenter)
        self.likes_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.likes_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e84393, stop:1 #fd79a8);
                border-radius: 10px;
                padding: 15px;
                color: white;
            }
        """)
        stats_layout.addWidget(self.likes_label)
        
        self.profiles_label = QLabel("Perfis\n0")
        self.profiles_label.setAlignment(Qt.AlignCenter)
        self.profiles_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.profiles_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00b894, stop:1 #55efc4);
                border-radius: 10px;
                padding: 15px;
                color: white;
            }
        """)
        stats_layout.addWidget(self.profiles_label)
        
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group, 0)  # Não cresce
        
        # === BARRA DE PROGRESSO ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)  # Indeterminado
        left_layout.addWidget(self.progress_bar, 0)  # Não cresce
        
        # === LOG ===
        log_group = QGroupBox("📝 Log de Atividade")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        left_layout.addWidget(log_group, 1)  # Stretch factor para crescer
        
        # === PAINEL DIREITO - MONITORAMENTO ===
        
        # Monitor em tempo real (estilo output)
        monitor_group = QGroupBox("⚡ Monitor em Tempo Real")
        monitor_layout = QVBoxLayout()
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setFont(QFont("Courier New", 11, QFont.Bold))
        self.monitor_text.setMinimumHeight(200)
        self.monitor_text.setStyleSheet("""
            QTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #1a1a1a);
                color: #00ff88;
                border: 2px solid #6c5ce7;
                border-radius: 10px;
                padding: 12px;
                font-family: 'Courier New', 'Monaco', monospace;
            }
        """)
        monitor_layout.addWidget(self.monitor_text)
        monitor_group.setLayout(monitor_layout)
        right_layout.addWidget(monitor_group, 1)  # Stretch 1 = divide espaço igualmente com gráficos
        
        # Tabs para gráficos
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #6c5ce7;
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(108, 92, 231, 0.05), stop:1 rgba(0, 0, 0, 0.3));
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3436, stop:1 #1e272e);
                color: #b2bec3;
                padding: 10px 20px;
                border: 2px solid #636e72;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 3px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c5ce7, stop:1 #5f4dd1);
                color: #ffffff;
                border-color: #6c5ce7;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d3d5c, stop:1 #2d2d4a);
                color: #ffffff;
            }
        """)
        
        # Tab 1: Ads vs Conteúdo
        self.canvas_ads = MplCanvas(self, width=6, height=4, dpi=100)
        self.tabs.addTab(self.canvas_ads, "📊 Ads vs Conteúdo")
        
        # Tab 2: Top Flooders
        self.canvas_flooders = MplCanvas(self, width=6, height=4, dpi=100)
        self.tabs.addTab(self.canvas_flooders, "🏆 Top Flooders")
        
        # Tab 3: Métricas de Performance
        self.canvas_metrics = MplCanvas(self, width=6, height=4, dpi=100)
        self.tabs.addTab(self.canvas_metrics, "⚡ Performance")
        
        # Tab 4: 🧠 Live Dashboard (Novo!)
        self.live_dashboard_widget = QWidget()
        self.init_live_dashboard(self.live_dashboard_widget)
        self.tabs.addTab(self.live_dashboard_widget, "🧠 Live Intelligence")
        
        # Tab 5: 🔬 Deep Analysis
        self.deep_analysis_widget = QWidget()
        self.init_deep_analysis(self.deep_analysis_widget)
        self.tabs.addTab(self.deep_analysis_widget, "🔬 Deep Analysis")

        # Tab 6: 🤼 Benchmarking 
        self.bench_widget = QWidget()
        self.init_benchmarking(self.bench_widget)
        self.tabs.addTab(self.bench_widget, "🤼 Benchmarking")
        
        right_layout.addWidget(self.tabs, 1)  # Stretch factor para os gráficos crescerem
        
        # Adiciona layouts ao main
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        # Timer para atualização do Dashboard (a cada 5s)
        self.dashboard_timer = QTimer()
        self.dashboard_timer.timeout.connect(self.update_live_dashboard)
        self.dashboard_timer.timeout.connect(self.update_deep_analysis)
        self.dashboard_timer.timeout.connect(self.update_benchmarking)
        self.dashboard_timer.timeout.connect(self.check_viral_alerts)
        self.dashboard_timer.start(5000)

        self.log("✨ Instagram Stories Bot iniciado", "info")
        self.log("Configure as coordenadas e clique em INICIAR BOT", "info")
        self.update_monitor_display()
    
    def init_live_dashboard(self, parent):
        layout = QVBoxLayout(parent)
        
        # KPI ROW
        kpi_layout = QHBoxLayout()
        
        self.kpi_trend = QLabel("Trend Ads (1h)\n--%")
        self.kpi_trend.setStyleSheet("background: #2d3436; color: white; padding: 10px; border-radius: 8px; font-weight: bold; border: 1px solid #636e72;")
        self.kpi_trend.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.kpi_trend)
        
        self.kpi_savings = QLabel("Economia Est.\n--s")
        self.kpi_savings.setStyleSheet("background: #2d3436; color: #00ff88; padding: 10px; border-radius: 8px; font-weight: bold; border: 1px solid #636e72;")
        self.kpi_savings.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.kpi_savings)

        self.kpi_prices = QLabel("Preços Det.\n0")
        self.kpi_prices.setStyleSheet("background: #2d3436; color: #f1c40f; padding: 10px; border-radius: 8px; font-weight: bold; border: 1px solid #636e72;")
        self.kpi_prices.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.kpi_prices)

        self.kpi_links = QLabel("Links/CTAs\n0")
        self.kpi_links.setStyleSheet("background: #2d3436; color: #3498db; padding: 10px; border-radius: 8px; font-weight: bold; border: 1px solid #636e72;")
        self.kpi_links.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.kpi_links)

        self.kpi_sentiment = QLabel("Sentimento\n--")
        self.kpi_sentiment.setStyleSheet("background: #2d3436; color: white; padding: 10px; border-radius: 8px; font-weight: bold; border: 1px solid #636e72;")
        self.kpi_sentiment.setAlignment(Qt.AlignCenter)
        kpi_layout.addWidget(self.kpi_sentiment)
        
        layout.addLayout(kpi_layout)
        
        # Action Buttons for Export
        actions_layout = QHBoxLayout()
        self.btn_export_excel = QPushButton("📗 Exportar Excel")
        self.btn_export_excel.clicked.connect(self.export_excel)
        self.btn_export_excel.setStyleSheet("background: #27ae60; color: white; font-weight: bold; padding: 8px;")
        
        self.btn_export_pdf = QPushButton("📕 Gerar PDF")
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_export_pdf.setStyleSheet("background: #c0392b; color: white; font-weight: bold; padding: 8px;")
        
        actions_layout.addWidget(self.btn_export_excel)
        actions_layout.addWidget(self.btn_export_pdf)
        layout.addLayout(actions_layout)

        # Pie Chart Content Categories
        layout.addWidget(QLabel("📂 Distribuição de Conteúdo (Baseado em Texto)"))
        self.canvas_categories = MplCanvas(self, width=5, height=4, dpi=90)
        layout.addWidget(self.canvas_categories)
        
    def update_live_dashboard(self):
        """Busca dados frescos do InsightsEngine e atualiza o painel"""
        try:
            # 1. Stats Gerais
            stats = self.insights.get_live_stats()
            self.kpi_trend.setText(f"Trend Ads (1h)\n{stats['ad_trend_last_hour']:.1f}%")
            self.kpi_savings.setText(f"Economia Est.\n{stats['estimated_savings']:.1f}s")
            self.kpi_prices.setText(f"Preços Det.\n{stats['detected_prices_count']}")
            self.kpi_links.setText(f"Links/CTAs\n{stats['detected_links_count']}")
            self.kpi_sentiment.setText(f"Sentimento\n{stats['avg_sentiment']}")
            
            # 2. Categorias
            cats = self.insights.get_content_categories()
            if cats:
                labels = list(cats.keys())
                sizes = list(cats.values())
                
                self.canvas_categories.axes.clear()
                self.canvas_categories.axes.set_facecolor('#0f0f1e')
                
                # Só desenha se tiver dados
                if sum(sizes) > 0:
                    wedges, texts, autotexts = self.canvas_categories.axes.pie(
                        sizes, labels=labels, autopct='%1.1f%%',
                        startangle=90, colors=['#ff7675', '#74b9ff', '#ffeaa7', '#dfe6e9'],
                        textprops={'color':"w"}
                    )
                    self.canvas_categories.axes.set_title("Categorias Detectadas", color="white")
                else:
                    self.canvas_categories.axes.text(0.5, 0.5, "Coletando dados...", color="white", ha='center')
                    
                self.canvas_categories.draw()
                
        except Exception as e:
            print(f"Erro ao atualizar dashboard: {e}")

    def init_deep_analysis(self, parent):
        """Inicializa a aba de Deep Analysis com visualizações de tendências."""
        layout = QVBoxLayout(parent)
        
        # Row 1: Hashtags e Menções Trending
        trends_layout = QHBoxLayout()
        
        # Hashtags Trending
        hashtags_group = QGroupBox("# Hashtags Trending (1h)")
        hashtags_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        hl = QVBoxLayout()
        self.hashtags_list = QTextEdit()
        self.hashtags_list.setReadOnly(True)
        self.hashtags_list.setMaximumHeight(120)
        self.hashtags_list.setStyleSheet("background: #1e272e; color: #00cec9; border-radius: 5px;")
        hl.addWidget(self.hashtags_list)
        hashtags_group.setLayout(hl)
        trends_layout.addWidget(hashtags_group)
        
        # Menções Trending
        mentions_group = QGroupBox("@ Menções Trending (1h)")
        mentions_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        ml = QVBoxLayout()
        self.mentions_list = QTextEdit()
        self.mentions_list.setReadOnly(True)
        self.mentions_list.setMaximumHeight(120)
        self.mentions_list.setStyleSheet("background: #1e272e; color: #fd79a8; border-radius: 5px;")
        ml.addWidget(self.mentions_list)
        mentions_group.setLayout(ml)
        trends_layout.addWidget(mentions_group)
        
        layout.addLayout(trends_layout)
        
        # Row 2: Marcas Detectadas
        brands_group = QGroupBox("🏷️ Marcas Detectadas (1h)")
        brands_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        bl = QVBoxLayout()
        self.brands_list = QTextEdit()
        self.brands_list.setReadOnly(True)
        self.brands_list.setMaximumHeight(80)
        self.brands_list.setStyleSheet("background: #1e272e; color: #ffeaa7; border-radius: 5px;")
        bl.addWidget(self.brands_list)
        brands_group.setLayout(bl)
        layout.addWidget(brands_group)
        
        # Row 3: Topic Distribution Chart
        layout.addWidget(QLabel("📊 Distribuição por Tópico"))
        self.canvas_topics = MplCanvas(self, width=5, height=3, dpi=90)
        layout.addWidget(self.canvas_topics)

    def update_deep_analysis(self):
        """Atualiza a aba Deep Analysis com dados em tempo real."""
        try:
            # 1. Hashtags
            hashtags = self.insights.get_trending_hashtags(5)
            if hashtags:
                self.hashtags_list.setHtml("<br>".join([f"<b>#{h}</b> ({c}x)" for h, c in hashtags]))
            else:
                self.hashtags_list.setText("Aguardando dados...")
            
            # 2. Menções
            mentions = self.insights.get_trending_mentions(5)
            if mentions:
                self.mentions_list.setHtml("<br>".join([f"<b>@{m}</b> ({c}x)" for m, c in mentions]))
            else:
                self.mentions_list.setText("Aguardando dados...")
            
            # 3. Marcas
            brands = self.insights.get_brand_exposure(5)
            if brands:
                self.brands_list.setHtml(" | ".join([f"<b>{b.upper()}</b> ({c}x)" for b, c in brands]))
            else:
                self.brands_list.setText("Nenhuma marca detectada ainda.")
            
            # 4. Tópicos
            topics = self.insights.get_topic_distribution()
            self.canvas_topics.axes.clear()
            self.canvas_topics.axes.set_facecolor('#0f0f1e')
            
            if topics:
                labels = list(topics.keys())
                sizes = list(topics.values())
                colors = ['#ff7675', '#74b9ff', '#55efc4', '#ffeaa7', '#a29bfe', '#fd79a8', '#e17055', '#00cec9']
                
                self.canvas_topics.axes.barh(labels, sizes, color=colors[:len(labels)])
                self.canvas_topics.axes.set_xlabel("Quantidade", color='white')
                self.canvas_topics.axes.tick_params(axis='y', colors='white')
                self.canvas_topics.axes.tick_params(axis='x', colors='white')
            else:
                self.canvas_topics.axes.text(0.5, 0.5, "Coletando...", color="white", ha='center')
            
            self.canvas_topics.draw()
            
        except Exception as e:
            print(f"Erro ao atualizar Deep Analysis: {e}")

    def init_benchmarking(self, parent):
        """Inicializa a aba de Benchmarking de Criadores."""
        layout = QVBoxLayout(parent)
        
        layout.addWidget(QLabel("🤼 Comparativo de Estrategia por Criador (Últimos 7 dias)"))
        
        self.canvas_bench = MplCanvas(self, width=6, height=4, dpi=100)
        layout.addWidget(self.canvas_bench)
        
        # Info Table / Text
        self.bench_info = QTextEdit()
        self.bench_info.setReadOnly(True)
        self.bench_info.setMaximumHeight(100)
        self.bench_info.setStyleSheet("background: #1e272e; color: #ecf0f1; border-radius: 5px;")
        layout.addWidget(self.bench_info)

    def update_benchmarking(self):
        """Atualiza o gráfico de benchmarking."""
        try:
            data = self.insights.get_creator_benchmarking()
            if not data: return
            
            names = list(data.keys())
            densities = [d['ad_density'] for d in data.values()]
            totals = [d['total_stories'] for d in data.values()]
            
            self.canvas_bench.axes.clear()
            self.canvas_bench.axes.set_facecolor('#0f0f1e')
            
            # Gráfico de barras duplo: Total vs Densidade de Ads
            x = range(len(names))
            self.canvas_bench.axes.bar(x, totals, width=0.4, label='Total Stories', color='#74b9ff')
            # Densidade em escala diferente? Usaremos eixo secundário idealmente, mas barras lado a lado basta
            
            self.canvas_bench.axes.set_xticks(x)
            self.canvas_bench.axes.set_xticklabels(names, color='white', rotation=15)
            self.canvas_bench.axes.tick_params(axis='y', colors='white')
            self.canvas_bench.axes.legend()
            self.canvas_bench.draw()
            
            # Texto detalhado
            html = "<table width='100%'>"
            for name, info in data.items():
                html += f"<tr><td><b>@{name}</b></td><td>Tópico: {info['primary_topic']}</td><td>Ads: {info['ad_density']:.1f}%</td><td>Engajamento: {info['engagement_potential']}</td></tr>"
            html += "</table>"
            self.bench_info.setHtml(html)
            
        except Exception as e:
            print(f"Erro ao atualizar benchmarking: {e}")

    def check_viral_alerts(self):
        """Verifica se há picos virais e exibe o banner."""
        try:
            spikes = self.insights.detect_viral_spikes()
            if spikes:
                top_spike = spikes[0]
                msg = f"🚀 ALERTA VIRAL: {top_spike['item'].upper()} está crescendo rápido ({top_spike['growth']}) nos últimos 30 min!"
                self.alert_banner.setText(msg)
                self.alert_banner.setStyleSheet("background: #e67e22; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
                self.alert_banner.show()
            else:
                self.alert_banner.hide()
        except:
            pass

    def export_excel(self):
        success, msg = self.exporter.export_to_excel()
        if success: self.log(f"✅ Excel exportado: {msg}", "success")
        else: self.log(f"❌ Erro ao exportar Excel: {msg}", "error")

    def export_pdf(self):
        success, msg = self.exporter.export_to_pdf()
        if success: self.log(f"✅ PDF gerado: {msg}", "success")
        else: self.log(f"❌ Erro ao gerar PDF: {msg}", "error")

    def log(self, message, msg_type="info"):
        colors = {
            "info": "#00ff00",
            "success": "#00ffff",
            "warning": "#ffaa00",
            "error": "#ff0000"
        }
        color = colors.get(msg_type, "#ffffff")
        timestamp = time.strftime("%H:%M:%S")
        html = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        self.log_text.append(html)
        self.log_text.moveCursor(QTextCursor.End)
    
    def update_progress(self, data):
        self.current_data = data
        
        stories = data.get('total_stories', 0)
        ads = data.get('total_ads', 0)
        likes = data.get('liked_count', 0)
        profiles = data.get('unique_profiles', 0)
        
        self.stories_label.setText(f"Stories\n{stories}")
        self.ads_label.setText(f"Anúncios\n{ads}")
        self.likes_label.setText(f"Likes\n{likes}")
        self.profiles_label.setText(f"Perfis\n{profiles}")
        
        # Atualiza monitor e gráficos
        self.update_monitor_display()
        self.update_graphs()
    
    def update_monitor_display(self):
        """Atualiza o display de monitoramento em tempo real"""
        data = self.current_data
        
        if not data:
            self.monitor_text.setHtml("""
                <pre style='color: #00ff00; font-weight: bold;'>
╔══════════════════════════════════════════════╗
║     AGUARDANDO INÍCIO DO BOT...              ║
╚══════════════════════════════════════════════╝
                </pre>
            """)
            return
        
        total = data.get('total_stories', 0)
        ads = data.get('total_ads', 0)
        real = data.get('real_stories', 0)
        likes = data.get('liked_count', 0)
        profiles = data.get('unique_profiles', 0)
        elapsed = data.get('elapsed_time', 0)
        speed = data.get('speed', 0)
        ad_pct = data.get('ad_percentage', 0)
        
        # Calcula métricas
        content_pct = 100 - ad_pct
        human_time = total * 5.0
        time_saved = human_time - elapsed if human_time > elapsed else 0
        
        # Barra de progresso visual
        def draw_bar(percentage, length=20):
            fill = int(length * percentage / 100)
            return '█' * fill + '░' * (length - fill)
        
        html = f"""
<pre style='color: #00ff00; font-weight: bold; font-size: 11pt;'>
╔══════════════════════════════════════════════╗
║        ⚡ MONITOR EM TEMPO REAL              ║
╠══════════════════════════════════════════════╣
║ ⏱️  Tempo Decorrido:  {str(timedelta(seconds=int(elapsed)))}
║ ⚡  Velocidade:       {speed:.1f} stories/min
║ 💎  Tempo Economizado: {str(timedelta(seconds=int(time_saved)))}
╠══════════════════════════════════════════════╣
║ 🎯 ATIVIDADE DO BOT
║    Stories Totais:    {total}
║    Conteúdo Real:     {real}
║    Anúncios:          {ads}
║    Likes Dados:       {likes}
║    Perfis Únicos:     {profiles}
╠══════════════════════════════════════════════╣
║ 📊 ECONOMIA DA ATENÇÃO
║
║  Conteúdo: {draw_bar(content_pct, 15)} {content_pct:.1f}%
║  Anúncios: {draw_bar(ad_pct, 15)} {ad_pct:.1f}%
║
</pre>
<pre style='color: #ffaa00; font-weight: bold;'>
║  💡 {self._get_ad_insight(real, ads)}
</pre>
<pre style='color: #00ff00; font-weight: bold;'>
╚══════════════════════════════════════════════╝
</pre>
        """
        self.monitor_text.setHtml(html)
    
    def _get_ad_insight(self, real, ads):
        if ads == 0:
            return "Sessão limpa! Nenhum anúncio detectado."
        freq = int(real / ads) if ads > 0 else 0
        return f"Instagram mostra 1 ad a cada {freq} stories."
    
    def update_graphs(self):
        """Atualiza todos os gráficos"""
        data = self.current_data
        if not data or data.get('total_stories', 0) == 0:
            return
        
        # Gráfico 1: Ads vs Conteúdo (Pizza)
        self.update_ads_chart(data)
        
        # Gráfico 2: Top Flooders (Barras)
        self.update_flooders_chart(data)
        
        # Gráfico 3: Métricas de Performance (Linhas/Barras)
        self.update_metrics_chart(data)
    
    def update_ads_chart(self, data):
        """Gráfico de pizza: Ads vs Conteúdo"""
        self.canvas_ads.axes.clear()
        
        ads = data.get('total_ads', 0)
        real = data.get('real_stories', 0)
        
        if ads == 0 and real == 0:
            return
        
        labels = ['Conteúdo Real', 'Anúncios']
        sizes = [real, ads]
        colors = ['#6c5ce7', '#ff6b6b']
        explode = (0.05, 0.05)
        
        wedges, texts, autotexts = self.canvas_ads.axes.pie(
            sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=90,
            textprops={'color': 'white', 'fontsize': 12, 'weight': 'bold'}
        )
        
        # Adiciona borda branca nos wedges
        for wedge in wedges:
            wedge.set_edgecolor('white')
            wedge.set_linewidth(2)
        
        self.canvas_ads.axes.set_title('Economia da Atenção: Conteúdo vs Anúncios',
                                        color='white', fontsize=14, weight='bold', pad=20)
        self.canvas_ads.draw()
    
    def update_flooders_chart(self, data):
        """Gráfico de barras: Top 5 Flooders"""
        self.canvas_flooders.axes.clear()
        
        profile_map = data.get('profile_map', {})
        if not profile_map:
            self.canvas_flooders.axes.text(0.5, 0.5, 'Aguardando dados...',
                                            ha='center', va='center', color='white',
                                            fontsize=14, transform=self.canvas_flooders.axes.transAxes)
            self.canvas_flooders.draw()
            return
        
        sorted_profiles = sorted(profile_map.items(), key=lambda x: x[1], reverse=True)[:5]
        users = [f"@{user}" for user, _ in sorted_profiles]
        counts = [count for _, count in sorted_profiles]
        
        colors_gradient = ['#6c5ce7', '#a29bfe', '#74b9ff', '#00b894', '#55efc4']
        
        bars = self.canvas_flooders.axes.barh(users, counts, color=colors_gradient, 
                                               edgecolor='white', linewidth=2)
        
        # Adiciona valores nas barras
        for i, (bar, count) in enumerate(zip(bars, counts)):
            width = bar.get_width()
            self.canvas_flooders.axes.text(width + max(counts)*0.02, bar.get_y() + bar.get_height()/2,
                                           f'{count}',
                                           ha='left', va='center', color='white',
                                           fontsize=11, weight='bold')
        
        self.canvas_flooders.axes.set_xlabel('Stories Postados', color='white', fontsize=11, weight='bold')
        self.canvas_flooders.axes.set_title('🏆 Top 5 Flooders - Quem Posta Mais?',
                                             color='white', fontsize=14, weight='bold', pad=20)
        self.canvas_flooders.axes.tick_params(colors='white', labelsize=10)
        self.canvas_flooders.axes.spines['bottom'].set_color('#6c5ce7')
        self.canvas_flooders.axes.spines['left'].set_color('#6c5ce7')
        self.canvas_flooders.axes.spines['bottom'].set_linewidth(2)
        self.canvas_flooders.axes.spines['left'].set_linewidth(2)
        self.canvas_flooders.axes.spines['top'].set_visible(False)
        self.canvas_flooders.axes.spines['right'].set_visible(False)
        self.canvas_flooders.axes.invert_yaxis()
        self.canvas_flooders.axes.grid(axis='x', alpha=0.2, linestyle='--', color='#a29bfe')
        self.canvas_flooders.fig.tight_layout()
        self.canvas_flooders.draw()
    
    def update_metrics_chart(self, data):
        """Gráfico de métricas: Stories, Ads, Likes, Speed"""
        self.canvas_metrics.axes.clear()
        
        total = data.get('total_stories', 0)
        ads = data.get('total_ads', 0)
        likes = data.get('liked_count', 0)
        profiles = data.get('unique_profiles', 0)
        
        categories = ['Stories\nTotais', 'Anúncios', 'Likes\nDados', 'Perfis\nÚnicos']
        values = [total, ads, likes, profiles]
        colors = ['#6c5ce7', '#ff6b6b', '#e84393', '#00b894']
        
        bars = self.canvas_metrics.axes.bar(categories, values, color=colors, alpha=0.9, 
                                             edgecolor='white', linewidth=2.5)
        
        # Adiciona valores em cima das barras
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.canvas_metrics.axes.text(bar.get_x() + bar.get_width()/2, height + max(values)*0.02,
                                          f'{value}',
                                          ha='center', va='bottom', color='white',
                                          fontsize=12, weight='bold')
        
        self.canvas_metrics.axes.set_ylabel('Quantidade', color='white', fontsize=11, weight='bold')
        self.canvas_metrics.axes.set_title('⚡ Métricas de Performance da Sessão',
                                           color='white', fontsize=14, weight='bold', pad=20)
        self.canvas_metrics.axes.tick_params(colors='white', labelsize=10)
        self.canvas_metrics.axes.spines['bottom'].set_color('#6c5ce7')
        self.canvas_metrics.axes.spines['left'].set_color('#6c5ce7')
        self.canvas_metrics.axes.spines['bottom'].set_linewidth(2)
        self.canvas_metrics.axes.spines['left'].set_linewidth(2)
        self.canvas_metrics.axes.spines['top'].set_visible(False)
        self.canvas_metrics.axes.spines['right'].set_visible(False)
        self.canvas_metrics.axes.grid(axis='y', alpha=0.2, linestyle='--', color='#a29bfe')
        self.canvas_metrics.fig.tight_layout()
        self.canvas_metrics.draw()
    
    def show_final_report(self, report):
        if not report:
            return
        
        total = report.get('total_stories', 0)
        ads = report.get('total_ads', 0)
        real = report.get('real_stories', 0)
        likes = report.get('liked_count', 0)
        duration = report.get('duration', 0)
        profile_map = report.get('profile_map', {})
        
        # Métricas calculadas
        human_time = total * 5.0
        time_saved = human_time - duration if human_time > duration else 0
        speed = (total / (duration / 60)) if duration > 0 else 0
        ad_pct = (ads / total * 100) if total > 0 else 0
        content_pct = 100 - ad_pct
        
        self.log("", "info")
        self.log("╔══════════════════════════════════════════════════════════╗", "success")
        self.log("║           📊 RELATÓRIO FINAL DE INTELIGÊNCIA             ║", "success")
        self.log("╠══════════════════════════════════════════════════════════╣", "success")
        self.log(f"║ ⏱️  Duração da Sessão:   {str(timedelta(seconds=int(duration)))}", "success")
        self.log(f"║ ⚡  Velocidade do Bot:   {speed:.1f} stories/min", "success")
        self.log(f"║ 💎  Tempo Economizado:   {str(timedelta(seconds=int(time_saved)))} (vs Humano)", "success")
        self.log("╠══════════════════════════════════════════════════════════╣", "success")
        self.log("║ 🎯 AÇÃO DO ROBÔ                                          ║", "success")
        self.log(f"║    Stories Vistos:       {total}", "success")
        self.log(f"║    Conteúdo Real:        {real}", "success")
        self.log(f"║    Anúncios:             {ads}", "success")
        self.log(f"║    Likes Dados:          {likes}", "success")
        self.log(f"║    Perfis Únicos:        {len(profile_map)}", "success")
        self.log("╠══════════════════════════════════════════════════════════╣", "success")
        self.log("║ ⚖️  ECONOMIA DA ATENÇÃO (Ads vs Conteúdo)                 ║", "success")
        self.log(f"║    Conteúdo: {content_pct:.1f}% | Anúncios: {ad_pct:.1f}%", "success")
        
        if ads > 0 and real > 0:
            freq = int(real / ads)
            self.log(f"║    👉 Instagram mostra 1 anúncio a cada {freq} stories", "success")
        
        if profile_map:
            self.log("╠══════════════════════════════════════════════════════════╣", "success")
            self.log("║ 🏆 RANKING DE FLOODERS (Top 5):                         ║", "success")
            sorted_profiles = sorted(profile_map.items(), key=lambda x: x[1], reverse=True)[:5]
            for i, (user, count) in enumerate(sorted_profiles, 1):
                pct = (count / total * 100) if total > 0 else 0
                self.log(f"║  {i}. @{user:<20} {count:>3} stories ({pct:.1f}%)", "success")
        
        self.log("╚══════════════════════════════════════════════════════════╝", "success")
    
    def start_bot(self):
        config = {
            'target_profile': self.target_profile_input.text(),
            'story_x': self.story_x_input.value(),
            'story_y': self.story_y_input.value(),
            'next_x': self.next_x_input.value(),
            'next_y': self.next_y_input.value(),
            'heart_x': self.heart_x_input.value(),
            'heart_y': self.heart_y_input.value(),
            'min_delay': self.min_time_input.value(),
            'max_delay': self.max_time_input.value(),
            'click_duration': self.click_duration_input.value(),
            'turbo_mode': self.turbo_mode_check.isChecked(),
            'package': 'com.instagram.android'
        }
        
        self.bot_thread = BotWorker(config)
        self.bot_thread.log_signal.connect(self.log)
        self.bot_thread.progress_signal.connect(self.update_progress)
        self.bot_thread.finished_signal.connect(self.show_final_report)
        self.bot_thread.finished.connect(self.on_bot_finished)
        self.bot_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setMaximum(0)
        self.log("🚀 Bot iniciado!", "success")

    def update_realtime_config(self):
        """Atualiza a configuração do bot em tempo real sem precisar parar"""
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.config['min_delay'] = self.min_time_input.value()
            self.bot_thread.config['max_delay'] = self.max_time_input.value()
            self.bot_thread.config['click_duration'] = self.click_duration_input.value()
            self.bot_thread.config['turbo_mode'] = self.turbo_mode_check.isChecked()
            # Feedback visual sutil no log (opcional, removi para não poluir)
            # self.log(f"⏱️ Tempo atualizado: {self.min_time_input.value()}s - {self.max_time_input.value()}s", "info")
    
    def stop_bot(self):
        if self.bot_thread:
            self.bot_thread.stop()
            self.log("🛑 Parando bot...", "warning")
    
    def on_bot_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.log("✅ Bot finalizado", "success")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstaBotGUI()
    window.show()
    sys.exit(app.exec_())
