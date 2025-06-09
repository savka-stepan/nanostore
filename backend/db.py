import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()


CLOUD_DB_HOST = os.environ.get("CLOUD_DB_HOST", "localhost")
CLOUD_DB_USER = os.environ.get("CLOUD_DB_USER", "postgres")
CLOUD_DB_PASSWORD = os.environ.get("CLOUD_DB_PASSWORD", "")
CLOUD_DB_NAME = os.environ.get("CLOUD_DB_NAME", "nanostore_db")


def get_setting_from_db(key: str, default=None) -> str:
    """Retrieve a value by key from the settings table."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            host=CLOUD_DB_HOST,
            user=CLOUD_DB_USER,
            password=CLOUD_DB_PASSWORD,
            dbname=CLOUD_DB_NAME,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=%s LIMIT 1", (key,))
        result = cursor.fetchone()
        return result[0] if result else default
    except Exception as e:
        print(f"Database error: {e}")
        return default
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
