from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging
from contextlib import contextmanager
from flask_cors import CORS

# --- Импорты для защиты админки ---
from flask_basicauth import BasicAuth
from flask_wtf import CSRFProtect, FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from utils.config_loader import get_admin_username, get_admin_password, get_secret_key
# ---------------------------------

DATABASE_NAME = "central_club.db"
ICON_FOLDER = 'static/icons'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    """Создает ВСЕ таблицы в ЕДИНОЙ базе данных central_club.db"""
    with db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('game', 'app')),
            icon TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS launch_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_name TEXT,
            ip_address TEXT,
            user TEXT,
            app_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            balance INTEGER DEFAULT 0,
            time_left INTEGER DEFAULT 0
        )''')

@contextmanager
def db_connection(db_path=DATABASE_NAME):
    """Подключается к ЕДИНОЙ базе данных"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

app = Flask(__name__)
CORS(app) # Разрешаем межсетевые запросы

# --- Настройка Ключа и CSRF ---
app.config['SECRET_KEY'] = get_secret_key()
csrf = CSRFProtect(app)
# -----------------------------

app.config['UPLOAD_FOLDER'] = ICON_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# --- Настройки Basic Auth для веб-админки ---
app.config['BASIC_AUTH_USERNAME'] = get_admin_username()
app.config['BASIC_AUTH_PASSWORD'] = get_admin_password()
app.config['BASIC_AUTH_FORCE'] = True 
app.config['BASIC_AUTH_REALM'] = 'Admin Login' # (Только латиница)
basic_auth = BasicAuth(app)
# -------------------------------------------

os.makedirs(ICON_FOLDER, exist_ok=True)
init_db() 

def save_icon(file):
    if not file or not allowed_file(file.filename):
        return None
    if len(file.read()) > MAX_FILE_SIZE:
        return None
    file.seek(0)
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return filename

def get_apps():
    with db_connection() as conn:
        rows = conn.execute("SELECT id, name, path, type, icon FROM apps").fetchall()
        return [dict(row) for row in rows]

def get_logs(limit=100):
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT computer_name, ip_address, user, app_name, timestamp FROM launch_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

def validate_app_data(name, path, app_type):
    # (Эта функция теперь используется только для API)
    if not name or not path or app_type not in ['game', 'app']:
        return False
    if len(name) > 100 or len(path) > 500:
        return False
    return True

# --- Класс WTForm для /add и /edit ---
class AppForm(FlaskForm):
    name = StringField(
        'Название приложения', 
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    path = StringField(
        'Путь к .exe или URL', 
        validators=[DataRequired(), Length(min=3, max=500)]
    )
    type = SelectField(
        'Тип', 
        choices=[('game', 'Игра'), ('app', 'Приложение')], 
        validators=[DataRequired()]
    )
    icon = FileField(
        'Иконка (png, jpg)', 
        validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения!')]
    )
    submit = SubmitField('Сохранить')
# ----------------------------------


# --- НАЧАЛО ЗАЩИЩЕННЫХ ВЕБ-МАРШРУТОВ (для Админки) ---

@app.route('/')
@basic_auth.required 
def index():
    apps = get_apps()
    games = [app for app in apps if app["type"] == "game"]
    software = [app for app in apps if app["type"] == "app"]
    logs = get_logs()
    return render_template('index.html', games=games, software=software, logs=logs)

@app.route('/run/<app_name>')
@basic_auth.required
def run_app(app_name):
    app_data = next((app for app in get_apps() if app["name"] == app_name), None)
    if not app_data:
        return f"App {app_name} not found", 404
    try:
        os.startfile(app_data["path"])
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error starting app {app_name}: {e}")
        return f"Error: {e}", 500

@app.route('/add', methods=['GET', 'POST'])
@basic_auth.required
def add_app():
    form = AppForm()
    
    if form.validate_on_submit():
        app_name = form.name.data
        app_path = form.path.data
        app_type = form.type.data
        icon_file = form.icon.data
        
        icon_filename = None
        if icon_file:
            icon_filename = save_icon(icon_file)

        try:
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO apps (name, path, type, icon) VALUES (?, ?, ?, ?)",
                    (app_name, app_path, app_type, icon_filename)
                )
            logger.info(f"App added: {app_name}")
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            form.name.errors.append("Приложение с таким именем уже существует")
        except Exception as e:
            logger.error(f"Error adding app: {e}")
            form.submit.errors.append("Ошибка сервера")

    return render_template('add_app.html', form=form)

@app.route('/delete/<app_name>')
@basic_auth.required
def delete_app(app_name):
    try:
        with db_connection() as conn:
            conn.execute("DELETE FROM apps WHERE name = ?", (app_name,))
        logger.info(f"App deleted: {app_name}")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error deleting app {app_name}: {e}")
        return "Server error", 500

@app.route('/edit/<int:app_id>', methods=['GET', 'POST'])
@basic_auth.required
def edit_app(app_id):
    with db_connection() as conn:
        app_data = conn.execute(
            "SELECT name, path, type, icon FROM apps WHERE id = ?", (app_id,)
        ).fetchone()
    if not app_data:
        return "App not found", 404

    form = AppForm()

    if form.validate_on_submit():
        app_name = form.name.data
        app_path = form.path.data
        app_type = form.type.data
        icon_file = form.icon.data
        
        icon_filename = None
        if icon_file:
            icon_filename = save_icon(icon_file)

        try:
            with db_connection() as conn:
                conn.execute(
                    "UPDATE apps SET name = ?, path = ?, type = ?, icon = COALESCE(?, icon) WHERE id = ?",
                    (app_name, app_path, app_type, icon_filename, app_id)
                )
            logger.info(f"App updated: {app_name}")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error updating app: {e}")
            form.submit.errors.append("Ошибка сервера")
    
    elif request.method == 'GET':
        form.name.data = app_data['name']
        form.path.data = app_data['path']
        form.type.data = app_data['type']

    return render_template('edit_app.html', form=form, app_id=app_id)

@app.route('/clear_logs')
@basic_auth.required
def clear_logs():
    try:
        with db_connection() as conn:
            conn.execute("DELETE FROM launch_logs")
        logger.info("Logs cleared")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return "Server error", 500

# --- КОНЕЦ ЗАЩИЩЕННЫХ ВЕБ-МАРШРУТОВ ---


# --- НАЧАЛО API-МАРШРУТОВ (ОТКРЫТЫ для CSRF, но НЕКОТОРЫЕ защищены BasicAuth) ---

@app.route('/log_launch', methods=['POST'])
@csrf.exempt 
def log_launch():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    
    required_fields = ['computer_name', 'ip_address', 'user', 'app_name']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO launch_logs (computer_name, ip_address, user, app_name) VALUES (?, ?, ?, ?)",
                (data['computer_name'], data['ip_address'], data['user'], data['app_name'])
            )
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error logging launch: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/apps')
@csrf.exempt 
def api_apps():
    return jsonify(get_apps())

@app.route('/api/add_time', methods=['POST'])
@basic_auth.required # API Админки
@csrf.exempt 
def add_time():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No JSON data"}), 400
    
    username = data.get("username")
    seconds = data.get("seconds")
    
    if not username or not isinstance(seconds, int) or seconds < 0:
        return jsonify({"success": False, "error": "Invalid input"}), 400

    try:
        with db_connection() as conn:
            result = conn.execute(
                "SELECT time_left FROM users WHERE username = ?", (username,)
            ).fetchone()
            
            current_time = result['time_left'] if result and result['time_left'] is not None else 0
            new_time = current_time + seconds
            
            conn.execute(
                "UPDATE users SET time_left = ? WHERE username = ?", 
                (new_time, username)
            )
            
        return jsonify({"success": True, "new_time": new_time})
    except Exception as e:
        logger.error(f"Error in add_time: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/add_balance', methods=['POST'])
@basic_auth.required # API Админки
@csrf.exempt 
def add_balance():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    
    username = data.get('username')
    amount = data.get('amount', 0)
    
    if not username or not isinstance(amount, int) or amount < 0:
        return jsonify({"status": "error", "message": "Invalid input"}), 400

    try:
        with db_connection() as conn:
            result = conn.execute(
                "SELECT balance FROM users WHERE username = ?", (username,)
            ).fetchone()

            if not result:
                return jsonify({"status": "error", "message": "User not found"}), 404
            
            new_balance = result['balance'] + amount
            conn.execute(
                "UPDATE users SET balance = ? WHERE username = ?", 
                (new_balance, username)
            )
            
            return jsonify({"status": "success", "new_balance": new_balance})
    except Exception as e:
        logger.error(f"Error in add_balance: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/create_user_test', methods=['POST'])
@csrf.exempt 
def create_user_test():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Нужен логин и пароль"}), 400

    hashed_password = generate_password_hash(password)

    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hashed_password)
            )
        return jsonify({"status": "success", "message": f"Юзер {username} создан"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Юзер уже существует"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
@csrf.exempt 
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Нужен логин и пароль"}), 400

    try:
        with db_connection() as conn:
            user = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()

        if not user:
            return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401

        if check_password_hash(user['password_hash'], password):
            return jsonify({"status": "success", "username": username})
        else:
            return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401

    except Exception as e:
        logger.error(f"Ошибка логина: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/add_app', methods=['POST'])
@basic_auth.required # API Админки
@csrf.exempt 
def api_add_app():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    app_name = data.get('name')
    app_path = data.get('path')
    app_type = data.get('type')
    icon_filename = data.get('icon') 
    if not validate_app_data(app_name, app_path, app_type):
         return jsonify({"status": "error", "message": "Invalid app data"}), 400
    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO apps (name, path, type, icon) VALUES (?, ?, ?, ?)",
                (app_name, app_path, app_type, icon_filename)
            )
        logger.info(f"App added via API: {app_name}")
        return jsonify({"status": "success", "name": app_name})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "App name already exists"}), 400
    except Exception as e:
        logger.error(f"Error adding app via API: {e}")
        return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/api/delete_app', methods=['POST'])
@basic_auth.required # API Админки
@csrf.exempt 
def api_delete_app():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"status": "error", "message": "Missing app name"}), 400
    app_name = data.get('name')
    try:
        with db_connection() as conn:
            conn.execute("DELETE FROM apps WHERE name = ?", (app_name,))
        logger.info(f"App deleted via API: {app_name}")
        return jsonify({"status": "success", "name": app_name})
    except Exception as e:
        logger.error(f"Error deleting app {app_name} via API: {e}")
        return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/api/get_user_status', methods=['GET'])
@csrf.exempt 
def api_get_user_status():
    username = request.args.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Username required"}), 400
    try:
        with db_connection() as conn:
            result = conn.execute(
                "SELECT balance, time_left FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not result:
            return jsonify({
                "status": "success", 
                "username": username,
                "balance": 0,
                "time_left": 0
            })
        balance = result['balance'] if result['balance'] is not None else 0
        time_left = result['time_left'] if result['time_left'] is not None else 0
        return jsonify({
            "status": "success", 
            "username": username,
            "balance": balance,
            "time_left": time_left
        })
    except Exception as e:
        logger.error(f"Error getting user status for {username}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update_time', methods=['POST'])
@csrf.exempt 
def api_update_time():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    username = data.get("username")
    time_left = data.get("time_left")
    if not username or not isinstance(time_left, int):
        return jsonify({"status": "error", "message": "Invalid input"}), 400
    try:
        with db_connection() as conn:
            conn.execute(
                "UPDATE users SET time_left = ? WHERE username = ?", 
                (time_left, username)
            )
        return jsonify({"status": "success", "username": username, "time_left": time_left})
    except Exception as e:
        logger.error(f"Error in api_update_time: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/buy_package', methods=['POST'])
@csrf.exempt 
def api_buy_package():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    username = data.get("username")
    seconds_to_add = data.get("seconds")
    price = data.get("price")
    if not all([username, isinstance(seconds_to_add, int), isinstance(price, int)]):
        return jsonify({"status": "error", "message": "Invalid input"}), 400
    try:
        with db_connection() as conn:
            result = conn.execute(
                "SELECT balance, time_left FROM users WHERE username = ?", (username,)
            ).fetchone()
            if not result:
                return jsonify({"status": "error", "message": "User not found"}), 404
            current_balance = result['balance'] if result['balance'] is not None else 0
            current_time = result['time_left'] if result['time_left'] is not None else 0
            if current_balance < price:
                return jsonify({"status": "error", "message": "Недостаточно средств"}), 402
            new_balance = current_balance - price
            new_time = current_time + seconds_to_add
            conn.execute(
                "UPDATE users SET balance = ?, time_left = ? WHERE username = ?", 
                (new_balance, new_time, username)
            )
        return jsonify({
            "status": "success",
            "new_balance": new_balance,
            "new_time": new_time
        })
    except Exception as e:
        logger.error(f"Error in api_buy_package: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- КОНЕЦ API-МАРШРУТОВ ---


@app.errorhandler(404)
def not_found(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {error}")
    return "Internal server error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)