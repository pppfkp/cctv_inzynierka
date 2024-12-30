import os
import csv
import psycopg2
from psycopg2 import pool
from shapely.geometry import Point, Polygon
import ast
import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

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

def get_detection_results(user_id, start_time, end_time):
    query = """
    SELECT id, "time", 
           vector_norm(subvector(xywh, 1, 1)) AS x, 
           vector_norm(subvector(xywh, 2, 1)) + vector_norm(subvector(xywh, 4, 1)) / 2 AS y, 
           camera_id, user_id, track_id
    FROM public.stats_detection
    WHERE user_id = %s AND "time" BETWEEN %s AND %s
    ORDER BY "time"
    """

    conn = None
    results = []
    try:
        conn = DB_POOL.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, start_time, end_time))
            results = cursor.fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        if conn:
            DB_POOL.putconn(conn)

    return results

def get_boundaries():
    query = """
    SELECT id, polygon, camera_id, zone_id
    FROM public.management_boundary
    """

    conn = None
    boundaries = []
    try:
        conn = DB_POOL.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query)
            for row in cursor.fetchall():
                # Convert polygon string to list of coordinate pairs
                polygon_str = row[1]
                try:
                    flat_coords = ast.literal_eval(polygon_str)
                    coords = [(flat_coords[i], flat_coords[i+1]) for i in range(0, len(flat_coords), 2)]
                    boundaries.append({
                        "id": row[0],
                        "polygon": Polygon(coords),
                        "camera_id": row[2],
                        "zone_id": row[3],
                    })
                except (ValueError, IndexError) as e:
                    print(f"Skipping invalid polygon for boundary ID {row[0]}: {e}")
    except Exception as e:
        print(f"Error fetching boundaries: {e}")
    finally:
        if conn:
            DB_POOL.putconn(conn)

    return boundaries

def associate_detections_with_boundaries(detections, boundaries):
    output_rows = []
    boundary_ids = [boundary["id"] for boundary in boundaries]

    for detection in detections:
        detection_id, time, x, y, camera_id, user_id, track_id = detection
        point = Point(x, y)

        # Initialize a list of booleans for each boundary (whether the detection is inside the boundary)
        boundary_associations = {boundary_id: False for boundary_id in boundary_ids}

        # Check each boundary for this detection
        for boundary in boundaries:
            if boundary["camera_id"] == camera_id and boundary["polygon"].contains(point):
                boundary_associations[boundary["id"]] = True

        output_rows.append({
            "id": detection_id,
            "time": time,
            "x": x,
            "y": y,
            "camera_id": camera_id,
            "user_id": user_id,
            "track_id": track_id,
            **boundary_associations  # Add the boundary association booleans
        })

    return output_rows

def save_to_csv(rows, output_file):
    # Extract fieldnames from the first row (to account for dynamic boolean fields)
    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

def create_heatmap_with_polygon(rows, boundaries):
    for boundary in boundaries:
        boundary_id = boundary["id"]
        polygon = boundary["polygon"]

        # Filter detections for this boundary
        detections = [(row["x"], row["y"]) for row in rows if row[boundary_id]]

        if not detections:
            continue

        # Plot the polygon and heatmap
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Get coordinates of the polygon
        xs, ys = zip(*polygon.exterior.coords)
        ax.plot(xs, ys, color="blue", label=f"Boundary {boundary_id} Boundary")

                # Convert coordinates to integers (e.g., using np.floor)
        xs, ys = zip(*detections)
        xs = np.floor(xs).astype(int)  # Cast x-coordinates to integers
        ys = np.floor(ys).astype(int)  # Cast y-coordinates to integers
        heatmap, xedges, yedges = np.histogram2d(xs, ys, bins=(640, 480), range=[[0, 640], [0, 480]])

        # Display the heatmap
        ax.imshow(
            heatmap.T,
            extent=(0, 640, 0, 480),
            origin="lower",
            cmap="hot",
            alpha=0.6
        )

        ax.set_xlim(0, 640)
        ax.set_ylim(0, 480)
        ax.set_title(f"Heatmap for Boundary {boundary_id}")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.legend()

        # Flip the image horizontally and vertically
        plt.gca().invert_yaxis()  # Flipping vertically (invert the y-axis)


        # Save the flipped heatmap as an image
        plt.savefig(f"heatmap_boundary_{boundary_id}.png")
        plt.close()

def count_detections_per_boundary(associated_results, boundaries):
    detection_count = {boundary["id"]: 0 for boundary in boundaries}
    for row in associated_results:
        for boundary in boundaries:
            if row[boundary["id"]]:
                detection_count[boundary["id"]] += 1
    return detection_count

if __name__ == "__main__":
    # Example usage
    user_id = 1
    start_time = datetime(2024, 12, 30, 16, 45, 00)
    end_time = datetime(2024, 12, 30, 16, 55, 00)

    detections = get_detection_results(user_id, start_time, end_time)
    boundaries = get_boundaries()
    print(len(boundaries))

    if detections and boundaries:
        associated_results = associate_detections_with_boundaries(detections, boundaries)
        detection_count = count_detections_per_boundary(associated_results, boundaries)
        save_to_csv(associated_results, "output.csv")
        print("CSV file created: output.csv")

        create_heatmap_with_polygon(associated_results, boundaries)
        print("Heatmaps created.")

        print(detection_count)
    else:
        print("No data to process.")