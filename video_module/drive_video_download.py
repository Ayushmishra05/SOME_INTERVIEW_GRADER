import re
import gdown 
from config import save_path  

def download_drive_url(url):
    pattern = r"https?://drive\.google\.com/(?:file/d/|open\?id=|uc\?id=|drive/folders/)?([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)
    
    if match:
        file_id = match.group(1) 
        direct_url = f"https://drive.google.com/uc?id={file_id}"  

        gdown.download(direct_url, output=save_path, quiet=False)

    else:
        print("Invalid Google Drive URL!")


