import subprocess
import time
import sys
import os

try:
    from utils.win_tools import show_taskbar, start_explorer, enable_task_manager
except ImportError:
    print("Ошибка: не удалось импортировать 'utils.win_tools'.")
    print("Убедитесь, что watchdog.py находится в корневой папке.")
    input("Нажмите Enter для выхода...")
    sys.exit(1)

def main(username):
    """
    Главная функция "сторожа".
    Запускает main.py и следит за ним.
    """
    
    main_script = ["py", "main.py", username]
    auth_script = ["py", "auth.py"]
    
    process = None
    
    try:
        print(f"Сторож: Запускаем main.py для пользователя {username}...")
        process = subprocess.Popen(main_script)
        
        while True:
            if process.poll() is None:
                # Процесс жив
                time.sleep(1)
            else:
                # ПРОЦЕСС УПАЛ!
                print(f"Сторож: Обнаружено падение main.py! Код выхода: {process.poll()}")
                break 

    except KeyboardInterrupt:
        print("Сторож: Получен сигнал остановки.")
        if process:
            process.kill()
            
    except Exception as e:
        print(f"Сторож: Критическая ошибка в самом стороже: {e}")
        if process:
            process.kill()
            
    finally:
        # БЛОК ОЧИСТКИ
        print("Сторож: Выполняем гарантированную очистку системы...")
        try:
            enable_task_manager()
            show_taskbar()
            start_explorer()
            print("Сторож: Система восстановлена.")
        except Exception as e:
            print(f"Сторож: Ошибка при очистке: {e}")
            
        print("Сторож: Перезапускаем auth.py...")
        subprocess.Popen(auth_script)
        print("Сторож: Завершение работы.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ошибка: Сторож (watchdog.py) не получил имя пользователя.")
        print("Этот скрипт должен запускаться только из auth.py.")
        input("Нажмите Enter для выхода...")
    else:
        username_arg = sys.argv[1]
        main(username_arg)