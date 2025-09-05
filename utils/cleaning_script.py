import os
import time

def clean_directories(expiry_minutes=20):
    """
    Deletes files with given extensions from multiple directories (recursively),
    only if they are older than expiry_minutes.
    """
    directories = ["./json", "./static/uploads", "./images", "./reports", "./audio"]
    extensions = [".json", ".mp4", ".pdf", ".png", ".wav"]

    now = time.time()
    expiry_seconds = expiry_minutes * 60

    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > expiry_seconds:  # Only delete old files
                            os.remove(file_path)
                            print(f"Deleted expired file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")


if __name__ == "__main__":
    clean_directories(expiry_minutes=5)
