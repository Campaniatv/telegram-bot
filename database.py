import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

conn = None
cursor = None

def get_db_connection():
    global conn, cursor
    if conn is None:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    return conn, cursor

def setup_database():
    conn, cursor = get_db_connection()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_commands (
        command_name TEXT PRIMARY KEY,
        response_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by BIGINT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broadcast_logs (
        id SERIAL PRIMARY KEY,
        admin_id BIGINT,
        message_type TEXT,
        message_content TEXT,
        sent_count INTEGER,
        failed_count INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

def add_user(user):
    conn, cursor = get_db_connection()
    cursor.execute("""
    INSERT INTO users (user_id, first_name, last_name, username)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        username = EXCLUDED.username,
        last_active = CURRENT_TIMESTAMP
    """, (user.id, user.first_name, user.last_name, user.username))
    conn.commit()

def update_active(user_id):
    conn, cursor = get_db_connection()
    cursor.execute("""
    UPDATE users SET last_active = CURRENT_TIMESTAMP
    WHERE user_id = %s
    """, (user_id,))
    conn.commit()

def get_custom_command(command_name):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT response_text FROM custom_commands WHERE command_name = %s", (command_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def add_custom_command(command_name, response_text, created_by):
    conn, cursor = get_db_connection()
    cursor.execute("""
    INSERT INTO custom_commands (command_name, response_text, created_by)
    VALUES (%s, %s, %s)
    ON CONFLICT (command_name) DO UPDATE SET
        response_text = EXCLUDED.response_text,
        created_by = EXCLUDED.created_by
    """, (command_name, response_text, created_by))
    conn.commit()

def delete_custom_command(command_name):
    conn, cursor = get_db_connection()
    cursor.execute("DELETE FROM custom_commands WHERE command_name = %s", (command_name,))
    conn.commit()

def log_broadcast(admin_id, message_type, message_content, sent_count, failed_count):
    conn, cursor = get_db_connection()
    cursor.execute("""
    INSERT INTO broadcast_logs (admin_id, message_type, message_content, sent_count, failed_count)
    VALUES (%s, %s, %s, %s, %s)
    """, (admin_id, message_type, message_content, sent_count, failed_count))
    conn.commit()
