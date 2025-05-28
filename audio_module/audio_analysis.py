import json
import re
import statistics
import math
import numpy as np
import librosa
import warnings
from pydub import AudioSegment
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder
import joblib
import speech_recognition as sr

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

def label_encoder(label): 
    mapping = {
        "low": 0,
        "neutral": 1,
        "high": 2
    }
    try:
        return mapping[label.lower()]
    except KeyError:
        raise ValueError(f"Invalid label '{label}'. Expected one of: {list(mapping.keys())}")

# Tone model paths (adjust if needed)
TONE_MODEL_PATH = r"D:\SOME_UPDATED\SOME_\audio_module\model.h5"

# Attempt to load the pretrained tone model
try:
    tone_model = load_model(TONE_MODEL_PATH)
    print("Tone model loaded successfully.")
except Exception as e:
    print("Tone model not loaded:", e)
    tone_model = None

def extract_mfcc(audio_path, max_len=40):
    signal, sample_rate = librosa.load(audio_path, sr=None, mono=True)
    mfcc = librosa.feature.mfcc(y=signal, sr=sample_rate, n_mfcc=13)
    if mfcc.shape[1] < max_len:
        pad_width = max_len - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    else:
        mfcc = mfcc[:, :max_len]
    # Do NOT take the mean; keep the 2D shape [n_mfcc, max_len]
    return mfcc

def predict_emotion(audio_path, model):
    mfcc_2d = extract_mfcc(audio_path, max_len=40)  # Shape: [13, 40]
    mfcc_4d = mfcc_2d[np.newaxis, ..., np.newaxis]  # Shape: [1, 13, 40, 1]
    predictions = model.predict(mfcc_4d)
    class_index = np.argmax(predictions, axis=-1)[0]
    reverse_mapping = {0: "low", 1: "neutral", 2: "high"}
    predicted_label = reverse_mapping[class_index]
    return predicted_label

def predict_tone(audio_path: str):
    if tone_model is None:
        print("Tone model missing; using default tone 'neutral'.")
        return "neutral"
    predicted_emotion = predict_emotion(audio_path, tone_model)
    return predicted_emotion

def get_volume_metrics(audio_path):
    y, sample_rate = librosa.load(audio_path, sr=None, mono=True)
    rms_energy = librosa.feature.rms(y=y)[0]
    avg_volume = 20 * np.log10(np.mean(rms_energy) + 1e-6)
    vol_std = 20 * np.log10(np.std(rms_energy) + 1e-6)
    return avg_volume, vol_std

def get_speaking_speed(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
    try:
        transcription = recognizer.recognize_google(audio_data)
        words = transcription.split()
        y, sample_rate = librosa.load(audio_path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sample_rate)
        wpm = (len(words) / duration) * 60 if duration > 0 else 0
        print(f"Transcription: {transcription}")
    except sr.UnknownValueError:
        print("Speech Recognition could not understand audio.")
        wpm = 0
    except Exception as e:
        print("Error in speech recognition:", e)
        wpm = 0
    return wpm

def analyze_audio_metrics(audio_path, transcription_json_path, segment_duration_ms=5000):
    """
    Analyze the audio file to compute:
      - Average volume (dBFS) and its standard deviation over segments.
      - Speaking speed (words per minute) computed from transcription JSON.
      - Predicted tone using the pretrained model.
    
    Returns a dictionary with:
      "average_volume": float,
      "volume_std": float,
      "speaking_speed": float,
      "predicted_tone": str
    """
    audio = AudioSegment.from_file(audio_path)
    average_volume = float(audio.dBFS)
    
    volumes = []
    for i in range(0, len(audio), segment_duration_ms):
        segment = audio[i:i+segment_duration_ms]
        v = float(segment.dBFS)
        if math.isfinite(v):
            volumes.append(v)
    volume_std = statistics.stdev(volumes) if len(volumes) > 1 else 0

    with open(transcription_json_path, 'r') as f:
        transcription_data = json.load(f)
    full_text = " ".join(seg.get("text", "") for seg in transcription_data)
    total_words = len(re.findall(r'\w+', full_text))
    speaking_time_seconds = sum(seg.get("end", 0) - seg.get("start", 0) for seg in transcription_data)
    speaking_time_minutes = speaking_time_seconds / 60 if speaking_time_seconds > 0 else 1
    words_per_minute = total_words / speaking_time_minutes

    predicted_tone = predict_tone(audio_path)
    speaking_speed = words_per_minute

    audio_metric = {
        "average_volume": round(average_volume, 2),
        "volume_std": round(volume_std, 2),
        "speaking_speed": round(speaking_speed, 2),
        "predicted_tone": predicted_tone
    }
    with open("json/audio_metrics.json", 'w') as fp:
        json.dump(audio_metric, fp=fp)

    return str(audio_metric)

if __name__ == '__main__':
    test_audio_path = "audio/audio.wav"
    test_transcription = "json/transcription_output.json"
    metrics = analyze_audio_metrics(test_audio_path, test_transcription)
    print("Audio Analysis Metrics:")
    print(metrics)
    tone = predict_tone(test_audio_path)
    print("Predicted Tone:", tone)