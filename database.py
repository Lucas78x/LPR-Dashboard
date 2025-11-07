import sqlite3
import os

DB_PATH = "auth.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def create_auth_db():
    conn = get_conn()
    cur = conn.cursor()

    # Tabela de usuários
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabela de alarmes (nome do carro + placa)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alarms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_name TEXT NOT NULL,
        plate TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def get_user(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def create_user(username: str, password_hash: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?,?)", (username, password_hash))
    conn.commit()
    conn.close()

def list_alarms():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    cur = conn.cursor()
    cur.execute("SELECT * FROM alarms ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_alarm(car_name: str, plate: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO alarms (car_name, plate) VALUES (?,?)", (car_name, plate))
    conn.commit()
    conn.close()

def delete_alarm(alarm_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
    conn.commit()
    conn.close()
