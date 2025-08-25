import os

def clean_directories():
    """
    Deletes files with given extensions from multiple directories (recursively).
    
    Args:
        directories (list): List of directories to clean.
        extensions (list): File extensions to remove (e.g., ['.json', '.mp4']).
    """
    directories = ["./json", "./static/uploads", "./" , "./reports" , "./audio"]  # put your folders here
    extensions = [".json", ".mp4", ".pdf", ".png" , ".wav"]

    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")

