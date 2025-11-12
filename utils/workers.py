# utils/workers.py
from PyQt5.QtCore import QThread, pyqtSignal
import requests
import time
import socket # <-- (НОВЫЙ ИМПОРТ)

class LoadAppsWorker(QThread):
    finished = pyqtSignal(list, list) 
    error = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.url = "https://192.168.1.101:5000/api/apps"
    def run(self):
        try:
            response = requests.get(self.url, timeout=5, verify=False)
            response.raise_for_status() 
            apps_list = response.json()
            games = [app for app in apps_list if app.get("type") == "game"]
            apps = [app for app in apps_list if app.get("type") == "app"]
            self.finished.emit(games, apps)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка загрузки приложений: {e}")
        except Exception as e:
            self.error.emit(f"Неизвестная ошибка в потоке: {e}")

class StatusWorker(QThread):
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.url = "https://192.168.1.101:5000/api/get_user_status" 
    def run(self):
        try:
            response = requests.get(
                self.url, params={"username": self.username},
                timeout=5, verify=False 
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                balance = data.get("balance", 0)
                time_left = data.get("time_left", 0)
                self.finished.emit(balance, time_left)
            else:
                self.error.emit(data.get("message", "Неизвестная ошибка API"))
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (Status): {e}")

class SyncTimeWorker(QThread):
    error = pyqtSignal(str)
    def __init__(self, username, time_left):
        super().__init__()
        self.username = username
        self.time_left = time_left
        self.url = "https://192.168.1.101:5000/api/update_time" 
    def run(self):
        try:
            payload = {"username": self.username, "time_left": self.time_left}
            response = requests.post(self.url, json=payload, timeout=5, verify=False) 
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка синхронизации времени: {e}")

class BuyPackageWorker(QThread):
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str) 
    def __init__(self, username, seconds, price, package_name, pc_name):
        super().__init__()
        self.username = username; self.seconds = seconds; self.price = price
        self.package_name = package_name; self.pc_name = pc_name
        self.url = "https://192.168.1.101:5000/api/buy_package"
    def run(self):
        try:
            payload = {
                "username": self.username, "seconds": self.seconds, "price": self.price,
                "package_name": self.package_name, "pc_name": self.pc_name
            }
            response = requests.post(self.url, json=payload, timeout=5, verify=False)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                self.finished.emit(data["new_balance"], data["new_time"])
            else:
                self.error.emit(data.get("message", "Ошибка покупки на сервере"))
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (Buy): {e}")
            
class AddAppWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    def __init__(self, name, path, app_type, icon_filename, admin_user, admin_pass):
        super().__init__()
        self.url = "https://192.168.1.101:5000/api/add_app" 
        self.payload = {
            "name": name, "path": path,
            "type": app_type, "icon": icon_filename
        }
        self.auth_data = (admin_user, admin_pass)
    def run(self):
        try:
            response = requests.post(
                self.url, json=self.payload, timeout=5,
                verify=False, auth=self.auth_data 
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                self.finished.emit(data.get("name", "Неизвестно"))
            else:
                self.error.emit(data.get("message", "Ошибка API при добавлении"))
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (AddApp): {e}")

class DeleteAppsWorker(QThread):
    finished = pyqtSignal(list, list) 
    error = pyqtSignal(str)
    def __init__(self, app_names_list, admin_user, admin_pass):
        super().__init__()
        self.app_names = app_names_list
        self.url = "https://192.168.1.101:5000/api/delete_app" 
        self.auth_data = (admin_user, admin_pass)
    def run(self):
        deleted = []; failed = []
        try:
            for name in self.app_names:
                payload = {"name": name}
                response = requests.post(
                    self.url, json=payload, timeout=3,
                    verify=False, auth=self.auth_data
                )
                if response.status_code == 200 and response.json().get("status") == "success":
                    deleted.append(name)
                else:
                    failed.append(name)
            self.finished.emit(deleted, failed)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (DeleteApps): {e}")

class TopUpBalanceWorker(QThread):
    finished = pyqtSignal(str) 
    error = pyqtSignal(str)
    def __init__(self, username, amount):
        super().__init__()
        self.username = username
        self.amount = amount
        self.url = "https://192.168.1.101:5000/api/create_payment"
    def run(self):
        try:
            payload = {"username": self.username, "amount": self.amount}
            response = requests.post(
                self.url, 
                json=payload, 
                timeout=10, 
                verify=False
            ) 
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success" and data.get("payment_url"):
                self.finished.emit(data["payment_url"]) 
            else:
                self.error.emit(data.get("message", "Ошибка API при создании счета"))
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (CreatePayment): {e}")

class HeartbeatWorker(QThread):
    error = pyqtSignal(str)
    def __init__(self, pc_name, status, user=None, time_left=None):
        super().__init__()
        self.url = "https://192.168.1.101:5000/api/heartbeat"
        self.payload = {
            "pc_name": pc_name, "status": status,
            "user": user, "time_left": time_left 
        }
    def run(self):
        try:
            requests.post(
                self.url, json=self.payload, timeout=5, verify=False 
            )
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка Heartbeat: {e}")

class CoreTimerWorker(QThread):
    tick = pyqtSignal(int)
    time_up = pyqtSignal()
    def __init__(self, initial_time_left):
        super().__init__()
        self.time_left = initial_time_left
        self.running = True
    def run(self):
        while self.time_left > 0 and self.running:
            time.sleep(1)
            if not self.running: break 
            self.time_left -= 1
            self.tick.emit(self.time_left)
        if self.running:
            self.time_up.emit()
    def stop(self):
        self.running = False

class HeartbeatLoopWorker(QThread):
    trigger = pyqtSignal()
    def __init__(self, interval_sec=15):
        super().__init__()
        self.interval = interval_sec
        self.running = True
    def run(self):
        while self.running:
            time.sleep(self.interval)
            if self.running:
                self.trigger.emit()
    def stop(self):
        self.running = False

class SyncLoopWorker(QThread):
    trigger = pyqtSignal()
    def __init__(self, interval_sec=5):
        super().__init__()
        self.interval = interval_sec
        self.running = True
    def run(self):
        while self.running:
            time.sleep(self.interval)
            if self.running:
                self.trigger.emit()
    def stop(self):
        self.running = False

# --- (НОВЫЙ КЛАСС ДЛЯ ЛОГОВ) ---
class LogLaunchWorker(QThread):
    """ (НОВЫЙ КЛАСС) Отправляет лог о запуске в фоне. """
    error = pyqtSignal(str)
    
    def __init__(self, pc_name, user, app_name):
        super().__init__()
        self.url = "192.168.1.101:5000/log_launch"
        self.payload = {
            "computer_name": pc_name,
            # (Мы получаем IP здесь, чтобы не "замораживать" GUI)
            "ip_address": socket.gethostbyname(socket.gethostname()), 
            "user": user,
            "app_name": app_name
        }

    def run(self):
        try:
            requests.post(
                self.url, 
                json=self.payload, 
                timeout=5, 
                verify=False
            )
            # (Нам не важен ответ, главное - отправить)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка LogLaunch: {e}")
# --- КОНЕЦ НОВОГО КЛАССА ---