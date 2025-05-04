import sqlite3

# Создаем подключение к файлу users.db (если его нет — он создастся)
conn = sqlite3.connect("users.db")
c = conn.cursor()

# Создаем таблицу users с полями id, username и password
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')

conn.commit()
conn.close()

print("База данных создана успешно!")
