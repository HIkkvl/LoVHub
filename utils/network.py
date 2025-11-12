import socket
import getpass
import requests

# 1. Используем https://
# 2. Указываем IP-адрес сервера (не localhost)
SERVER_URL = "https://192.168.1.101:5000/log_launch"
# --------------------

def send_app_launch_info(app_name):
    info = {
        "computer_name": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "user": getpass.getuser(), 
        "app_name": app_name
    }
    
    try:
        requests.post(
            SERVER_URL, 
            json=info, 
            timeout=2,
            verify=False 
        )
    except Exception as e:
        print(f"Ошибка отправки логов ({SERVER_URL}): {e}")