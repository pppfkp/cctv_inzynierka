import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv(dotenv_path='../.env')

# Database connection settings from .env
DB_SETTINGS = {
    "host": os.getenv("TIMESCALE_DB_ADDRESS"),
    "port": int(os.getenv("TIMESCALE_DB_PORT", 5433)),
    "dbname": os.getenv("TIMESCALE_DB_NAME"),
    "user": os.getenv("TIMESCALE_DB_USER"),
    "password": os.getenv("TIMESCALE_DB_PASSWORD"),
}

# Create a connection pool
DB_POOL = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_SETTINGS
)


def save_to_timescaledb(data_batch):
    """
    Save a batch of tracking data to TimescaleDB.

    Args:
        data_batch (list): A list of tuples containing tracking data to insert.
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO tracking_data (
            camera_link, track_id, user_id, detection_date, detection_time,
            x_center, y_center, width, height
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_query, data_batch)
        conn.commit()
        print(f"{len(data_batch)} rows saved to TimescaleDB")
    except Exception as e:
        print(f"Error saving data to TimescaleDB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)
