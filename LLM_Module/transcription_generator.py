import io
import tempfile
import moviepy.editor as mp
import json
import ffmpeg
import os
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import AsyncGroq, APIError
from dotenv import load_dotenv 
load_dotenv(override=True)

api_key = os.environ['GROQ_API_KEY']




# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# with open(r'utils/groq_key.json' , 'r') as fp:
#     data = json.load(fp)



class VideoTranscriber:
    def __init__(self, video_file, output_audio_path, output_json_path):
        self.video_file = video_file
        self.output_audio_path = output_audio_path
        self.output_json_path = output_json_path
        self.target_size_kb = 50000
        self.compressed_audio_path = f"audio/compressed_audio_{os.urandom(4).hex()}.mp3"
        self.client = AsyncGroq()
        self.api_key = api_key
        if not self.api_key:
            logger.error("GROQ_API_KEY environment variable not set")
            raise ValueError("GROQ_API_KEY not set")

    async def extract_audio(self):
        """Extract and compress audio from video in a thread-safe manner."""
        if isinstance(self.video_file, str):
            if not os.path.exists(self.video_file):
                logger.error(f"Video file not found: {self.video_file}")
                raise FileNotFoundError(f"Video file not found: {self.video_file}")
            temp_video_file_path = self.video_file
        else:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                    temp_video_file.write(self.video_file.read())
                    temp_video_file_path = temp_video_file.name
                logger.info(f"Temporary video file created: {temp_video_file_path}")
            except Exception as e:
                logger.error(f"Error creating temporary video file: {e}")
                raise

        def sync_extract():
            try:
                video_clip = mp.VideoFileClip(temp_video_file_path)
                video_clip.audio.write_audiofile(self.output_audio_path)
                duration = video_clip.audio.duration
                video_clip.close()
                target_bitrate = max(32, (self.target_size_kb * 8) / duration)
                ffmpeg.input(self.output_audio_path).output(
                    self.compressed_audio_path,
                    audio_bitrate=f"{int(target_bitrate)}k",
                    format="mp3",
                    acodec="libmp3lame"
                ).run(overwrite_output=True, quiet=True)
                if not isinstance(self.video_file, str):
                    os.remove(temp_video_file_path)
                return os.path.getsize(self.compressed_audio_path) / 1024
            except Exception as e:
                logger.error(f"Error during audio extraction/compression: {e}")
                raise

        try:
            size_kb = await asyncio.to_thread(sync_extract)
            logger.info(f"Compressed audio saved to {self.compressed_audio_path}, Size: {size_kb:.2f} KB")
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APIError, asyncio.TimeoutError))
    )
    async def transcribe(self):
        """Transcribe audio asynchronously using Groq API and save results."""
        await self.extract_audio()

        if not os.path.exists(self.compressed_audio_path):
            logger.error(f"Compressed audio file not found: {self.compressed_audio_path}")
            raise FileNotFoundError(f"Compressed audio file not found: {self.compressed_audio_path}")

        try:
            with open(self.compressed_audio_path, "rb") as file:
                results = await self.client.audio.transcriptions.create(
                    file=(self.compressed_audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language="en"
                )
            logger.info("Transcription completed successfully")

            transcription_output = []
            data = ""
            for segment in results.segments:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"]
                logger.info(f"[{start:.2f}s - {end:.2f}s] {text}")
                data += f"[{start:.2f}s - {end:.2f}s] {text} "
                transcription_output.append({"start": start, "end": end, "text": text})

            await asyncio.to_thread(
                json.dump, transcription_output, open(self.output_json_path, 'w', encoding='utf-8'),
                ensure_ascii=False, indent=4
            )
            logger.info(f"Transcription results saved to {self.output_json_path}")
            logger.info(f"Transcription output type: {type(transcription_output)}, Sample: {transcription_output[:1]}")
            return transcription_output  # Return list of dictionaries instead of string
        except APIError as e:
            logger.error(f"Groq API error during transcription: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise
        finally:
            if os.path.exists(self.compressed_audio_path):
                await asyncio.to_thread(os.remove, self.compressed_audio_path)
