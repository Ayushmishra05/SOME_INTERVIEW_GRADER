import yt_dlp
# from config import save_path
def download_youtube_video(url, save_path='yt_video.mp4'):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4', 
        'outtmpl': save_path,  
        'merge_output_format': 'mp4', 
        'verbose' : True, 
        'ffmpeg_location' : r'C:\ProgramData\chocolatey\bin\ffmpeg.exe'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


download_youtube_video(r'https://youtu.be/3MJh2Dm9IgQ?si=4cSHrRcjT6UZoeg0')