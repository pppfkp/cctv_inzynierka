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

def save_entry_to_db(entry):
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Updated INSERT query to match the Detection model with track_id
        insert_query = """
        INSERT INTO stats_enter (
            time, user_id
        ) VALUES (%s, %s)
        """

        cursor.execute(insert_query, entry)
        conn.commit()
        print(f"saved entry to db")
    except Exception as e:
        print(f"Error saving data to DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)

def save_exit_to_db(entry):
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Updated INSERT query to match the Detection model with track_id
        insert_query = """
        INSERT INTO stats_exit (
            time, user_id
        ) VALUES (%s, %s)
        """

        cursor.execute(insert_query, entry)
        conn.commit()
        print(f"saved exit to db")
    except Exception as e:
        print(f"Error saving data to DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)

def set_user_inside_status(user_id, status):
    """
    Update the is_inside field for a user's TrackingSubject to True or False.

    Args:
        user_id (int): The ID of the user whose is_inside status needs to be updated.
        status (bool): The value to set for is_inside (True or False).
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Update query for the TrackingSubject model
        update_query = """
        UPDATE management_trackingsubject
        SET is_inside = %s
        WHERE user_id = %s
        """

        cursor.execute(update_query, (status, user_id))
        conn.commit()
        print(f"Set is_inside for user_id {user_id} to {status}")
    except Exception as e:
        print(f"Error updating is_inside for user_id {user_id}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)

def get_all_cameras():
    """
    Fetch all camera details from the database.

    Returns:
        list: A list of dictionaries containing camera details (id, link, name, enabled, transformation_matrix).
              Each dictionary corresponds to a row in the management_camera table.
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Query to fetch camera details
        select_query = """
        SELECT id, link, name, enabled, transformation_matrix
        FROM public.management_camera;
        """

        cursor.execute(select_query)
        cameras = cursor.fetchall()

        # Convert result into a list of dictionaries
        camera_details = [
            {
                "id": camera[0],
                "link": camera[1],
                "name": camera[2],
                "enabled": camera[3],
                "transformation_matrix": camera[4]
            }
            for camera in cameras
        ]

        return camera_details
    except Exception as e:
        print(f"Error fetching camera details from DB: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)

def get_all_settings():
    """
    Fetch all settings from the database.

    Returns:
        list: A list of dictionaries containing settings details (id, key, value, description, data_type).
              Each dictionary corresponds to a row in the management_setting table.
    """
    try:
        conn = DB_POOL.getconn()
        cursor = conn.cursor()

        # Query to fetch settings details
        select_query = """
        SELECT id, key, value, description, data_type
        FROM public.management_setting;
        """

        cursor.execute(select_query)
        settings = cursor.fetchall()

        # Convert result into a list of dictionaries
        settings_details = [
            {
                "id": setting[0],
                "key": setting[1],
                "value": setting[2],
                "description": setting[3],
                "data_type": setting[4]
            }
            for setting in settings
        ]

        return settings_details
    except Exception as e:
        print(f"Error fetching settings details from DB: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            DB_POOL.putconn(conn)
