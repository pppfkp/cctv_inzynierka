import asyncio
import os
import cv2
from psycopg2 import pool
import torch
from ultralytics import YOLO
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection settings
DB_SETTINGS = {
    "host": os.getenv("PGVECTOR_DB_HOST"),
    "port": int(os.getenv("PGVECTOR_DB_PORT")),
    "dbname": os.getenv("PGVECTOR_DB_NAME"),
    "user": os.getenv("PGVECTOR_DB_USER"),
    "password": os.getenv("PGVECTOR_DB_PASSWORD"),
}

# Create a connection pool
DB_POOL = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_SETTINGS
)