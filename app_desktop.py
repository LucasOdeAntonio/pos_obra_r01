import sys
import os

if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(__file__))

def resource_path(relative_path):
    """
    Retorna o caminho absoluto de 'relative_path', seja em desenvolvimento ou quando empacotado.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

import threading
import subprocess
import time
import webview

def start_streamlit():
    home_file = resource_path("home.py")
    subprocess.run([
        "streamlit", "run",
        home_file,
        "--server.headless", "true",
        "--server.address", "0.0.0.0",
        "--server.port", "8501"
    ])

if __name__ == '__main__':
    t = threading.Thread(target=start_streamlit, daemon=True)
    t.start()
    time.sleep(5)  # Ajuste o tempo se necessário
    webview.create_window("Dashboard de Pós-Obra", "http://localhost:8501")
    webview.start()
