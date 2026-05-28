import psycopg2
from psycopg2.extras import RealDictCursor

MASTER_DSN = {
    "host": "localhost",
    "port": 5432,
    "database": "autoservice",
    "user": "postgres",
    "password": "ZXasQW12"
}

SLAVE_DSN = {
    "host": "localhost",
    "port": 5432,
    "database": "autoservice",
    "user": "postgres",
    "password": "ZXasQW12"
}

def get_connection(mode='master'):
    dsn = MASTER_DSN if mode == 'master' else SLAVE_DSN
    try:
        conn = psycopg2.connect(**dsn, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"DB connection error ({mode}): {e}")
        if mode == 'slave':
            print("Fallback to master")
            conn = psycopg2.connect(**MASTER_DSN, cursor_factory=RealDictCursor)
            return conn
        raise

def query(sql, params=None, mode='slave', fetch=False):
    """Универсальная функция для запросов"""
    conn = get_connection(mode)
    cur = conn.cursor()
    cur.execute(sql, params)
    if fetch:
        res = cur.fetchall() if fetch == 'all' else cur.fetchone()
    else:
        conn.commit()
        res = None
    cur.close()
    conn.close()
    return res
