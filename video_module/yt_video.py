import yt_dlp
from config import save_path
def download_youtube_video(url, save_path=save_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4', 
        'outtmpl': save_path,  
        'merge_output_format': 'mp4'  
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
