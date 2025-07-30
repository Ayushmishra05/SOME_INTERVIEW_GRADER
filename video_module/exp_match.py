"""
Expression ↔ Speech Match  –  MediaPipe Edition
==============================================

Analyzes a video and transcript to compute the average match score (1–5 scale)
indicating how well the speaker’s facial expressions fit the sentiment of their speech.

Dependencies
------------
pip install mediapipe==0.10.* opencv-python torch transformers pandas tqdm
"""

from __future__ import annotations
import os, sys, types, importlib.util, json, math, re, urllib.request, shutil
from pathlib import Path
from collections import defaultdict
from tempfile import gettempdir
from tqdm import tqdm
import cv2, mediapipe as mp, numpy as np, pandas as pd, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

# -------------------------------------------------------------------------
#  0.  Nuke TensorFlow / JAX and clean environment
# -------------------------------------------------------------------------
os.environ["MEDIAPIPE_DISABLE_TENSORFLOW_MODULES"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["TRANSFORMERS_NO_JAX"] = "1"
if "PYTHONPATH" in os.environ:
    del os.environ["PYTHONPATH"]

for _name in ("tensorflow", "jax"):
    mod = types.ModuleType(_name)
    mod.__spec__ = importlib.machinery.ModuleSpec(name=_name, loader=None)
    sys.modules[_name] = mod

_orig_find_spec = importlib.util.find_spec
def _no_tf_find_spec(name, *a, **k):
    if name == "tensorflow":
        return None
    return _orig_find_spec(name, *a, **k)
importlib.util.find_spec = _no_tf_find_spec

# -------------------------------------------------------------------------
#  1.  Transcript parser
# -------------------------------------------------------------------------
_PATTERN = re.compile(
    r"^\s*\[?(?P<start>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\]?\s*(?P<text>.*)$"
)

def _as_seconds(ts: str) -> float:
    ts = ts.replace(",", ":").replace(".", ":")
    h, m, s, ms = [0.0] * (4 - len(parts := [float(p) for p in ts.split(":")])) + parts
    return h * 3600 + m * 60 + s + ms / 1000

def parse_transcript(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if m := _PATTERN.match(ln):
                d = m.groupdict()
                rows.append(
                    {
                        "start": _as_seconds(d["start"]),
                        "end": _as_seconds(d["end"]),
                        "text": d["text"].strip(),
                    }
                )
    return pd.DataFrame(rows, columns=["start", "end", "text"])

# -------------------------------------------------------------------------
#  2.  Simple valence functions
# -------------------------------------------------------------------------
_POS_BS = {"smile", "cheekPuff", "cheekSquint", "eyeSquint", "eyeWide", "jawOpen"}
_NEG_BS = {"browDown", "browInnerUp", "mouthFrown", "mouthDimple", "noseSneer"}

def blend_valence(blendshapes) -> float:
    pos = sum(b.score for b in blendshapes if any(p in b.category_name for p in _POS_BS))
    neg = sum(b.score for b in blendshapes if any(n in b.category_name for n in _NEG_BS))
    total = pos + neg
    return 0.0 if total == 0 else (pos - neg) / total  # ∈ [-1,1]

# -------------------------------------------------------------------------
#  3.  Ensure Face-Landmarker model present
# -------------------------------------------------------------------------
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL_NAME = "face_landmarker.task"

def _get_model_path() -> Path:
    """Set up and validate the model path, with fallback to script directory."""
    temp_model_path = Path(gettempdir()) / MODEL_NAME
    script_dir = Path(__file__).parent
    local_model_path = script_dir / MODEL_NAME

    def download_model(target_path: Path):
        print(f"Downloading Face Landmarker model (~27 MB) to: {target_path}")
        try:
            with urllib.request.urlopen(MODEL_URL) as resp, open(target_path, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0))
                with tqdm(total=total, unit="B", unit_scale=True, desc="model") as pbar:
                    for chunk in iter(lambda: resp.read(65536), b""):
                        out.write(chunk)
                        pbar.update(len(chunk))
            if not target_path.exists() or target_path.stat().st_size < 1000:
                raise FileNotFoundError(f"Model download failed or file is corrupt at {target_path}")
            print(f"Model successfully downloaded to: {target_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to download model: {str(e)}") from e

    # Try temp directory first
    model_path = temp_model_path
    try:
        if not model_path.exists() or model_path.stat().st_size < 1000:
            print(f"Model not found or corrupt at {model_path}. Attempting download...")
            download_model(model_path)
    except Exception as e:
        print(f"Failed to use temp directory model: {e}. Falling back to script directory...")
        model_path = local_model_path
        try:
            if not model_path.exists() or model_path.stat().st_size < 1000:
                print(f"Model not found or corrupt at {model_path}. Attempting download...")
                download_model(model_path)
        except Exception as e:
            raise RuntimeError(f"Unable to set up model file: {str(e)}") from e

    model_path = model_path.resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found at {model_path}")
    print(f"Using model path: {model_path}")
    return model_path

# Initialize MODEL_PATH
try:
    MODEL_PATH = _get_model_path()
except Exception as e:
    print(f"Error: Failed to initialize model path: {str(e)}")
    MODEL_PATH = None

# -------------------------------------------------------------------------
#  4.  Main analysis function
# -------------------------------------------------------------------------
def analyze_video_smile(video_path: Path, transcript_path: Path, window: float = 1.0, device: str = "cpu") -> float:
    """
    Analyze a video and transcript to compute the average match score (1–5 scale)
    for how well facial expressions fit speech sentiment.

    Args:
        video_path: Path to the video file (MP4, AVI, etc.).
        transcript_path: Path to the bracket-style transcript file.
        window: Bin size in seconds for matching expressions to speech.
        device: Device for the text model ("cpu" or "cuda").

    Returns:
        float: Average match score (1–5 scale) across all time bins.
    """
    print(f"Starting analysis of: {video_path}")
    print(f"Device set to use: {device}")
    print(f"Current working directory: {os.getcwd()}")

    if MODEL_PATH is None:
        print("Error: Model path not initialized. Cannot proceed with analysis.")
        return 0.0

    # ---- Text model (Go-Emotions) ----
    try:
        tok = AutoTokenizer.from_pretrained("SamLowe/roberta-base-go_emotions")
        model = AutoModelForSequenceClassification.from_pretrained("SamLowe/roberta-base-go_emotions")
        clf = pipeline("text-classification", model=model, tokenizer=tok,
                       device=0 if device == "cuda" else -1, top_k=None)
    except Exception as e:
        print(f"Error: Failed to load Go-Emotions model: {str(e)}")
        return 0.0

    try:
        df = parse_transcript(transcript_path)
    except Exception as e:
        print(f"Error: Failed to parse transcript {transcript_path}: {str(e)}")
        return 0.0

    def sent_val(txt):
        res = clf(txt)[0]
        pos = sum(s["score"] for s in res if s["label"] in
                  {"joy", "love", "optimism", "admiration", "approval"})
        neg = sum(s["score"] for s in res if s["label"] in
                  {"anger", "disapproval", "disgust", "sadness", "fear", "confusion"})
        tot = pos + neg or 1.0
        return (pos - neg) / tot

    df["valence"] = df["text"].apply(sent_val)

    # ---- MediaPipe Face Landmarker ----
    BaseOpts = mp.tasks.BaseOptions
    VisionRM = mp.tasks.vision.RunningMode
    FaceLM = mp.tasks.vision.FaceLandmarker

    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=BaseOpts(model_asset_path=str(MODEL_PATH)),
        output_face_blendshapes=True,
        running_mode=VisionRM.IMAGE,
        num_faces=1,
    )
    try:
        lm = FaceLM.create_from_options(opts)
    except Exception as e:
        print(f"Error: Failed to initialize Face Landmarker with model at {MODEL_PATH}: {str(e)}")
        return 0.0

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            lm.close()
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        bin_frames = int(window * fps)

        bins: dict[int, list[float]] = defaultdict(list)
        idx = 0
        with tqdm(desc="Processing frames") as pbar:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
                res = lm.detect(mp_img)
                if res.face_blendshapes:
                    bins[idx // bin_frames].append(blend_valence(res.face_blendshapes[0]))
                idx += 1
                pbar.update(1)

        cap.release()
        lm.close()

        n_bins = max(bins.keys(), default=-1) + 1
        if n_bins <= 0:
            print("Error: No valid face blendshapes detected")
            return 0.0

        v = np.array([np.mean(bins[i]) if bins[i] else 0.0 for i in range(n_bins)])
        t = np.zeros(n_bins)
        for _, r in df.iterrows():
            b0, b1 = int(r.start // window), int(r.end // window) + 1
            t[b0:b1] = r.valence

        diff = np.abs(v - t)
        scaled = 1 + 4 * (1 - (diff - diff.min()) / (diff.max() - diff.min() + 1e-6))
        match_scores = np.rint(scaled).astype(int)

        avg_match_score = np.mean(match_scores) if match_scores.size > 0 else 0.0
        print(f"Average match score: {avg_match_score:.2f}/5 (bins = {n_bins}, window = {window}s)")
        return avg_match_score

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        if 'cap' in locals():
            cap.release()
        if 'lm' in locals():
            lm.close()
        return 0.0

# -------------------------------------------------------------------------
# #  5.  Example usage
# # -------------------------------------------------------------------------
# if __name__ == "__main__":
#     video_file = Path(r"D:\SOME_UPDATED\SOME_\static\uploads\Nishant_Sharma_22386[1] (2).mp4")
#     transcript_file = Path(r"path\to\transcript.txt")  # Replace with actual transcript path
#     avg_score = analyze_video_file(video_file, transcript_file, window=1.0, device="cpu")

# # -------------------------------------------------------------------------
# #  5.  Example usage
# # # -------------------------------------------------------------------------
# if __name__ == "__main__":
#     video_file = Path(r"D:\SOME_UPDATED\SOME_\static\uploads\Nishant_Sharma_22386[1] (2).mp4")
#     transcript_file = Path(r"json/transcription_output.json")  # Replace with actual transcript path
#     avg_score = analyze_video_file(video_file, transcript_file, window=1.0, device="cpu")