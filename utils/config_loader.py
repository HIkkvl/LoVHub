import configparser
import os
import secrets 

CONFIG_FILE = 'config.ini' # Файл будет лежать в корне проекта

def load_config():
    """
    Читает config.ini и возвращает объект-конфигурацию.
    Если файл не существует, создает его со значениями по умолчанию.
    """
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        print(f"Файл {CONFIG_FILE} не найден. Создаем новый...")
        config['Admin'] = {
            'AdminUsername': 'HIkkvl',
            'AdminPassword': '1478',
            'SECRET_KEY': secrets.token_hex(24) 
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    else:
        config.read(CONFIG_FILE, encoding='utf-8')

    if 'Admin' not in config:
        config['Admin'] = {}
        
    changed = False
    
    if 'AdminUsername' not in config['Admin']:
        config['Admin']['AdminUsername'] = 'admin'
        changed = True
        
    if 'AdminPassword' not in config['Admin']:
        config['Admin']['AdminPassword'] = '1478' 
        changed = True
        
    if 'SECRET_KEY' not in config['Admin']:
        config['Admin']['SECRET_KEY'] = secrets.token_hex(24) 
        changed = True
    

    if changed:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
            
    return config

def get_admin_password():
    """
    Безопасно загружает админ-пароль из config.ini.
    (Используется в main_window.py и server.py)
    """
    config = load_config()
    return config['Admin'].get('AdminPassword', '1478')

def get_admin_username():
    """
    Безопасно загружает админ-логин из config.ini.
    (Используется в server.py для BasicAuth)
    """
    config = load_config()
    return config['Admin'].get('AdminUsername', 'admin')

def get_secret_key():
    """
    Безопасно загружает SECRET_KEY из config.ini.
    (Используется в server.py для CSRF)
    """
    config = load_config()
    return config['Admin'].get('SECRET_KEY', 'default_fallback_key_12345')


def get_kaspi_public_key():
    """Возвращает Kaspi Public Key"""
    try:
        return load_config()['Kaspi']['PublicKey']
    except Exception:
        raise KeyError("В config.ini не найден [Kaspi] -> PublicKey")

def get_kaspi_private_key():
    """Возвращает Kaspi Private Key"""
    try:
        return load_config()['Kaspi']['PrivateKey']
    except Exception:
        raise KeyError("В config.ini не найден [Kaspi] -> PrivateKey")