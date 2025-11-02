from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sqlite3
from werkzeug.utils import secure_filename
from functools import wraps
import logging
from contextlib import contextmanager

# Конфигурация
ICON_FOLDER = 'static/icons'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
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

@contextmanager
def db_connection(db_path="apps.db"):
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
app.config['UPLOAD_FOLDER'] = ICON_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

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
    if not name or not path or app_type not in ['game', 'app']:
        return False
    if len(name) > 100 or len(path) > 500:
        return False
    return True

@app.route('/')
def index():
    apps = get_apps()
    games = [app for app in apps if app["type"] == "game"]
    software = [app for app in apps if app["type"] == "app"]
    logs = get_logs()
    return render_template('index.html', games=games, software=software, logs=logs)

@app.route('/run/<app_name>')
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
def add_app():
    if request.method == 'POST':
        app_name = request.form.get('name', '').strip()
        app_path = request.form.get('path', '').strip()
        app_type = request.form.get('type', 'app')
        icon_file = request.files.get('icon')
        
        if not validate_app_data(app_name, app_path, app_type):
            return "Invalid app data", 400
        
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
            return "App name already exists", 400
        except Exception as e:
            logger.error(f"Error adding app: {e}")
            return "Server error", 500

    return render_template('add_app.html')

@app.route('/delete/<app_name>')
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
def edit_app(app_id):
    if request.method == 'POST':
        app_name = request.form.get('name', '').strip()
        app_path = request.form.get('path', '').strip()
        app_type = request.form.get('type', 'app')
        icon_file = request.files.get('icon')
        
        if not validate_app_data(app_name, app_path, app_type):
            return "Invalid app data", 400
        
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
            return "Server error", 500

    with db_connection() as conn:
        app_data = conn.execute(
            "SELECT name, path, type, icon FROM apps WHERE id = ?", (app_id,)
        ).fetchone()
    
    if not app_data:
        return "App not found", 404
    
    return render_template('edit_app.html', 
                         app_id=app_id, 
                         app_name=app_data['name'],
                         app_path=app_data['path'], 
                         app_type=app_data['type'], 
                         icon=app_data['icon'])

@app.route('/log_launch', methods=['POST'])
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
def api_apps():
    return jsonify(get_apps())

@app.route('/clear_logs')
def clear_logs():
    try:
        with db_connection() as conn:
            conn.execute("DELETE FROM launch_logs")
        logger.info("Logs cleared")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return "Server error", 500

@app.route('/api/add_time', methods=['POST'])
def add_time():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No JSON data"}), 400
    
    username = data.get("username")
    seconds = data.get("seconds")
    
    if not username or not isinstance(seconds, int) or seconds < 0:
        return jsonify({"success": False, "error": "Invalid input"}), 400

    try:
        with db_connection("users.db") as conn:
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
def add_balance():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
    
    username = data.get('username')
    amount = data.get('amount', 0)
    
    if not username or not isinstance(amount, int) or amount < 0:
        return jsonify({"status": "error", "message": "Invalid input"}), 400

    try:
        with db_connection("users.db") as conn:
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

@app.errorhandler(404)
def not_found(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {error}")
    return "Internal server error", 500

if __name__ == '__main__':
    app.run(debug=False)