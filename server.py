from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import os
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging
from contextlib import contextmanager
from flask_cors import CORS
import ssl
import sys
from datetime import datetime, timedelta 

from flask_basicauth import BasicAuth 
from flask_login import (LoginManager, UserMixin, login_user, 
                         logout_user, login_required, current_user)

from flask_wtf import CSRFProtect, FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, SubmitField, PasswordField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, Optional

from utils.config_loader import (
    get_admin_username, get_admin_password, get_secret_key,
    get_kaspi_public_key, get_kaspi_private_key 
)

import json
import requests
import time
import hashlib
import hmac
import base64

KASPI_API_URL = "https://api.kaspi.kz/v2/invoices" 
KASPI_SIGNATURE_HEADER = "X-Signature" 

DATABASE_NAME = "central_club.db"
ICON_FOLDER = 'static/icons'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_kaspi_signature(payload_string, private_key):
    try:
        private_key_bytes = private_key.encode('utf-8')
        payload_bytes = payload_string.encode('utf-8')
        signature = hmac.new(private_key_bytes, payload_bytes, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка создания подписи Kaspi: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    """Создает ВСЕ таблицы в ЕДИНОЙ базе данных central_club.db"""
    with db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, path TEXT NOT NULL, type TEXT NOT NULL CHECK(type IN ('game', 'app')), icon TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS launch_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, computer_name TEXT, ip_address TEXT, user TEXT, app_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, balance INTEGER DEFAULT 0, time_left INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS computers (id INTEGER PRIMARY KEY AUTOINCREMENT, pc_name TEXT NOT NULL UNIQUE, ip_address TEXT, status TEXT DEFAULT 'Отключен', current_user TEXT, last_heartbeat DATETIME, time_remaining INTEGER DEFAULT 0, session_name TEXT, session_start_time DATETIME, session_end_time DATETIME, display_name TEXT )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, type TEXT NOT NULL CHECK(type IN ('kaspi_topup', 'package_purchase', 'admin_topup')), username TEXT, amount INTEGER NOT NULL, order_id TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_text TEXT, 
            price_common INTEGER DEFAULT 0,
            price_vip INTEGER DEFAULT 0,
            schedule_text TEXT,
            schedule_icons TEXT,
            is_active BOOLEAN DEFAULT 0 
        )''')

@contextmanager
def db_connection(db_path=DATABASE_NAME):
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
CORS(app) 
app.config['SECRET_KEY'] = get_secret_key()
csrf = CSRFProtect(app)
app.config['UPLOAD_FOLDER'] = ICON_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' 
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'error' 
app.config['BASIC_AUTH_USERNAME'] = get_admin_username()
app.config['BASIC_AUTH_PASSWORD'] = get_admin_password()
app.config['BASIC_AUTH_REALM'] = 'Launcher API Login' 
basic_auth = BasicAuth(app)
os.makedirs(ICON_FOLDER, exist_ok=True)
init_db() 

def save_icon(file):
    if not file or not allowed_file(file.filename): return None
    if len(file.read()) > MAX_FILE_SIZE: return None
    file.seek(0)
    filename = secure_filename(file.filename); file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path); return filename
def get_apps():
    with db_connection() as conn:
        rows = conn.execute("SELECT id, name, path, type, icon FROM apps").fetchall()
        return [dict(row) for row in rows]
def get_logs(limit=100):
    with db_connection() as conn:
        rows = conn.execute(
            """SELECT 
                   T1.ip_address, T1.user, T1.app_name, T1.timestamp,
                   COALESCE(T2.display_name, T1.computer_name) as computer_name_to_display
               FROM launch_logs AS T1
               LEFT JOIN computers AS T2 ON T1.computer_name = T2.pc_name
               ORDER BY T1.timestamp DESC 
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
def get_users(search_term=None):
    with db_connection() as conn:
        if search_term:
            query = "SELECT id, username, balance, time_left FROM users WHERE username LIKE ? ORDER BY username"; params = (f'%{search_term}%',)
        else:
            query = "SELECT id, username, balance, time_left FROM users ORDER BY username"; params = ()
        rows = conn.execute(query, params).fetchall(); return [dict(row) for row in rows]
def get_dashboard_stats():
    try:
        with db_connection() as conn:
            users_count = conn.execute("SELECT COUNT(id) FROM users").fetchone()[0]; apps_count = conn.execute("SELECT COUNT(id) FROM apps").fetchone()[0]
            total_computers = conn.execute("SELECT COUNT(id) FROM computers").fetchone()[0]
            active_threshold = datetime.now() - timedelta(seconds=60)
            enabled_computers = conn.execute("SELECT COUNT(id) FROM computers WHERE last_heartbeat > ?", (active_threshold,)).fetchone()[0]
            disabled_computers = total_computers - enabled_computers
            top_app = conn.execute("SELECT app_name, COUNT(app_name) as count FROM launch_logs GROUP BY app_name ORDER BY count DESC LIMIT 1").fetchone()
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            revenue_total = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE timestamp >= ? AND type IN ('kaspi_topup', 'admin_topup')", (today_start,)).fetchone()[0]
            revenue_packages = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE timestamp >= ? AND type = 'package_purchase'", (today_start,)).fetchone()[0]
            revenue_kaspi = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE timestamp >= ? AND type = 'kaspi_topup'", (today_start,)).fetchone()[0]
        return {
            "users_count": users_count, "apps_count": apps_count, "total_computers": total_computers, "enabled_computers": enabled_computers, "disabled_computers": disabled_computers,
            "top_app_name": top_app['app_name'] if top_app else "N/A", "top_app_count": top_app['count'] if top_app else 0,
            "revenue_total": revenue_total, "revenue_packages": revenue_packages, "revenue_kaspi": revenue_kaspi
        }
    except Exception as e:
        logger.error(f"Ошибка сбора статистики: {e}")
        return {"users_count": 0, "apps_count": 0, "total_computers": 0, "enabled_computers": 0, "disabled_computers": 0, "top_app_name": "Error", "top_app_count": 0, "revenue_total": 0, "revenue_packages": 0, "revenue_kaspi": 0}
def validate_app_data(name, path, app_type):
    if not name or not path or app_type not in ['game', 'app']: return False
    if len(name) > 100 or len(path) > 500: return False
    return True

# --- Формы WTForms ---
class AppForm(FlaskForm):
    name = StringField('Название приложения', validators=[DataRequired(), Length(min=2, max=100)])
    path = StringField('Путь к .exe или URL', validators=[DataRequired(), Length(min=3, max=500)])
    type = SelectField('Тип', choices=[('game', 'Игра'), ('app', 'Приложение')], validators=[DataRequired()])
    icon = FileField('Иконка (png, jpg)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения!')])
    submit = SubmitField('Сохранить')
class RegisterUserForm(FlaskForm):
    username = StringField('Имя пользователя (Логин)', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=4, max=100)])
    confirm = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    submit = SubmitField('Создать пользователя')
class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = 1; self.username = username; self.password = get_admin_password()
    def check_password(self, password_input):
        return self.password == password_input
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class TariffForm(FlaskForm):
    """ (НОВАЯ ФОРМА) Для создания/редактирования тарифа """
    name = StringField('Название тарифа (напр. "1 час")', validators=[DataRequired()])
    duration_text = StringField('Длительность (напр. "1 час")', validators=[DataRequired()])
    price_common = IntegerField('Цена (Общий зал)', validators=[DataRequired()])
    price_vip = IntegerField('Цена (VIP зал)', validators=[DataRequired()])
    schedule_text = StringField('График продажи (напр. "Пн-Чт 09:00-18:00")', validators=[Optional()])
    schedule_icons = StringField('Иконки (sun, moon)', validators=[Optional()])
    is_active = BooleanField('Активная скидка? (Желтая карточка)')
    submit = SubmitField('Сохранить')


@login_manager.user_loader
def load_user(user_id):
    return AdminUser(get_admin_username())


# --- ВЕБ-МАРШРУТЫ (все на @login_required) ---
@app.route('/')
@login_required 
def index():
    stats = get_dashboard_stats()
    search_term = request.args.get('search', '') 
    error_pcs = []
    try:
        with db_connection() as conn:
            active_threshold = datetime.now() - timedelta(seconds=60)
            rows = conn.execute(
                """SELECT pc_name, display_name, last_heartbeat 
                   FROM computers 
                   WHERE last_heartbeat IS NULL OR last_heartbeat < ?
                   ORDER BY pc_name""", 
                (active_threshold,)
            )
            for row in rows:
                pc_data = dict(row)
                pc_data['name_to_display'] = pc_data['display_name'] or pc_data['pc_name']
                if pc_data['last_heartbeat']:
                    pc_data['last_seen'] = datetime.fromisoformat(pc_data['last_heartbeat']).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    pc_data['last_seen'] = 'Никогда'
                error_pcs.append(pc_data)
    except Exception as e:
        logger.error(f"Ошибка получения списка проблемных ПК: {e}")
        flash(f"Ошибка получения списка проблемных ПК: {e}", "error")
    return render_template('index.html', stats=stats, search_term=search_term, error_pcs=error_pcs)

@app.route('/computers')
@login_required
def computers_page():
    search_term = request.args.get('search', ''); computers_list = []
    try:
        with db_connection() as conn:
            rows = conn.execute("SELECT * FROM computers ORDER BY pc_name")
            for row in rows:
                pc_data = dict(row); last_beat = pc_data.get('last_heartbeat')
                if not last_beat:
                    pc_data['status'] = "Неизвестно"; pc_data['status_class'] = "status-offline" ; pc_data['current_user'] = "-"
                else:
                    time_diff = datetime.now() - datetime.fromisoformat(last_beat)
                    if time_diff.total_seconds() > 60:
                        pc_data['status'] = "Отключен"; pc_data['status_class'] = "status-offline"; pc_data['current_user'] = "-"
                    else:
                        if pc_data['current_user']:
                            pc_data['status'] = "Используется"; pc_data['status_class'] = "status-active"
                        else:
                            pc_data['status'] = "Активен"; pc_data['status_class'] = "status-active"
                pc_data['client'] = pc_data['current_user'] if pc_data['current_user'] else "-"
                time_sec = pc_data.get('time_remaining')
                if time_sec is not None and time_sec > 0:
                    hours = time_sec // 3600; mins = (time_sec % 3600) // 60
                    pc_data['remaining'] = f"{hours}ч {mins}м"
                else:
                    pc_data['remaining'] = "-"
                if pc_data['status'] != "Отключен" and pc_data.get('session_name'):
                    pc_data['session'] = pc_data['session_name']; pc_data['start'] = datetime.fromisoformat(pc_data['session_start_time']).strftime('%H:%M'); pc_data['end'] = datetime.fromisoformat(pc_data['session_end_time']).strftime('%H:%M')
                else:
                    pc_data['session'] = "-"; pc_data['start'] = "-"; pc_data['end'] = "-"
                if pc_data['display_name']:
                    pc_data['name_to_display'] = pc_data['display_name']
                else:
                    pc_data['name_to_display'] = pc_data['pc_name']
                pc_data['version'] = "0.1221"; computers_list.append(pc_data)
    except Exception as e:
        logger.error(f"Ошибка get_computers: {e}"); flash(f"Ошибка загрузки списка ПК: {e}", "error")
    return render_template('computers.html', computers=computers_list, search_term=search_term)
@app.route('/clients')
@login_required
def clients_page():
    search_term = request.args.get('search', '') 
    users = get_users(search_term=search_term) 
    return render_template('clients.html', users=users, search_term=search_term)
@app.route('/logs')
@login_required
def logs_page():
    logs = get_logs()
    search_term = request.args.get('search', '')
    return render_template('logs.html', logs=logs, search_term=search_term)

@app.route('/tariffs', methods=['GET', 'POST'])
@login_required
def tariffs_page():
    form = TariffForm()
    
    if form.validate_on_submit():
        try:
            with db_connection() as conn:
                conn.execute(
                    """INSERT INTO tariffs 
                       (name, duration_text, price_common, price_vip, 
                        schedule_text, schedule_icons, is_active) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        form.name.data, form.duration_text.data,
                        form.price_common.data, form.price_vip.data,
                        form.schedule_text.data, form.schedule_icons.data,
                        form.is_active.data
                    )
                )
            flash(f'Тариф "{form.name.data}" успешно создан!', 'success')
            return redirect(url_for('tariffs_page'))
        except Exception as e:
            logger.error(f"Ошибка создания тарифа: {e}")
            flash(f"Ошибка сервера: {e}", 'error')

    tariffs = []
    try:
        with db_connection() as conn:
            rows = conn.execute("SELECT * FROM tariffs ORDER BY price_common").fetchall()
            tariffs = [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка загрузки тарифов: {e}")
        flash(f"Ошибка загрузки тарифов: {e}", 'error')

    return render_template('tariffs.html', form=form, tariffs=tariffs)

@app.route('/apps', methods=['GET', 'POST'])
@login_required
def apps_page():
    form = AppForm()
    if form.validate_on_submit(): 
        app_name = form.name.data; app_path = form.path.data; app_type = form.type.data
        icon_file = form.icon.data; icon_filename = None
        if icon_file: icon_filename = save_icon(icon_file)
        try:
            with db_connection() as conn:
                conn.execute("INSERT INTO apps (name, path, type, icon) VALUES (?, ?, ?, ?)", (app_name, app_path, app_type, icon_filename))
            logger.info(f"App added: {app_name}"); flash(f'Приложение "{app_name}" успешно добавлено!', 'success')
            return redirect(url_for('apps_page')) 
        except sqlite3.IntegrityError:
            form.name.errors.append("Приложение с таким именем уже существует")
        except Exception as e:
            logger.error(f"Error adding app: {e}"); form.submit.errors.append("Ошибка сервера")
    apps = get_apps()
    games = [app for app in apps if app["type"] == "game"]
    software = [app for app in apps if app["type"] == "app"]
    search_term = request.args.get('search', '')
    return render_template('apps.html', games=games, software=software, form=form, search_term=search_term)
@app.route('/run/<app_name>')
@login_required
def run_app(app_name):
    app_data = next((app for app in get_apps() if app["name"] == app_name), None)
    if not app_data: return f"App {app_name} not found", 404
    try:
        os.startfile(app_data["path"]); return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error starting app {app_name}: {e}"); return f"Error: {e}", 500
@app.route('/delete/<app_name>')
@login_required
def delete_app(app_name):
    try:
        with db_connection() as conn: conn.execute("DELETE FROM apps WHERE name = ?", (app_name,))
        logger.info(f"App deleted: {app_name}"); return redirect(url_for('apps_page')) 
    except Exception as e:
        logger.error(f"Error deleting app {app_name}: {e}"); return "Server error", 500
@app.route('/edit/<int:app_id>', methods=['GET', 'POST'])
@login_required
def edit_app(app_id):
    with db_connection() as conn:
        app_data = conn.execute("SELECT name, path, type, icon FROM apps WHERE id = ?", (app_id,)).fetchone()
    if not app_data: return "App not found", 404
    form = AppForm()
    if form.validate_on_submit():
        app_name = form.name.data; app_path = form.path.data; app_type = form.type.data
        icon_file = form.icon.data; icon_filename = None
        if icon_file: icon_filename = save_icon(icon_file)
        try:
            with db_connection() as conn:
                conn.execute("UPDATE apps SET name = ?, path = ?, type = ?, icon = COALESCE(?, icon) WHERE id = ?", (app_name, app_path, app_type, icon_filename, app_id))
            logger.info(f"App updated: {app_name}"); return redirect(url_for('apps_page')) 
        except Exception as e:
            logger.error(f"Error updating app: {e}"); form.submit.errors.append("Ошибка сервера")
    elif request.method == 'GET':
        form.name.data = app_data['name']; form.path.data = app_data['path']; form.type.data = app_data['type']
    return render_template('edit_app.html', form=form, app_id=app_id)
@app.route('/edit_pc/<int:pc_id>', methods=['GET', 'POST'])
@login_required
def edit_pc(pc_id):
    if request.method == 'POST':
        new_name = request.form.get('display_name')
        if not new_name: flash("Имя не может быть пустым", "error")
        else:
            try:
                with db_connection() as conn: conn.execute("UPDATE computers SET display_name = ? WHERE id = ?", (new_name, pc_id))
                logger.info(f"ПК с ID {pc_id} переименован в '{new_name}'"); flash(f"ПК успешно переименован в '{new_name}'", "success")
                return redirect(url_for('computers_page'))
            except Exception as e:
                logger.error(f"Ошибка переименования ПК: {e}"); flash(f"Ошибка сервера: {e}", "error")
    try:
        with db_connection() as conn:
            pc_data = conn.execute("SELECT id, pc_name, display_name FROM computers WHERE id = ?", (pc_id,)).fetchone()
        if not pc_data: return "ПК не найден", 404
        return render_template('edit_pc.html', pc=pc_data)
    except Exception as e:
        logger.error(f"Ошибка загрузки ПК: {e}"); return "Ошибка сервера", 500
@app.route('/clear_logs')
@login_required
def clear_logs():
    try:
        with db_connection() as conn: conn.execute("DELETE FROM launch_logs")
        logger.info("Logs cleared"); return redirect(url_for('logs_page')) 
    except Exception as e:
        logger.error(f"Error clearing logs: {e}"); return "Server error", 500
@app.route('/web/add_balance', methods=['POST'])
@login_required 
def web_add_balance():
    try:
        username = request.form['username']; amount = int(request.form['amount'])
        if amount <= 0: flash('Сумма должна быть положительной', 'error'); return redirect(url_for('clients_page'))
        with db_connection() as conn:
            result = conn.execute("SELECT balance FROM users WHERE username = ?", (username,)).fetchone()
            if not result: flash(f'Пользователь "{username}" не найден', 'error'); return redirect(url_for('clients_page'))
            new_balance = (result['balance'] if result['balance'] is not None else 0) + amount
            conn.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
            conn.execute("INSERT INTO transactions (type, username, amount) VALUES (?, ?, ?)", ('admin_topup', username, amount))
        logger.info(f"Админ пополнил баланс {username} на {amount} тг"); flash(f'Баланс {username} пополнен на {amount} тг', 'success')
        return redirect(url_for('clients_page'))
    except Exception as e:
        logger.error(f"Ошибка web_add_balance: {e}"); flash(f"Ошибка сервера: {e}", 'error'); return redirect(url_for('clients_page'))
@app.route('/web/add_time', methods=['POST'])
@login_required
def web_add_time():
    try:
        username = request.form['username']; minutes = int(request.form['minutes']); seconds_to_add = minutes * 60
        if seconds_to_add <= 0: flash('Время должно быть положительным', 'error'); return redirect(url_for('clients_page'))
        with db_connection() as conn:
            result = conn.execute("SELECT time_left FROM users WHERE username = ?", (username,)).fetchone()
            if not result:
                flash(f'Пользователь "{username}" не найден', 'error'); return redirect(url_for('clients_page'))
            current_time_total = (result['time_left'] if result['time_left'] is not None else 0)
            new_time_total = current_time_total + seconds_to_add
            conn.execute("UPDATE users SET time_left = ? WHERE username = ?", (new_time_total, username))
            pc = conn.execute("SELECT id FROM computers WHERE current_user = ?", (username,)).fetchone()
            if pc:
                new_session_end_time = datetime.now() + timedelta(seconds=new_time_total)
                conn.execute(
                    """UPDATE computers SET time_remaining = ?, session_end_time = ? 
                       WHERE current_user = ?""", 
                    (new_time_total, new_session_end_time, username)
                )
                logger.info(f"Также обновлена АКТИВНАЯ сессия для {username}.")
        logger.info(f"Админ добавил {minutes} минут пользователю {username}"); flash(f'{minutes} минут добавлено пользователю {username}', 'success')
        return redirect(url_for('clients_page'))
    except Exception as e:
        logger.error(f"Ошибка web_add_time: {e}"); flash(f"Ошибка сервера: {e}", 'error'); return redirect(url_for('clients_page'))
@app.route('/register_client', methods=['GET', 'POST'])
@login_required
def register_client_page():
    form = RegisterUserForm()
    if form.validate_on_submit():
        try:
            username = form.username.data; password = form.password.data; hashed_password = generate_password_hash(password)
            with db_connection() as conn: conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            flash(f'Пользователь "{username}" успешно создан!', 'success'); logger.info(f"Админ создал нового пользователя: {username}")
            return redirect(url_for('clients_page')) 
        except sqlite3.IntegrityError:
            form.username.errors.append(f'Ошибка: Пользователь "{username}" уже существует.')
        except Exception as e:
            logger.error(f"Ошибка web_create_user: {e}"); flash(f"Ошибка сервера: {e}", 'error')
    return render_template('register_client.html', form=form)
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if request.method == 'POST':
        try:
            with db_connection() as conn:
                user_to_delete = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
                if user_to_delete and user_to_delete['username'] == get_admin_username():
                    flash('Вы не можете удалить главного администратора.', 'error'); return redirect(url_for('clients_page'))
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            logger.info(f"Админ удалил пользователя ID {user_id}"); flash('Пользователь успешно удален.', 'success')
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя: {e}"); flash(f"Ошибка сервера: {e}", 'error')
    return redirect(url_for('clients_page'))
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        username_from_config = get_admin_username(); admin = AdminUser(username_from_config)
        if (form.username.data == admin.username and admin.check_password(form.password.data)):
            login_user(admin); logger.info(f"Администратор {admin.username} вошел в систему.")
            next_page = request.args.get('next'); return redirect(next_page or url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    return render_template('admin_login.html', form=form)
@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user(); flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('admin_login'))
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.route('/edit_tariff/<int:tariff_id>', methods=['POST'])
@login_required
def edit_tariff(tariff_id):
    """ (НОВЫЙ МАРШРУТ) Обрабатывает POST-запрос от модального окна 'Изменить тариф' """
    form = TariffForm()
    
    if form.validate_on_submit():
        try:
            with db_connection() as conn:
                conn.execute(
                    """UPDATE tariffs SET 
                       name = ?, duration_text = ?, price_common = ?, price_vip = ?, 
                       schedule_text = ?, schedule_icons = ?, is_active = ?
                       WHERE id = ?""",
                    (
                        form.name.data, form.duration_text.data,
                        form.price_common.data, form.price_vip.data,
                        form.schedule_text.data, form.schedule_icons.data,
                        form.is_active.data,
                        tariff_id
                    )
                )
            flash(f'Тариф "{form.name.data}" успешно обновлен!', 'success')
        except Exception as e:
            logger.error(f"Ошибка обновления тарифа: {e}")
            flash(f"Ошибка сервера: {e}", 'error')
            
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле '{getattr(form, field).label.text}': {error}", 'error')

    return redirect(url_for('tariffs_page'))


@app.route('/delete_tariff/<int:tariff_id>', methods=['POST'])
@login_required
def delete_tariff(tariff_id):
    """ (НОВЫЙ МАРШРУТ) Удаляет тариф """
    try:
        with db_connection() as conn:
            conn.execute("DELETE FROM tariffs WHERE id = ?", (tariff_id,))
        flash('Тариф успешно удален.', 'success')
    except Exception as e:
        logger.error(f"Ошибка удаления тарифа: {e}")
        flash(f"Ошибка сервера: {e}", 'error')
            
    return redirect(url_for('tariffs_page'))

# --- НАЧАЛО API-МАРШРУТОВ ---

@app.route('/log_launch', methods=['POST'])
@csrf.exempt 
def log_launch():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    required_fields = ['computer_name', 'ip_address', 'user', 'app_name']
    if not all(field in data for field in required_fields): return jsonify({"status": "error", "message": "Missing required fields"}), 400
    try:
        with db_connection() as conn:
            conn.execute("INSERT INTO launch_logs (computer_name, ip_address, user, app_name) VALUES (?, ?, ?, ?)", (data['computer_name'], data['ip_address'], data['user'], data['app_name']))
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error logging launch: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/apps')
@csrf.exempt 
def api_apps():
    return jsonify(get_apps())
@app.route('/api/login', methods=['POST'])
@csrf.exempt 
def api_login():
    data = request.get_json(); username = data.get('username'); password = data.get('password')
    if not username or not password: return jsonify({"status": "error", "message": "Нужен логин и пароль"}), 400
    try:
        with db_connection() as conn:
            user = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if not user: return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401
        if check_password_hash(user['password_hash'], password):
            return jsonify({"status": "success", "username": username})
        else:
            return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401
    except Exception as e:
        logger.error(f"Ошибка логина: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/get_user_status', methods=['GET'])
@csrf.exempt 
def api_get_user_status():
    username = request.args.get('username')
    if not username: return jsonify({"status": "error", "message": "Username required"}), 400
    try:
        with db_connection() as conn:
            result = conn.execute("SELECT balance, time_left FROM users WHERE username = ?", (username,)).fetchone()
        if not result:
            return jsonify({"status": "success", "username": username, "balance": 0, "time_left": 0})
        balance = result['balance'] if result['balance'] is not None else 0
        time_left = result['time_left'] if result['time_left'] is not None else 0
        return jsonify({"status": "success", "username": username, "balance": balance, "time_left": time_left})
    except Exception as e:
        logger.error(f"Error getting user status for {username}: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/update_time', methods=['POST'])
@csrf.exempt 
def api_update_time():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    username = data.get("username"); time_left = data.get("time_left")
    if not username or not isinstance(time_left, int): return jsonify({"status": "error", "message": "Invalid input"}), 400
    try:
        with db_connection() as conn:
            conn.execute("UPDATE users SET time_left = ? WHERE username = ?", (time_left, username))
        return jsonify({"status": "success", "username": username, "time_left": time_left})
    except Exception as e:
        logger.error(f"Error in api_update_time: {e}"); return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/buy_package', methods=['POST'])
@csrf.exempt 
def api_buy_package():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    username = data.get("username"); seconds_to_add = data.get("seconds"); price = data.get("price"); package_name = data.get("package_name"); pc_name = data.get("pc_name")
    if not all([username, isinstance(seconds_to_add, int), isinstance(price, int), package_name, pc_name]):
        return jsonify({"status": "error", "message": "Invalid input (отсутствует username, seconds, price, package_name или pc_name)"}), 400
    try:
        with db_connection() as conn:
            result = conn.execute("SELECT balance, time_left FROM users WHERE username = ?", (username,)).fetchone()
            if not result: return jsonify({"status": "error", "message": "User not found"}), 404
            current_balance = result['balance'] if result['balance'] is not None else 0
            current_time = result['time_left'] if result['time_left'] is not None else 0
            if current_balance < price: return jsonify({"status": "error", "message": "Недостаточно средств"}), 402
            new_balance = current_balance - price; new_time = current_time + seconds_to_add
            conn.execute("UPDATE users SET balance = ?, time_left = ? WHERE username = ?", (new_balance, new_time, username))
            conn.execute("INSERT INTO transactions (type, username, amount) VALUES (?, ?, ?)", ('package_purchase', username, price))
            start_time = datetime.now(); end_time = start_time + timedelta(seconds=seconds_to_add)
            cursor = conn.execute("""UPDATE computers SET status = ?, current_user = ?, time_remaining = ?, session_name = ?, session_start_time = ?, session_end_time = ?, last_heartbeat = ? WHERE pc_name = ?""", ("Используется", username, new_time, package_name, start_time, end_time, start_time, pc_name ))
            if cursor.rowcount == 0:
                conn.execute("""INSERT INTO computers (pc_name, status, current_user, time_remaining, session_name, session_start_time, session_end_time, last_heartbeat, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT ip_address FROM computers WHERE pc_name = ?))""", (pc_name, "Используется", username, new_time, package_name, start_time, end_time, start_time, pc_name ))
        return jsonify({"status": "success", "new_balance": new_balance, "new_time": new_time})
    except Exception as e:
        logger.error(f"Error in api_buy_package: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/heartbeat', methods=['POST'])
@csrf.exempt 
def api_heartbeat():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    pc_name = data.get('pc_name'); status = data.get('status'); user = data.get('user'); time_left = data.get('time_left'); ip = request.remote_addr
    if not pc_name or not status: return jsonify({"status": "error", "message": "Missing pc_name or status"}), 400
    try:
        with db_connection() as conn:
            cursor = conn.execute("""UPDATE computers SET ip_address = ?, status = ?, current_user = ?, last_heartbeat = ?, time_remaining = ? WHERE pc_name = ?""", (ip, status, user, datetime.now(), time_left, pc_name))
            if cursor.rowcount == 0:
                conn.execute("""INSERT INTO computers (pc_name, ip_address, status, current_user, last_heartbeat, time_remaining) VALUES (?, ?, ?, ?, ?, ?)""", (pc_name, ip, status, user, datetime.now(), time_left))
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Ошибка Heartbeat: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/app_details/<int:app_id>')
@login_required 
def api_app_details(app_id):
    try:
        with db_connection() as conn:
            app_data = conn.execute("SELECT name, path, type, icon FROM apps WHERE id = ?", (app_id,)).fetchone()
        if not app_data: return jsonify({"status": "error", "message": "App not found"}), 404
        return jsonify({"status": "success", "data": dict(app_data)})
    except Exception as e:
        logger.error(f"Ошибка получения деталей приложения: {e}"); return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/tariff_details/<int:tariff_id>')
@login_required 
def api_tariff_details(tariff_id):
    """ (НОВЫЙ API) Отдает детали тарифа в формате JSON """
    try:
        with db_connection() as conn:
            tariff_data = conn.execute(
                "SELECT * FROM tariffs WHERE id = ?", (tariff_id,)
            ).fetchone()
        
        if not tariff_data:
            return jsonify({"status": "error", "message": "Tariff not found"}), 404
            
        return jsonify({"status": "success", "data": dict(tariff_data)})
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей тарифа: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/add_time', methods=['POST'])
@login_required 
@csrf.exempt 
def add_time():
    data = request.get_json()
    if not data: return jsonify({"success": False, "error": "No JSON data"}), 400
    username = data.get("username"); seconds = data.get("seconds")
    if not username or not isinstance(seconds, int) or seconds < 0: return jsonify({"success": False, "error": "Invalid input"}), 400
    try:
        with db_connection() as conn:
            result = conn.execute("SELECT time_left FROM users WHERE username = ?", (username,)).fetchone()
            current_time = result['time_left'] if result and result['time_left'] is not None else 0
            new_time = current_time + seconds
            conn.execute("UPDATE users SET time_left = ? WHERE username = ?", (new_time, username))
        return jsonify({"success": True, "new_time": new_time})
    except Exception as e:
        logger.error(f"Error in add_time: {e}"); return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create_payment', methods=['POST'])
@csrf.exempt 
def create_payment():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    username = data.get('username'); amount = data.get('amount', 0)
    if not username or not isinstance(amount, int) or amount <= 0: 
        return jsonify({"status": "error", "message": "Invalid input"}), 400
    try:
        kaspi_public_key = get_kaspi_public_key()
        kaspi_private_key = get_kaspi_private_key()
        order_id = f"lovhub_{username}_{int(time.time())}"
        payload = {
            "orderId": order_id, "amount": float(amount), 
            "description": f"Пополнение баланса для {username}",
            "metadata": { "username": username, "amount": amount }
        }
        payload_string = json.dumps(payload, separators=(',', ':'))
        signature = create_kaspi_signature(payload_string, kaspi_private_key)
        if not signature:
            return jsonify({"status": "error", "message": "Server signing error"}), 500
        headers = {
            'Content-Type': 'application/json',
            'X-Public-Key': kaspi_public_key, 
            KASPI_SIGNATURE_HEADER: signature
        }
        logger.info(f"Отправка запроса в Kaspi для {username} на {amount} тг...")
        response = requests.post(KASPI_API_URL, data=payload_string, headers=headers, timeout=10)
        response.raise_for_status() 
        response_data = response.json()
        payment_url_from_gateway = response_data.get('paymentUrl') 
        if not payment_url_from_gateway:
            logger.error(f"Kaspi не вернул paymentUrl: {response_data}")
            return jsonify({"status": "error", "message": "Payment gateway error"}), 500
        return jsonify({"status": "success", "payment_url": payment_url_from_gateway})
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating payment (Kaspi API): {e}")
        return jsonify({"status": "error", "message": f"Ошибка связи с Kaspi: {e}"}), 500
    except Exception as e:
        logger.error(f"Error creating payment (Internal): {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/payment_webhook', methods=['POST'])
@csrf.exempt 
def payment_webhook():
    try:
        kaspi_signature = request.headers.get(KASPI_SIGNATURE_HEADER)
        if not kaspi_signature:
            logger.warning("Вебхук: Запрос без подписи.")
            return jsonify({"status": "error", "message": "Missing signature"}), 401
        raw_data = request.get_data()
        raw_data_string = raw_data.decode('utf-8')
        kaspi_private_key = get_kaspi_private_key()
        our_signature = create_kaspi_signature(raw_data_string, kaspi_private_key)
        
        if not hmac.compare_digest(our_signature, kaspi_signature):
            logger.error("Вебхук: НЕВЕРНАЯ ПОДПИСЬ!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 401
            
        data = json.loads(raw_data_string)
        logger.info(f"Получен ВЕБХУК: {data}")
        payment_status = data.get('status')
        metadata = data.get('metadata', {})
        username = metadata.get('username')
        amount = metadata.get('amount')
        order_id = data.get('orderId')
        if not username or not amount or not order_id:
             logger.error(f"Вебхук: Неполные данные: {data}")
             return jsonify({"status": "error", "message": "Invalid webhook data"}), 400
        if payment_status != 'PAID': 
            logger.warning(f"Вебхук: Статус платежа не 'PAID' ({payment_status})")
            return jsonify({"status": "success", "message": "Status not paid"})
        with db_connection() as conn:
            result = conn.execute("SELECT balance FROM users WHERE username = ?", (username,)).fetchone()
            if not result:
                logger.warning(f"Вебхук: Пользователь {username} не найден!")
                return jsonify({"status": "error", "message": "User not found"}), 404
            new_balance = (result['balance'] if result['balance'] is not None else 0) + int(amount)
            conn.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
            conn.execute("INSERT INTO transactions (type, username, amount, order_id) VALUES (?, ?, ?, ?)", ('kaspi_topup', username, int(amount), order_id))
        logger.info(f"Вебхук: Баланс {username} пополнен на {amount} (Заказ: {order_id})")
        return jsonify({"status": "success"}) 
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}"); 
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/fake_payment_page')
def fake_payment_page():
    order_id = request.args.get('order_id')
    amount = request.args.get('amount')
    user = request.args.get('user')
    webhook_url = url_for('payment_webhook', _external=True) 
    return render_template(
        'fake_payment_page.html', 
        order_id=order_id, 
        amount=amount, 
        user=user, 
        webhook_url=webhook_url
    )

@app.route('/api/add_app', methods=['POST'])
@basic_auth.required 
@csrf.exempt 
def api_add_app():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "No JSON data"}), 400
    app_name = data.get('name'); app_path = data.get('path'); app_type = data.get('type'); icon_filename = data.get('icon') 
    if not validate_app_data(app_name, app_path, app_type):
         return jsonify({"status": "error", "message": "Invalid app data"}), 400
    try:
        with db_connection() as conn:
            conn.execute("INSERT INTO apps (name, path, type, icon) VALUES (?, ?, ?, ?)", (app_name, app_path, app_type, icon_filename))
        logger.info(f"App added via API: {app_name}")
        return jsonify({"status": "success", "name": app_name})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "App name already exists"}), 400
    except Exception as e:
        logger.error(f"Error adding app via API: {e}"); return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/api/delete_app', methods=['POST'])
@basic_auth.required 
@csrf.exempt 
def api_delete_app():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"status": "error", "message": "Missing app name"}), 400
    app_name = data.get('name')
    try:
        with db_connection() as conn: conn.execute("DELETE FROM apps WHERE name = ?", (app_name,))
        logger.info(f"App deleted via API: {app_name}")
        return jsonify({"status": "success", "name": app_name})
    except Exception as e:
        logger.error(f"Error deleting app {app_name} via API: {e}"); return jsonify({"status": "error", "message": "Server error"}), 500
# --- КОНЕЦ API ---


@app.errorhandler(404)
def not_found(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {error}")
    return "Internal server error", 500


if __name__ == '__main__':
    print("Запуск сервера в режиме HTTPS (с принудительным TLS)...")
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain('cert.pem', 'key.pem')
    except FileNotFoundError:
        print("\n!!! ОШИБКА: Файлы 'cert.pem' или 'key.pem' не найдены!")
        input("Нажмите Enter для выхода...")
        sys.exit(1)
    except Exception as e:
        print(f"\n!!! ОШИБКА SSL: Не удалось загрузить сертификаты: {e}")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False, 
        ssl_context=context 
    )