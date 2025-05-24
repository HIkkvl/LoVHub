import socket
import getpass
import requests


def send_app_launch_info(app_name):
    info = {
        "computer_name": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "user": getpass.getuser(),
        "app_name": app_name
    }
    try:
        requests.post("http://localhost:5000/log_launch", json=info, timeout=2)
    except Exception as e:
        print("Ошибка отправки логов:", e)
