import ctypes
import os
import subprocess
import win32process
import win32con
import win32gui
import win32api
import winreg


def hide_taskbar():
    hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)


def show_taskbar():
    hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)


def kill_explorer():
    os.system("taskkill /f /im explorer.exe")


def start_explorer():
    subprocess.Popen("explorer.exe")


def force_fullscreen_work_area():
    SPI_SETWORKAREA = 0x002F
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = RECT(0, 0, screen_width, screen_height)
    user32.SystemParametersInfoW(SPI_SETWORKAREA, 0, ctypes.byref(rect), 1)


def disable_task_manager():
    try:
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        )
        winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        print("Ошибка блокировки диспетчера задач:", e)


def enable_task_manager():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "DisableTaskMgr")
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass

def get_exe_path_from_pid(pid):
    try:
        h_process = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid
        )
        exe_path = win32process.GetModuleFileNameEx(h_process, 0)
        return exe_path
    except Exception as e:
        print(f"[ERROR] Не удалось получить путь к .exe по PID {pid}: {e}")
        return None