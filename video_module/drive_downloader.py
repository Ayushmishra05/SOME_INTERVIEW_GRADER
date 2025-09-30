import re
import gdown
import asyncio
import os

async def download_drive_url(url, output_path):
    pattern = r"https?://drive\.google\.com/(?:file/d/|open\?id=|uc\?id=|drive/folders/)?([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)
    if match:
        file_id = match.group(1)
        direct_url = f"https://drive.google.com/uc?id={file_id}"
        def sync_download():
            gdown.download(direct_url, output=output_path, quiet=False)
        await asyncio.to_thread(sync_download)
    else:
        print("Invalid Google Drive URL!")