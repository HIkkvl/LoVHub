
import requests

# --- Настройки ---
SERVER_URL = "https://127.0.0.1:5000" 
USER_TO_CREATE = "123"
PASSWORD_TO_CREATE = "123"
# -----------------

payload = {
    "username": USER_TO_CREATE,
    "password": PASSWORD_TO_CREATE
}

print(f"Пытаюсь создать пользователя '{USER_TO_CREATE}' на {SERVER_URL}...")

try:
    response = requests.post(
        f"{SERVER_URL}/api/create_user_test", 
        json=payload,
        verify=False 
    )
    

    print("\n--- Ответ Сервера ---")
    print(f"Статус-код: {response.status_code}")
    print(f"Ответ: {response.json()}")
    print("---------------------\n")

except requests.exceptions.ConnectionError:
    print(f"ОШИБКА: Не удалось подключиться к {SERVER_URL}.")
    print("Убедись, что server.py запущен (в режиме HTTPS).")
except Exception as e:
    print(f"Произошла неизвестная ошибка: {e}")

input("\nНажмите Enter для выхода...")