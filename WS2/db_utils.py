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

def check_password_needs_rehash(hashed_password):
     """Verifica se o hash usa os parâmetros Argon2 atuais."""
     if not hashed_password: return False
     try:
          return ph.check_needs_rehash(hashed_password)
     except Exception:
          return False 


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




def db_add_package(sender_id, receiver_id, name, description, sender_city, dest_city):
    conn = get_db_connection()
    if conn is None: return None
    cursor = conn.cursor()
    new_package_id = None
    try:
        query = """
            INSERT INTO packages (sender_id, receiver_id, name, description, sender_city, destination_city, is_tracked)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (sender_id, receiver_id, name, description, sender_city, dest_city, False))
        conn.commit()
        if cursor.lastrowid:
             new_package_id = cursor.lastrowid
    except Error as e:
        print(f"Erro na query db_add_package: {e}")
        conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return new_package_id

def db_remove_package(package_id):
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    success = False
    try:
         query = "DELETE FROM packages WHERE id = %s"
         cursor.execute(query, (package_id,))
         conn.commit()
         success = cursor.rowcount > 0
    except Error as e:
         print(f"Erro na query db_remove_package: {e}")
         conn.rollback()
    finally:
         if cursor: cursor.close()
         if conn: conn.close()
    return success

def db_register_tracking(package_id, initial_city, initial_time_str):
    """Marca pacote como rastreado e adiciona ponto inicial."""
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    success = False
    try:
        try:
             initial_time = datetime.fromisoformat(initial_time_str)
        except ValueError:
             print(f"Formato de timestamp inválido: {initial_time_str}")
             return False 

        update_pkg_query = "UPDATE packages SET is_tracked = TRUE WHERE id = %s AND is_tracked = FALSE" # Evitar re-registar
        cursor.execute(update_pkg_query, (package_id,))
        updated_rows = cursor.rowcount

        if updated_rows == 0:
             check_query = "SELECT id FROM packages WHERE id = %s AND is_tracked = TRUE"
             cursor.execute(check_query, (package_id,))
             if cursor.fetchone():
                  print(f"Pacote {package_id} já estava rastreado.")
             else:
                   print(f"Pacote {package_id} não encontrado para registar rastreio.")
                   return False 

        insert_track_query = """
            INSERT INTO tracking_info (package_id, city, timestamp)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE city = VALUES(city) -- Exemplo: se (package_id, timestamp) fosse unique
            -- Se não houver constraint unique, apenas insere
        """
        cursor.execute(insert_track_query, (package_id, initial_city, initial_time))

        conn.commit()
        success = True
    except Error as e:
        print(f"Erro na query db_register_tracking: {e}")
        conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return success

def db_update_package_status(package_id, city, time_str):
    """Adiciona uma nova entrada de rastreamento."""
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    success = False
    try:
        check_pkg_query = "SELECT id FROM packages WHERE id = %s AND is_tracked = TRUE"
        cursor.execute(check_pkg_query, (package_id,))
        if not cursor.fetchone():
            print(f"Pacote {package_id} não encontrado ou não está a ser rastreado.")
            return False

        try:
             time_obj = datetime.fromisoformat(time_str)
        except ValueError:
             print(f"Formato de timestamp inválido: {time_str}")
             return False

        insert_query = """
            INSERT INTO tracking_info (package_id, city, timestamp)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (package_id, city, time_obj))
        conn.commit()
        success = cursor.rowcount > 0
    except Error as e:
        print(f"Erro na query db_update_package_status: {e}")
        conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return success

def db_get_all_users():
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    users = []
    try:
        query = "SELECT id, username FROM users ORDER BY username ASC"
        cursor.execute(query)
        users = cursor.fetchall()
    except Error as e:
        print(f"Erro na query db_get_all_users: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return users

def db_get_all_packages():
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    packages = []
    try:
        query = """
            SELECT
                p.id, p.name, p.description, p.sender_city, p.destination_city, p.is_tracked,
                sender.username AS sender_username,
                receiver.username AS receiver_username,
                p.creation_date
            FROM packages p
            JOIN users sender ON p.sender_id = sender.id
            JOIN users receiver ON p.receiver_id = receiver.id
            ORDER BY p.creation_date DESC
        """
        cursor.execute(query)
        packages = cursor.fetchall()
        for pkg in packages:
            if isinstance(pkg['creation_date'], datetime):
                pkg['creation_date'] = pkg['creation_date'].isoformat()
    except Error as e:
        print(f"Erro na query db_get_all_packages: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return packages