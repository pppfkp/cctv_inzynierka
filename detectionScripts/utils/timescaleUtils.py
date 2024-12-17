import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv(dotenv_path='../.env')

# Database connection settings from .env
DB_SETTINGS = {
    "host": "localhost",
    "port": int(os.getenv("PGVECTOR_DB_PORT")),
    "dbname": os.getenv("PGVECTOR_DB_NAME"),
    "user": os.getenv("PGVECTOR_DB_USER"),
    "password": os.getenv("PGVECTOR_DB_PASSWORD"),
}

# Create a connection pool
DB_POOL = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_SETTINGS
)


def save_to_timescaledb(data_batch):
    """
    Save a batch of detection data to the database.

    Args:
        data_batch (list): A list of tuples containing detection data to insert.
                           Each tuple should contain:
                           (user_id, camera_id, track_id, time, x_center, y_center, width, height)
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Updated INSERT query to match the Detection model with track_id
        insert_query = """
        INSERT INTO stats_detection (
            user_id, camera_id, track_id, time, xywh
        ) VALUES (%s, %s, %s, %s, array[%s, %s, %s, %s])
        """

        # Transform data_batch to match the query's format
        transformed_batch = [
            (user_id, camera_id, track_id, time, x_center, y_center, width, height)
            for user_id, camera_id, track_id, time, x_center, y_center, width, height in data_batch
        ]

        cursor.executemany(insert_query, transformed_batch)
        conn.commit()
        print(f"{len(data_batch)} rows saved to DB")
    except Exception as e:
        print(f"Error saving data to DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)
