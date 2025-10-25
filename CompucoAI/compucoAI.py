#compucoAI
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont, QMovie
from PySide6.QtWidgets import QWidget, QTextEdit, QApplication, QPlainTextEdit, QToolButton, QStyle, QInputDialog, QMessageBox, QPushButton, QHBoxLayout
from google import genai
from google.genai.types import GenerateContentConfig
import subprocess
import os
import sys
import shutil
import platform
import json
import sqlite3

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compuco AI")

        connection = sqlite3.connect("automations.db")
        c = connection.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS automations
                    (id INTEGER PRIMARY KEY, name TEXT NOT NULL, code TEXT NOT NULL)''')
        connection.commit()
        connection.close()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout()
        central.setLayout(layout)
        self.text = QtWidgets.QLabel("Automate Anything",
                    alignment=QtCore.Qt.AlignCenter)
        self.text.setFont(QFont("Noto Sans Symbols", 48, QFont.Weight.Bold))
        layout.addWidget(self.text)

        self.prompt_box = QtWidgets.QTextEdit()
        self.prompt_box.setPlaceholderText("What do you want to do today? ")
        layout.addWidget(self.prompt_box)

        self.button = QtWidgets.QPushButton("Let's Go!")
        layout.addWidget(self.button)

        toolbar = self.addToolBar("MainWindow")
        toolbar.setMovable(False)
        toolbar.setOrientation(Qt.Horizontal)
        menu_button = menu()
        toolbar.addWidget(menu_button)

        self.button.clicked.connect(self.ai_initial)
    
    @QtCore.Slot()
    def ai_initial(self):
        self.system = platform.system()
        try:
            key = os.environ.get("GOOGLE_API")
            self.prompt = self.prompt_box.toPlainText()
        except ValueError:
            print("API key not found. Please export your Google GenAI API key to 'GOOGLE_API'.")
            sys.exit(1)

        self.hide()

        self.loading_label = QtWidgets.QLabel()
        self.loading_label.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.loading_label.setGeometry(800, 100, 400, 400)
        self.loading_label.setScaledContents(True)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.movie = QMovie("loading.gif")
        self.loading_label.setMovie(self.movie)

        self.movie.start()
        self.loading_label.show()

        self.worker = AIWorker(self.prompt, self.system, key)
        self.worker.finished.connect(self.on_finish)
        self.worker.start()

    @QtCore.Slot(str)
    def on_finish(self, response):
        self.movie.stop()
        self.loading_label.hide()
        self.switch_to_chat(response)
        self.close()

    def switch_to_chat(self, response):
        self.chat = ChatWindow(response)
        self.chat.resize(800,400)
        self.chat.show()

class AIWorker(QThread):
    finished = QtCore.Signal(str)

    def __init__(self, prompt, system, key):
        super().__init__()
        self.prompt = prompt
        self.system = system
        self.key = key

    def run(self):
        client = genai.Client(api_key=self.key)
        ai_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[f"{self.prompt}. Make an automation according to the user's request. If the request at the beginning is not a request for creating an automation, explain why to the user, but add the phrase '[Not code]', as shown exactly as shown at the very beginning of the response. Follow these instructions exactly as stated. Your response should only be code with included comments that you want to add. Don't add any introductory or concluding statements or anything other than code. Choose the most optimal programming language for the request. Make the code suitable for this platform: {self.system}."])
        response = ai_response.text

        self.finished.emit(response)


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self,response):
        super().__init__()
        self.setWindowTitle("Chat")
        self.response = response

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout()
        central.setLayout(layout)

        self.code_box = QPlainTextEdit()
        self.code_box.setPlainText(response)
        self.code_box.setReadOnly(True)
        self.code_box.setFont(QFont("Roboto Mono", 16))
        layout.addWidget(self.code_box)

        self.chat_box = QtWidgets.QTextEdit()
        self.chat_box.setPlaceholderText("Type your request... ")
        layout.addWidget(self.chat_box)

        self.button = QtWidgets.QPushButton("Send ➡️")
        layout.addWidget(self.button)

        self.save = QtWidgets.QPushButton("Save 💾")
        layout.addWidget(self.save)

        toolbar2 = self.addToolBar("ChatWindow")
        toolbar2.setMovable(False)
        toolbar2.setOrientation(Qt.Horizontal)
        menu_button2 = menu()
        toolbar2.addWidget(menu_button2)

        self.button.clicked.connect(self.ai_chat)
        self.save.clicked.connect(self.save_automation)

    @QtCore.Slot()
    def ai_chat(self):
        self.system = platform.system()
        try:
            key = os.environ.get("GOOGLE_API")
            self.client = genai.Client(api_key=key)
            self.chat_prompt = self.chat_box.toPlainText()
        except ValueError:
            print("API key not found. Please export your Google GenAI API key to 'GOOGLE_API' as an environment variable.")
            sys.exit(1)

        self.ai_response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[f"{self.chat_prompt}. Make an automation according to the user's request. If the request at the beginning is not a request for creating an automation, explain why to the user, but add the phrase '[Not code] ', as shown exactly as shown at the very beginning of the response. Follow these instructions exactly as stated. Your response should only be code with included comments that you want to add. Don't add any introductory or concluding statements. Return only the code and none of the thinking procedure. Choose either bash or Python, and add either [bash] or [python] at the start of your code. Add a newline after the header (either [bash] or [python]). Make the code suitable for this platform: {self.system}. If the user wants you to run the code, just respond, exactly as follows ([code] means the code you have provided), 'Running [code]'."])
        self.response = self.ai_response.text

        self.code_box.appendPlainText(f"\n--------------------------------\n{self.response}")
        self.code_box.verticalScrollBar().setValue(
            self.code_box.verticalScrollBar().maximum()
        )

    @QtCore.Slot()
    def save_automation(self):
        data = self.response

        text, ok = QInputDialog.getText(self, "Automation Dialog", "What would you like to call this automation?")
        if not text.strip() and not ok:
            return
        name = text.strip()

        connection = sqlite3.connect("automations.db")
        c = connection.cursor()
        c.execute("INSERT INTO automations (name, code) VALUES (?, ?)",
                  (name, data))
        connection.commit()
        connection.close()

        QMessageBox.information(self, "Saved", f"Automation '{name}' saved successfully!")

class menu(QtWidgets.QToolButton):
    def __init__(self):
        super().__init__()
        style = self.style()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton)
        self.setIcon(icon)

        self.setPopupMode(QToolButton.InstantPopup)

        menu = QtWidgets.QMenu(self)
        home = menu.addAction("Home")
        automations = menu.addAction("Saved Automations")
        settings = menu.addAction("Settings")

        home.triggered.connect(self.go_home)
        automations.triggered.connect(self.go_to_automations)
        #settings.triggered.connect(self.go_to_settings)

        self.setMenu(menu)

    def go_home(self):
        self.home = MainWindow()
        self.home.resize(800,400)
        self.home.show()
        self.close()

    def go_to_automations(self):
        self.automations = AutomationsWindow()
        self.automations.resize(800,400)
        self.automations.show()
        self.close()

class AutomationTiles(QWidget):
    def __init__(self, code, name):
        super().__init__()
        self.system = platform.system()

        self.code = code
        self.name = name

        self.label = QtWidgets.QLabel(self.name)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.run = QPushButton("Run")
        self.run.clicked.connect(self.run_automation)
        self.add_to_startup = QPushButton("Add to Startup")
        self.add_to_startup.clicked.connect(self.add_automation_to_startup)
        layout.addWidget(self.run)
        layout.addWidget(self.add_to_startup)

    def run_automation(self):

        if "[bash]" in self.code:
            try:
                with open(f"{self.name}.sh", "w") as script:
                    self.code = self.code.replace("[bash]", "").replace("[python]", "").strip()
                    script.write(self.code)
                    try:
                        subprocess.run(['bash', f"{self.name}.sh"], capture_output=True, text=True, check=True)
                    except subprocess.CalledProcessError as e:
                        QMessageBox.information(self, "Error", e)
            except Exception as e:
                QMessageBox.information(self, "Error", e)
        elif "[python]" in self.code:
            try:
                self.code = self.code.replace("[bash]", "").replace("[python]", "").strip()
                exec(self.code)
            except Exception as e:
                QMessageBox.information(self, "Error", e)

    def add_automation_to_startup(self):
        self.key = os.environ.get("GOOGLE_API")
        self.client = genai.Client(api_key=self.key)

        self.system = platform.system()

        try:
                with open(f"{self.name}-startup.sh", "w") as script:
                    self.code = self.code.replace("[bash]", "").replace("[python]", "").strip()
                    script.write(self.code)
                    try:

                        if self.system == "Linux":
                            os.chmod(f"{self.name}-startup.sh", 0o755)
                            autostart_dir = os.path.expanduser("~/.config/autostart")
                            os.makedirs(autostart_dir, exist_ok=True)
                            shutil.copy(f"{self.name}-startup.sh", autostart_dir)

                            QMessageBox.information(self, "Success", f"{self.name} added to startup!")

                        elif self.system == "Windows":
                            with open(bat_path, "w") as f:
                                self.code = self.code.replace("[bash]", "").replace("[python]", "").strip()
                                f.write(self.code)

                            startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
                            shutil.copy(f"{self.name}-startup.bat", startup_dir)

                            QMessageBox.information(self, "Success", f"{self.name} added to startup!")

                        else:
                            QMessageBox.information(self, "Error", "MacOS is not supported for startup automations")

                    except Exception as e:
                        QMessageBox.information(self, "Error", str(e))

        except Exception as e:
            QMessageBox.information(self, "Error", str(e))

class AutomationsWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Saved Automations")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout()
        central.setLayout(layout)

        connection = sqlite3.connect("automations.db")
        c = connection.cursor()
        c.execute("SELECT name, code FROM automations")
        automations_list = c.fetchall()
        connection.close()

        for name, code in automations_list:
            tile = AutomationTiles(code, name)
            layout.addWidget(tile)

        layout.addStretch()

        toolbar3 = self.addToolBar("ChatWindow")
        toolbar3.setMovable(False)
        toolbar3.setOrientation(Qt.Horizontal)
        menu_button3 = menu()
        toolbar3.addWidget(menu_button2)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("""
    /* ===== Global Window & Widgets ===== */
    QWidget {
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(10,10,10,0.95),
            stop:1 rgba(20,0,40,0.95)
        );  /* Dark gradient base */
        color: #00FFEA;
        font-family: "Orbitron", "Roboto Mono", monospace;
    }

    /* ===== Labels ===== */
    QLabel {
        color: #FF00FF;
        font-size: 36px;
        font-weight: bold;
        qproperty-alignment: 'AlignCenter';
    }

    /* Neon glow for labels */
    QLabel#glow {
        color: #00FFEA;
        text-shadow: 0 0 10px #00FFEA, 0 0 20px #00FFEA, 0 0 30px #FF00FF;
    }

    /* ===== Text Boxes ===== */
    QTextEdit, QPlainTextEdit {
        background-color: rgba(255, 255, 255, 0.05); /* semi-transparent glass */
        border: 2px solid rgba(0, 255, 234, 0.7);
        border-radius: 18px;
        padding: 12px;
        color: #00FFEA;
        selection-background-color: rgba(255, 0, 255, 0.3);
        font-size: 16px;
        transition: all 0.3s;
    }

    QTextEdit:hover, QPlainTextEdit:hover {
        border: 2px solid rgba(255, 0, 255, 0.9);
        background-color: rgba(255, 255, 255, 0.1);
    }

    /* ===== Buttons ===== */
    QPushButton {
        background-color: rgba(255, 0, 255, 0.2);
        color: #0D0D0D;
        border: 2px solid #00FFEA;
        border-radius: 14px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 16px;
    }

    QPushButton:hover {
        background-color: rgba(0, 255, 234, 0.4);
        color: #0D0D0D;
        border: 2px solid #FF00FF;
        transform: scale(1.05);
    }

    /* ===== Tool Buttons ===== */
    QToolButton {
        background-color: rgba(0, 0, 0, 0.2);
        border: 2px solid rgba(255, 0, 255, 0.7);
        border-radius: 12px;
        padding: 6px;
    }

    QToolButton:hover {
        border: 2px solid #00FFEA;
        background-color: rgba(255, 0, 255, 0.3);
    }

    /* ===== Menus ===== */
    QMenu {
        background-color: rgba(0, 0, 0, 0.4);
        color: #00FFEA;
        border: 2px solid #FF00FF;
        border-radius: 12px;
    }

    QMenu::item:selected {
        background-color: rgba(255, 0, 255, 0.5);
        color: #0D0D0D;
    }

    /* ===== Scrollbars ===== */
    QScrollBar:vertical {
        background: rgba(20,20,20,0.2);
        width: 12px;
        margin: 0px 0px 0px 0px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background: rgba(0,255,234,0.6);
        min-height: 20px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical:hover {
        background: rgba(255,0,255,0.8);
    }

    QScrollBar::add-line, QScrollBar::sub-line {
        height: 0px;
    }

    #glowLabel {
        color: #FF00FF;
        text-shadow: 0 0 15px #FF00FF, 0 0 30px #FF00FF, 0 0 45px #00FFEA;
    }
    """)



    window = MainWindow()
    window.resize(800,400)
    window.show()

    sys.exit(app.exec())
