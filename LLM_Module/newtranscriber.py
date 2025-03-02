import io
import tempfile
import moviepy.editor as mp
import whisper
import json
import streamlit as st
from groq import Groq
# from transcriptionimprover import TranscriptionImprover 
import ffmpeg 
import tempfile 
from groq import Groq
import os 
class VideoTranscriber:
    def __init__(self, video_file, output_audio_path, output_json_path):
        self.video_file = video_file  
        self.output_audio_path = output_audio_path
        self.output_json_path = output_json_path
        self.client = Groq()
        self.model = whisper.load_model("small")
        self.target_size_kb = 50000 
        self.client = Groq()
        self.compressed_audio_path = "audio/audio.wav"

    # def extract_audio(self):
    def extract_audio(self):
        """ 
        Extracts audio from a video file and compresses it to a specific file size.
        
        Parameters:
        - video_file: Either a file path (str) or an uploaded file object
        - output_audio_path: Path to save the compressed audio file
        - target_size_kb: Desired file size in KB
        """
        video_file = self.video_file
        if isinstance(video_file, str):  # If file path is given
            temp_video_file_path = video_file
        else:  # If file object is given (e.g., in Streamlit or Flask)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                temp_video_file.write(video_file.read())
                temp_video_file_path = temp_video_file.name
        print(temp_video_file_path)

        video_clip = mp.VideoFileClip(temp_video_file_path)
        audio_path = self.output_audio_path
        video_clip.audio.write_audiofile(audio_path)
        
       
        duration = video_clip.audio.duration  # Get audio duration in seconds
        target_bitrate = (self.target_size_kb * 8) / duration  # Bitrate in kbps

       
        min_bitrate = 32  
        if target_bitrate < min_bitrate:
            target_bitrate = min_bitrate
        
        ffmpeg.input(audio_path).output(
            self.compressed_audio_path, 
            audio_bitrate=f"{int(target_bitrate)}k", 
            format="mp3", 
            acodec="libmp3lame"
        ).run(overwrite_output=True)

        print(f"Compressed file saved to {self.output_audio_path}, Size: {os.path.getsize(self.output_audio_path) / 1024:.2f} KB")



    def transcribe(self):
        """Transcribe audio and save the results to the JSON file."""
        self.extract_audio() 
        with open(self.compressed_audio_path, "rb") as file:
            results = self.client.audio.transcriptions.create(
            file=(self.compressed_audio_path, file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
            language='en'
            )
            
      
        transcription_output = []
        data = ""
        for segment in results.segments:
            start = segment['start']
            end = segment['end']
            text = segment['text']
            
            print(f"[{start:.2f}s - {end:.2f}s] {text}")
            data += f"[{start:.2f}s - {end:.2f}s] {text}"

            transcription_output.append({
                'start': start,
                'end': end,
                'text': text
            })

        with open(self.output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(transcription_output, json_file, ensure_ascii=False, indent=4)

        print(f"Transcription results saved to {self.output_json_path}")
        return data

