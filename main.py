# ==========================================
# CENTRAL DE ALERTAS METEOROLÓGICOS
# Versão 5.1 - Correção da Janela de Emergência e Parada de Som
# Desenvolvedor: Thiago
# © 2026 - Todos os direitos reservados.
# ==========================================

import sys
import os
import winsound
import requests
from datetime import datetime
from plyer import notification  # Biblioteca para notificações nativas do Windows

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QMessageBox,
    QMainWindow,
    QDialog,
    QLineEdit,
    QFormLayout,
    QTextEdit,
    QComboBox
)

os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

# -----------------------
# CONFIGURAÇÕES DE LINKS
# -----------------------
URL_SERVIDOR_FIREBASE = "https://central-de-alertas-26-default-rtdb.firebaseio.com/.json"
URL_PAGINA_ANUNCIOS = "anuncios.html"

# -----------------------
# FUNÇÕES DE SUPORTE
# -----------------------

def encontrar_caminho_recurso(nome_arquivo):
    try:
        pasta_base = sys._MEIPASS
    except AttributeError:
        pasta_base = os.path.abspath(".")
    return os.path.join(pasta_base, nome_arquivo)

def disparar_notificacao_windows(titulo, mensagem):
    try:
        notification.notify(
            title=titulo,
            message=mensagem,
            app_name="Central de Alertas",
            app_icon=encontrar_caminho_recurso("logo.ico") if os.path.exists("logo.ico") else None,
            timeout=7
        )
    except Exception as e:
        print(f"Erro ao disparar notificação: {e}")

def tocar_alarme_usa():
    try:
        caminho_do_som = encontrar_caminho_recurso("jeremayjimenez-usa-eas-alarm-249125.wav")
        winsound.PlaySound(caminho_do_som, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    except Exception as e:
        print(f"Erro ao tocar som USA: {e}")

def tocar_alarme_iphone():
    try:
        caminho_do_som = encontrar_caminho_recurso("jeremayjimenez-eas-alarm-iphone-alarm-262882.wav")
        winsound.PlaySound(caminho_do_som, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    except Exception as e:
        print(f"Erro ao tocar som Iphone: {e}")

def tocar_bipe_curto():
    try:
        from threading import Thread
        def bipar():
            for _ in range(3):
                winsound.Beep(2000, 150)
                import time
                time.sleep(0.1)
        Thread(target=bipar).start()
    except Exception as e:
        print(f"Erro ao emitir bipe: {e}")

def parar_todos_os_sons():
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception as e:
        print(f"Erro ao parar áudio: {e}")


class CentralAlertasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Central de Alertas Meteorológicos")
        self.resize(550, 750)
        self.setWindowIcon(QIcon(encontrar_caminho_recurso("logo.png")))
        
        self.estado_atual_internet = -1
        self.historico_alertas = []
        
        self.init_ui()
        
        # Timers paralelos
        self.timer_relogio = QTimer()
        self.timer_relogio.timeout.connect(self.atualizar_relogio)
        self.timer_relogio.start(1000)
        
        self.timer_nuvem = QTimer()
        self.timer_nuvem.timeout.connect(self.checar_alertas_nuvem)
        self.timer_nuvem.start(3000)
        
        self.atualizar_relogio()
        self.checar_alertas_nuvem()
        
        # Executa a geolocalização automática por IP após abrir
        QTimer.singleShot(200, self.detectar_localizacao_por_ip)

    def init_ui(self):
        # Menu Superior
        menu = self.menuBar()
        arquivo = menu.addMenu("Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close)
        arquivo.addAction(acao_sair)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Título Superior
        self.titulo = QLabel("🚨 CENTRAL DE ALERTAS\nMETEOROLÓGICOS")
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold; line-height: 1.3; color: white;")
        
        # Labels de Informações Centrais
        self.cidade = QLabel("📍 Localização: Detectando...")
        self.cidade.setAlignment(Qt.AlignCenter)
        self.cidade.setStyleSheet("font-weight: bold; color: white;")
        
        self.status = QLabel("🟢 Sistema ONLINE")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-weight: bold; color: white;")
        
        self.relogio = QLabel()
        self.relogio.setAlignment(Qt.AlignCenter)
        self.relogio.setStyleSheet("font-weight: bold; color: white;")

        # Quadro Alertas Padrão
        self.caixa1 = QFrame()
        layout_c1 = QVBoxLayout()
        self.lbl_title1 = QLabel("⚠️ ALERTAS")
        self.lbl_title1.setStyleSheet("font-weight: bold; color: white; border: none;")
        self.texto_alerta = QLabel("Nenhum alerta ativo.")
        self.texto_alerta.setStyleSheet("color: white; border: none;")
        self.texto_mensagem = QLabel("")
        self.texto_mensagem.setWordWrap(True)
        self.texto_mensagem.setStyleSheet("color: #d0d0d0; border: none;")
        layout_c1.addWidget(self.lbl_title1)
        layout_c1.addWidget(self.texto_alerta)
        layout_c1.addWidget(self.texto_mensagem)
        self.caixa1.setLayout(layout_c1)

        # Quadro Alertas Graves
        self.caixa2 = QFrame()
        layout_c2 = QVBoxLayout()
        self.lbl_title2 = QLabel("🚨 ALERTAS GRAVES")
        self.lbl_title2.setStyleSheet("font-weight: bold; color: white; border: none;")
        self.texto_grave = QLabel("Nenhum alerta grave.")
        self.texto_grave.setStyleSheet("color: white; border: none;")
        layout_c2.addWidget(self.lbl_title2)
        layout_c2.addWidget(self.texto_grave)
        self.caixa2.setLayout(layout_c2)

        # Botão Painel Administrador
        self.botao_admin = QPushButton("👑 Painel do Administrador")
        self.botao_admin.clicked.connect(self.abrir_admin)

        # Caixa de Histórico de Alertas Recentes
        self.caixa_historico = QFrame()
        layout_hist = QVBoxLayout()
        self.lbl_title_hist = QLabel("📜 HISTÓRICO RECENTE")
        self.lbl_title_hist.setStyleSheet("font-size: 15px; font-weight: bold; color: white; border: none;")
        self.texto_historico = QLabel("Nenhum registro anterior.")
        self.texto_historico.setWordWrap(True)
        self.texto_historico.setStyleSheet("font-size: 13px; color: #e0e0e0; border: none;")
        layout_hist.addWidget(self.lbl_title_hist)
        layout_hist.addWidget(self.texto_historico)
        self.caixa_historico.setLayout(layout_hist)

        # Área de Anúncios organizada
        self.caixa_anuncio = QFrame()
        self.caixa_anuncio.setFixedHeight(140)
        self.caixa_anuncio.setStyleSheet("QFrame { background-color: #222222; border: 1px solid #444444; border-radius: 12px; }")
        layout_anuncio = QVBoxLayout()
        layout_anuncio.setContentsMargins(0, 0, 0, 0)
        self.navegador_anuncios = QWebEngineView()
        self.navegador_anuncios.setUrl(QUrl(URL_PAGINA_ANUNCIOS))
        layout_anuncio.addWidget(self.navegador_anuncios)
        self.caixa_anuncio.setLayout(layout_anuncio)

        # Rodapé Unificado
        self.fonte = QLabel("Fonte: INMET / GFS")
        self.fonte.setAlignment(Qt.AlignCenter)
        self.fonte.setStyleSheet("font-size: 14px; color: white;")
        
        self.ultima = QLabel()
        self.ultima.setAlignment(Qt.AlignCenter)
        self.ultima.setStyleSheet("font-size: 14px; color: white;")

        # Adicionar tudo ao layout sequencial
        layout.addWidget(self.titulo)
        layout.addWidget(self.cidade)
        layout.addWidget(self.status)
        layout.addWidget(self.relogio)
        layout.addWidget(self.caixa1)
        layout.addWidget(self.caixa2)
        layout.addWidget(self.botao_admin)
        layout.addWidget(self.caixa_historico)
        layout.addWidget(self.caixa_anuncio)
        layout.addWidget(self.fonte)
        layout.addWidget(self.ultima)

        self.central = QWidget()
        self.central.setLayout(layout)
        self.setCentralWidget(self.central)
        self.atualizar_cor("#1f7a1f")

    def atualizar_cor(self, cor):
        self.setStyleSheet(f"""
        QMainWindow {{ background-color: {cor}; }}
        QWidget {{ background-color: {cor}; color: white; font-family: Arial; font-size:16px; }}
        QPushButton {{ background-color:#2b2b2b; border:2px solid white; padding:10px; border-radius:12px; font-weight:bold; color: white; }}
        QPushButton:hover {{ background-color:#444444; }}
        QFrame {{ background-color:#2b2b2b; border:2px solid white; border-radius:12px; }}
        """)

    def abrir_janela_emergencia(self, titulo_alerta, mensagem_texto):
        janela_pop = QDialog(self)
        janela_pop.setWindowTitle(f"⚠️ {titulo_alerta.upper()}")
        janela_pop.resize(500, 300)
        janela_pop.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        janela_pop.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; font-family: Arial; }
            QLabel { color: white; }
            QPushButton { background-color: #444444; border: 2px solid white; font-weight: bold; padding: 10px; border-radius: 5px; color: white; }
            QPushButton:hover { background-color: #666666; }
        """)
        
        layout_pop = QVBoxLayout()
        alerta_titulo = QLabel(f"🚨 {titulo_alerta}")
        alerta_titulo.setAlignment(Qt.AlignCenter)
        alerta_titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffcc00;")
        
        info_evento = QLabel(f"<b>Informações Importantes:</b><br><br>{mensagem_texto}")
        info_evento.setWordWrap(True)
        info_evento.setStyleSheet("font-size: 16px;")
        
        btn_ciente = QPushButton("OK, ESTOU CIENTE")
        
        def fechar_e_parar():
            parar_todos_os_sons()
            janela_pop.accept()
            
        btn_ciente.clicked.connect(fechar_e_parar)
        layout_pop.addWidget(alerta_titulo)
        layout_pop.addSpacing(10)
        layout_pop.addWidget(info_evento)
        layout_pop.addSpacing(20)
        layout_pop.addWidget(btn_ciente)
        janela_pop.setLayout(layout_pop)
        janela_pop.exec()

    def detectar_localizacao_por_ip(self):
        try:
            resposta = requests.get("http://ip-api.com/json/?fields=status,city,region", timeout=4)
            if resposta.status_code == 200:
                dados = response = resposta.json()
                if dados.get("status") == "success":
                    cidade_detectada = dados.get("city", "Curitiba")
                    estado_detectado = dados.get("region", "PR")
                    self.cidade.setText(f"📍 {cidade_detectada} - {estado_detectado}")
                    return
            self.cidade.setText("📍 Curitiba - PR")
        except Exception:
            self.cidade.setText("📍 Curitiba - PR")

    def atualizar_relogio(self):
        agora = datetime.now()
        self.relogio.setText("🕒 " + agora.strftime("%d/%m/%Y, %H:%M:%S"))

    def adicionar_ao_historico(self, nome_alerta, hora):
        if not hora or hora == "--:--:--":
            return
        if self.historico_alertas and self.historico_alertas[0].startswith(f"🕒 {hora}"):
            return
        
        registro = f"🕒 {hora} - {nome_alerta}"
        if registro not in self.historico_alertas:
            self.historico_alertas.insert(0, registro)
            if len(self.historico_alertas) > 3:
                self.historico_alertas.pop()
            self.texto_historico.setText("\n".join(self.historico_alertas))

    def processar_mudanca_estado(self, novo_estado, msg_texto, horario_alerta):
        self.estado_atual_internet = novo_estado
        parar_todos_os_sons()
        notif_msg = msg_texto if msg_texto else "Verifique as atualizações do sistema."

        if novo_estado == 0:
            self.atualizar_cor("#1f7a1f")
            self.texto_alerta.setText("Nenhum alerta ativo.")
            self.texto_grave.setText("Nenhum alerta grave.")
            self.texto_mensagem.setText("")
            disparar_notificacao_windows("Central de Alertas", "Painel atualizado: Nenhum alerta ativo.")
            self.adicionar_ao_historico("🟢 Sistema Limpo / Sem Alertas", horario_alerta)
            
        elif novo_estado == 1:
            self.atualizar_cor("#d4b000")
            self.texto_alerta.setText("Central Amarelo (Perigo Potencial)")
            self.texto_mensagem.setText(msg_texto)
            self.texto_grave.setText("Nenhum alerta grave.")
            disparar_notificacao_windows("🟡 Central: Perigo Potencial", notif_msg)
            self.adicionar_ao_historico("🟡 Central: Alerta Amarelo", horario_alerta)
            self.abrir_janela_emergencia("Central: Perigo Potencial", msg_texto)
            
        elif novo_estado == 2:
            self.atualizar_cor("#d46a00")
            self.texto_alerta.setText("Central Laranja (Perigo)")
            self.texto_mensagem.setText(msg_texto)
            self.texto_grave.setText("Nenhum alerta grave.")
            tocar_bipe_curto()
            disparar_notificacao_windows("🟠 Central: Alerta de Perigo", notif_msg)
            self.adicionar_ao_historico("🟠 Central: Alerta Laranja", horario_alerta)
            self.abrir_janela_emergencia("Central: Alerta de Perigo", msg_texto)
            
        elif novo_estado == 3:
            self.atualizar_cor("#b00000")
            self.texto_alerta.setText("Central Vermelho (Grande Perigo)")
            self.texto_mensagem.setText(msg_texto)
            self.texto_grave.setText("🚨 ALERTA GRAVE")
            tocar_alarme_usa()
            disparar_notificacao_windows("🔴 Central: GRANDE PERIGO!", notif_msg)
            self.adicionar_ao_historico("🔴 Central: Alerta Vermelho", horario_alerta)
            self.abrir_janela_emergencia("Central: Grande Perigo", msg_texto)
            
        elif novo_estado == 4:
            self.atualizar_cor("#5e2ca5")
            self.texto_alerta.setText("Central Roxo Severo (Cell Broadcast)")
            self.texto_mensagem.setText(msg_texto)
            self.texto_grave.setText("🚨 ALERTA GRAVE")
            tocar_alarme_iphone()
            disparar_notificacao_windows("🟣 Central: Alerta Severo", notif_msg)
            self.adicionar_ao_historico("🟣 GFS: Cell Broadcast Severo", horario_alerta)
            self.abrir_janela_emergencia("Cell Broadcast Severo", msg_texto)
            
        elif novo_estado == 5:
            self.atualizar_cor("#4b0082")
            self.texto_alerta.setText("Central Roxo Extremo (Cell Broadcast)")
            self.texto_mensagem.setText(msg_texto)
            self.texto_grave.setText("🚨 ALERTA GRAVE")
            tocar_alarme_iphone()
            disparar_notificacao_windows("🟣 Central: ALERTA EXTREMO!", notif_msg)
            self.adicionar_ao_historico("🟣 GFS: Cell Broadcast Extremo", horario_alerta)
            self.abrir_janela_emergencia("Cell Broadcast Extremo", msg_texto)

    def checar_alertas_nuvem(self):
        try:
            resposta = requests.get(URL_SERVIDOR_FIREBASE, timeout=2)
            if resposta.status_code == 200:
                dados = resposta.json()
                if dados and "alerta_atual" in dados:
                    info_servidor = dados["alerta_atual"]
                    novo_est = info_servidor.get("estado", 0)
                    msg_servidor = info_servidor.get("mensagem", "")
                    hora_nuvem = info_servidor.get("horario", "--:--:--")
                    
                    if novo_est != self.estado_atual_internet:
                        self.processar_mudanca_estado(novo_est, msg_servidor, hora_nuvem)
                        self.ultima.setText("Última atualização: " + hora_nuvem)
        except Exception as e:
            print(f"Aguardando conexão Firebase... ({e})")

    def abrir_admin(self):
        janela_login = QDialog(self)
        janela_login.setWindowTitle("Acesso Restrito")
        layout_login = QFormLayout()
        usuario = QLineEdit()
        senha = QLineEdit()
        senha.setEchoMode(QLineEdit.Password)
        layout_login.addRow("Usuário:", usuario)
        layout_login.addRow("Senha:", senha)

        def verificar_login():
            if usuario.text() == "admin" and senha.text() == "123":
                janela_login.accept()
                self.painel_admin()
            else:
                QMessageBox.warning(janela_login, "Erro", "Acesso negado.")

        botao = QPushButton("Entrar")
        botao.clicked.connect(verificar_login)
        layout_login.addWidget(botao)
        janela_login.setLayout(layout_login)
        janela_login.exec()

    def painel_admin(self):
        painel = QDialog(self)
        painel.setWindowTitle("Painel de Controle")
        painel.resize(350, 250)
        
        layout_p = QVBoxLayout()
        form_p = QFormLayout()
        
        self.select_estado = QComboBox()
        self.select_estado.addItem("🟢 Nenhum", 0)
        self.select_estado.addItem("🟡 Amarelo (Perigo Potencial)", 1)
        self.select_estado.addItem("🟠 Laranja (Perigo)", 2)
        self.select_estado.addItem("🔴 Vermelho (Grande Perigo)", 3)
        self.select_estado.addItem("🟣 Roxo Severo (Cell Broadcast)", 4)
        self.select_estado.addItem("🟣 Roxo Extremo (Cell Broadcast)", 5)
        
        self.input_msg = QTextEdit()
        self.input_msg.setPlaceholderText("Escreva os detalhes...")
        
        form_p.addRow("Nível do Alerta:", self.select_estado)
        form_p.addRow("Detalhes:", self.input_msg)
        
        layout_btn = QHBoxLayout()
        btn_emitir = QPushButton("📢 EMITIR")
        btn_emitir.setStyleSheet("background-color: #1f7a1f; color: white; font-weight: bold; padding: 6px;")
        btn_emitir.clicked.connect(lambda: self.enviar_nuvem(painel, apagar=False))
        
        btn_apagar = QPushButton("🗑️ APAGAR AVISOS")
        btn_apagar.setStyleSheet("background-color: #d46a00; color: white; font-weight: bold; padding: 6px;")
        btn_apagar.clicked.connect(lambda: self.enviar_nuvem(painel, apagar=True))
        
        layout_btn.addWidget(btn_emitir)
        layout_btn.addWidget(btn_apagar)
        
        layout_p.addLayout(form_p)
        layout_p.addLayout(layout_btn)
        painel.setLayout(layout_p)
        painel.exec()

    def enviar_nuvem(self, janela_painel, apagar=False):
        hora_str = datetime.now().strftime("%H:%M:%S")
        
        if apagar:
            estado_sel = 0
            msg_sel = ""
        else:
            estado_sel = self.select_estado.currentData()
            msg_sel = self.input_msg.toPlainText() if self.input_msg.toPlainText() else "Aviso oficial."
            
        dados_alerta = {
            "alerta_atual": {
                "estado": estado_sel,
                "mensagem": msg_sel,
                "horario": hora_str
            }
        }
        
        try:
            resposta = requests.put(URL_SERVIDOR_FIREBASE, json=dados_alerta, timeout=3)
            if resposta.status_code == 200:
                QMessageBox.information(janela_painel, "Sucesso", "Nuvem atualizada com sucesso!")
                janela_painel.accept()
                self.checar_alertas_nuvem()
        except Exception as e:
            QMessageBox.critical(janela_painel, "Erro", f"Erro ao conectar na nuvem: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CentralAlertasApp()
    window.show()
    sys.exit(app.exec())