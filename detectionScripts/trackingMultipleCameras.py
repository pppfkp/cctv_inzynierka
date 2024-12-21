import subprocess
import time
from utils.timescaleUtils import get_all_cameras, get_all_settings

def run_camera_script(camera_link, camera_id, fps_tracking, batch_size, face_detection_model, person_detection_model, face_similarity_treshold, face_detection_treshold, person_detection_treshold):
    """Runs the tracking script for a single camera in a new PowerShell window."""
    venv_python = ".venv/Scripts/python.exe"  # Replace with your venv path
    command = [
        "start", "powershell", "-NoExit", "-Command",  # Use `start` to open a new window
        f"& '{venv_python}' 'buferlessTracking.py' "  # Command to run the Python script
        f"--camera_link {camera_link} "
        f"--camera_id {camera_id} "
        f"--fps_tracking {fps_tracking} "
        f"--batch_size {batch_size} "
        f"--face_detection_model {face_detection_model} "
        f"--person_detection_model {person_detection_model} "
        f"--face_similarity_treshold {face_similarity_treshold} "
        f"--face_detection_treshold {face_detection_treshold} "
        f"--person_detection_treshold {person_detection_treshold}"
    ]
    print(f"Running command: {' '.join(command)}")
    process = subprocess.Popen(command, shell=True)  # Use `shell=True` to ensure `start` works correctly
    return process

if __name__ == "__main__":

    # Fetch camera details from the database
    cameras_from_db = get_all_cameras()
    # Fetch settings from the database
    settings_from_db = get_all_settings()

    # Create a dictionary from the settings to easily access values by key
    settings_dict = {setting['key']: setting['value'] for setting in settings_from_db}

    # Build the camera_configs list using the fetched camera data and settings
    camera_configs = [
        {
            "link": camera["link"],
            "id": camera["id"],
            "fps": int(settings_dict.get("fpsTracking", 10)),  
            "batch": int(settings_dict.get("batchSizeDetectionsSave", 100)),  
            "face_model": settings_dict.get("faceDetectionModel", "yolov10n-face.pt"),  
            "person_model": settings_dict.get("trackingModel", "yolo11n.pt"),  
            "face_similarity": float(settings_dict.get("faceSimilarityTresholdTracking", 0.7)),  
            "face_detection": float(settings_dict.get("faceDetectionTresholdTracking", 0.4)),  
            "person_detection": float(settings_dict.get("personDetectionTresholdTracking", 0.6)), 
            "face_similarity_enter_exit": float(settings_dict.get("faceSimilarityTresholdEnterExit", 0.7)) 
            
        }
        for camera in cameras_from_db
    ]

    processes = []
    for config in camera_configs:
        process = run_camera_script(
            config["link"], config["id"], config["fps"], config["batch"], config["face_model"], config["person_model"], config["face_similarity"], config["face_detection"], config["person_detection"]
        )
        processes.append(process)
        time.sleep(1)  # small delay between starting processes

    try:
        # Keep the main script running to monitor subprocesses (optional)
        while True:
            time.sleep(60)  # Check every 5 seconds
            for i, process in enumerate(processes):
                if process.poll() is not None:  # Check if process has finished
                    print(f"Camera {camera_configs[i]['id']} process exited with code {process.returncode}")
                    # Optionally restart the process here if needed
                    # processes[i] = run_camera_script(
                    #     camera_configs[i]["link"], camera_configs[i]["id"], camera_configs[i]["fps"], camera_configs[i]["batch"], camera_configs[i]["face_model"], camera_configs[i]["person_model"], camera_configs[i]["face_similarity"], camera_configs[i]["face_detection"], camera_configs[i]["person_detection"]
                    # )
                    # print(f"Restarting Camera {camera_configs[i]['id']}")
    except KeyboardInterrupt:
        print("Stopping camera processes...")
        for process in processes:
            process.terminate()  # Send SIGTERM to gracefully stop
        for process in processes:
            process.wait()  # Wait for processes to finish
        print("All camera processes stopped.")
