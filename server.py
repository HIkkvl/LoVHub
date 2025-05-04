from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sqlite3
import socket

# Инициализация базы данных
def init_db():
    if not os.path.exists("apps.db"):
        conn = sqlite3.connect("apps.db")
        c = conn.cursor()
        c.execute('''
            CREATE TABLE apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                type TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE launch_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                computer_name TEXT,
                ip_address TEXT,
                user TEXT,
                app_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

init_db()

app = Flask(__name__)

def get_apps():
    conn = sqlite3.connect("apps.db")
    c = conn.cursor()
    c.execute("SELECT id, name, path, type FROM apps")
    apps = [{"id": row[0], "name": row[1], "path": row[2], "type": row[3]} for row in c.fetchall()]
    conn.close()
    return apps

def get_logs():
    conn = sqlite3.connect("apps.db")
    c = conn.cursor()
    c.execute("SELECT computer_name, ip_address, user, app_name, timestamp FROM launch_logs ORDER BY timestamp DESC")
    logs = [{"computer_name": row[0], "ip_address": row[1], "user": row[2], "app_name": row[3], "timestamp": row[4]} for row in c.fetchall()]
    conn.close()
    return logs

@app.route('/')
def index():
    apps = get_apps()
    games = [app for app in apps if app["type"] == "game"]
    software = [app for app in apps if app["type"] == "app"]
    logs = get_logs()
    return render_template('index.html', games=games, software=software, logs=logs)



@app.route('/run/<app_name>')
def run_app(app_name):
    app = next((app for app in get_apps() if app["name"] == app_name), None)
    if app:
        try:
            os.startfile(app["path"])
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error: {e}"
    return f"App {app_name} not found"

@app.route('/add', methods=['GET', 'POST'])
def add_app():
    if request.method == 'POST':
        app_name = request.form['name']
        app_path = request.form['path']
        app_type = request.form['type']
        conn = sqlite3.connect("apps.db")
        c = conn.cursor()
        c.execute("INSERT INTO apps (name, path, type) VALUES (?, ?, ?)", (app_name, app_path, app_type))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_app.html')

@app.route('/delete/<app_name>', methods=['GET'])
def delete_app(app_name):
    conn = sqlite3.connect("apps.db")
    c = conn.cursor()
    c.execute("DELETE FROM apps WHERE name = ?", (app_name,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:app_id>', methods=['GET', 'POST'])
def edit_app(app_id):
    conn = sqlite3.connect("apps.db")
    c = conn.cursor()

    if request.method == 'POST':
        app_name = request.form['name']
        app_path = request.form['path']
        app_type = request.form['type']
        c.execute("UPDATE apps SET name = ?, path = ?, type = ? WHERE id = ?", (app_name, app_path, app_type, app_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT name, path, type FROM apps WHERE id = ?", (app_id,))
    app = c.fetchone()
    conn.close()

    if app:
        return render_template('edit_app.html', app_id=app_id, app_name=app[0], app_path=app[1], app_type=app[2])
    else:
        return "App not found", 404

@app.route('/log_launch', methods=['POST'])
def log_launch():
    data = request.json
    computer_name = data.get('computer_name')
    ip_address = data.get('ip_address')
    user = data.get('user')
    app_name = data.get('app_name')

    conn = sqlite3.connect("apps.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO launch_logs (computer_name, ip_address, user, app_name)
        VALUES (?, ?, ?, ?)
    ''', (computer_name, ip_address, user, app_name))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/clear_logs')
def clear_logs():
    conn = sqlite3.connect("apps.db")
    c = conn.cursor()
    c.execute("DELETE FROM launch_logs")
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)