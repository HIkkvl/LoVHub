# utils/workers.py
from PyQt5.QtCore import QThread, pyqtSignal
import requests

class LoadAppsWorker(QThread):
    """
    Рабочий поток для асинхронной загрузки списка приложений с сервера.
    """
    # Сигнал: (list_of_games, list_of_apps)
    finished = pyqtSignal(list, list) 
    # Сигнал: (error_message_string)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.url = "http://192.168.100.15:5000/api/apps"

    def run(self):
        """Этот код будет выполнен в отдельном потоке"""
        try:
            response = requests.get(self.url, timeout=5)
            response.raise_for_status() # Вызовет ошибку, если сервер ответил 4xx или 5xx
            
            apps_list = response.json()
            
            games = [app for app in apps_list if app.get("type") == "game"]
            apps = [app for app in apps_list if app.get("type") == "app"]
            
            # Отправляем сигнал "успех" с данными
            self.finished.emit(games, apps)
        
        except requests.exceptions.RequestException as e:
            # Отправляем сигнал "ошибка"
            self.error.emit(f"Ошибка загрузки приложений: {e}")
        except Exception as e:
            self.error.emit(f"Неизвестная ошибка в потоке: {e}")
class StatusWorker(QThread):
    """
    Загружает баланс и время пользователя в фоновом режиме.
    """
    # Сигнал: (balance, time_left_seconds)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.url = "http://192.168.100.15:5000/api/get_user_status"

    def run(self):
        try:
            response = requests.get(
                self.url,
                params={"username": self.username},
                timeout=5
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
    """
    Отправляет ("синхронизирует") текущее время на сервер в фоне.
    Это "выстрелил и забыл" воркер, ему не нужен .finished
    """
    error = pyqtSignal(str)

    def __init__(self, username, time_left):
        super().__init__()
        self.username = username
        self.time_left = time_left
        self.url = "http://192.168.100.15:5000/api/update_time"

    def run(self):
        try:
            payload = {"username": self.username, "time_left": self.time_left}
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Отправляем ошибку, чтобы ее можно было залогировать
            self.error.emit(f"Ошибка синхронизации времени: {e}")


class BuyPackageWorker(QThread):
    """
    Покупает пакет времени в фоновом режиме.
    """
    # Сигнал: (new_balance, new_time)
    finished = pyqtSignal(int, int)
    # Сигнал: (error_message)
    error = pyqtSignal(str) 

    def __init__(self, username, seconds, price):
        super().__init__()
        self.username = username
        self.seconds = seconds
        self.price = price
        self.url = "http://192.168.100.15:5000/api/buy_package"

    def run(self):
        try:
            payload = {
                "username": self.username,
                "seconds": self.seconds,
                "price": self.price
            }
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                self.finished.emit(data["new_balance"], data["new_time"])
            else:
                self.error.emit(data.get("message", "Ошибка покупки на сервере"))

        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (Buy): {e}")
            
class AddAppWorker(QThread):
    """
    Добавляет новое приложение на сервер в фоновом режиме.
    """
    finished = pyqtSignal(str) # Сигнал: (app_name)
    error = pyqtSignal(str)    # Сигнал: (error_message)

    def __init__(self, name, path, app_type, icon_filename):
        super().__init__()
        self.url = "http://192.168.100.15:5000/api/add_app"
        self.payload = {
            "name": name,
            "path": path,
            "type": app_type,
            "icon": icon_filename
        }

    def run(self):
        try:
            response = requests.post(self.url, json=self.payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                self.finished.emit(data.get("name", "Неизвестно"))
            else:
                self.error.emit(data.get("message", "Ошибка API при добавлении"))
                
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (AddApp): {e}")


class DeleteAppsWorker(QThread):
    """
    Удаляет ОДНО или НЕСКОЛЬКО приложений на сервере в фоновом режиме.
    """
    # Сигнал: (list_of_deleted_names, list_of_failed_names)
    finished = pyqtSignal(list, list) 
    error = pyqtSignal(str) # Общая ошибка

    def __init__(self, app_names_list):
        super().__init__()
        self.app_names = app_names_list
        self.url = "http://192.168.100.15:5000/api/delete_app"

    def run(self):
        deleted = []
        failed = []
        try:
            for name in self.app_names:
                payload = {"name": name}
                response = requests.post(self.url, json=payload, timeout=3)
                
                if response.status_code == 200 and response.json().get("status") == "success":
                    deleted.append(name)
                else:
                    failed.append(name)
            
            # Отправляем сигнал, что работа завершена
            self.finished.emit(deleted, failed)

        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (DeleteApps): {e}")

class TopUpBalanceWorker(QThread):
    """
    Пополняет баланс пользователя в фоновом режиме.
    """
    # Сигнал: (new_balance)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, username, amount):
        super().__init__()
        self.username = username
        self.amount = amount
        self.url = "http://192.168.100.15:5000/api/add_balance"

    def run(self):
        """Этот код выполняется в отдельном потоке"""
        try:
            payload = {"username": self.username, "amount": self.amount}
            # Это блокирующий вызов, но он в потоке
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                # Отправляем сигнал "успех" с новым балансом
                self.finished.emit(data["new_balance"])
            else:
                self.error.emit(data.get("message", "Ошибка API при пополнении"))
                
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Ошибка сети (TopUp): {e}")