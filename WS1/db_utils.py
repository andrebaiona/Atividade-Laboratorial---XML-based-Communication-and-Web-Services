import mysql.connector
from mysql.connector import Error
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime 

# --- Configuração e Conexão BD ---
DB_CONFIG = {
    'user': os.environ.get("MYSQL_USER"),
    'password': os.environ.get("MYSQL_PASSWORD"),
    'host': os.environ.get("MYSQL_HOST"),
    'database': os.environ.get("MYSQL_DATABASE"),
    'port': os.environ.get("MYSQL_PORT", 3306)
}

def get_db_connection():
    """Estabelece e retorna uma conexão MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None


ph = PasswordHasher()

def hash_password(password):
    """Gera o hash de uma password usando Argon2."""
    return ph.hash(password.encode('utf-8'))

def check_password(hashed_password, plain_password):
    """Verifica se a password fornecida corresponde ao hash Argon2."""
    if not hashed_password or not plain_password:
         return False
    try:
        ph.verify(hashed_password, plain_password.encode('utf-8'))
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        print(f"Erro ao verificar password com Argon2: {e}")
        return False



# Funções de Acesso à BD 


def db_user_login(username, password):
    conn = get_db_connection()
    if conn is None: return None
    cursor = conn.cursor(dictionary=True)
    user_info = None
    try:
        query = "SELECT id, password_hash, role FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user_record = cursor.fetchone()
        if user_record and check_password(user_record['password_hash'], password):
            user_info = {"user_id": user_record['id'], "role": user_record['role']}
    except Error as e: print(f"Erro na query db_user_login: {e}")
    except Exception as argon_e: print(f"Erro Argon2 em db_user_login: {argon_e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return user_info

def db_user_register(username, password, email):
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    success = False
    try:
        check_query = "SELECT id FROM users WHERE username = %s OR email = %s"
        cursor.execute(check_query, (username, email))
        if cursor.fetchone():
             print(f"Utilizador ou email já existe: {username}/{email}")
             return False
        hashed_pw = hash_password(password)
        insert_query = """
            INSERT INTO users (username, password_hash, email, role)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (username, hashed_pw, email, 'client'))
        conn.commit()
        success = cursor.rowcount > 0
    except Error as e:
        print(f"Erro na query db_user_register: {e}")
        conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return success

def db_list_packages(user_id):
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    packages = []
    try:
        query = """
            SELECT id, name, description, sender_city, destination_city, is_tracked
            FROM packages
            WHERE sender_id = %s OR receiver_id = %s
            ORDER BY creation_date DESC
        """
        cursor.execute(query, (user_id, user_id))
        packages = cursor.fetchall()
    except Error as e: print(f"Erro na query db_list_packages: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return packages

def db_check_status(package_id):
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    tracking_history = []
    try:
        query = """
            SELECT city, timestamp
            FROM tracking_info
            WHERE package_id = %s
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (package_id,))
        tracking_history = cursor.fetchall()
        for entry in tracking_history:
             if isinstance(entry['timestamp'], datetime):
                 entry['timestamp'] = entry['timestamp'].isoformat()
    except Error as e: print(f"Erro na query db_check_status: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return tracking_history

def db_search_packages(user_id, search_term):
    """Procura pacotes de um utilizador por um termo (nome ou descrição)."""
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    packages = []
    try:
        term = f"%{search_term}%"
        query = """
            SELECT id, name, description, sender_city, destination_city, is_tracked
            FROM packages
            WHERE (sender_id = %s OR receiver_id = %s)
              AND (name LIKE %s OR description LIKE %s)
            ORDER BY creation_date DESC
        """
        cursor.execute(query, (user_id, user_id, term, term))
        packages = cursor.fetchall()
    except Error as e:
        print(f"Erro na query db_search_packages: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return packages