"""
audio_transcriber.py — Local audio transcription using faster-whisper.

Uses OpenAI's Whisper medium model running 100% locally.
No audio data leaves the machine.
"""
import os
import json
from pathlib import Path
from typing import Optional
import torch
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE
from logging_config import get_logger

log = get_logger("audio")

# ── Config ─────────────────────────────────────────────────────────────────

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"

# Model singleton
_whisper_model: Optional[WhisperModel] = None


# ── Model Loading ──────────────────────────────────────────────────────────

def get_whisper_model() -> WhisperModel:
    """
    Load faster-whisper model (singleton).
    
    Downloads model on first run (~1.5GB for medium).
    Subsequent runs load from cache instantly.
    """
    global _whisper_model
    if _whisper_model is None:
        log.info(f"🔄 Loading Whisper {WHISPER_MODEL_SIZE} model...")
        log.info(f"   Device: {DEVICE}, Compute: {COMPUTE_TYPE}")
        if DEVICE == "cpu":
            log.warning("Running on CPU — transcription will be slower")
            log.info("   💡 For faster transcription, use a machine with CUDA GPU")
        
        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            download_root=None,  # Uses default cache: ~/.cache/huggingface/
        )
        log.info(f"✓ Whisper {WHISPER_MODEL_SIZE} loaded")
    
    return _whisper_model


# ── Transcription ──────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str, language: str = None) -> dict:
    """
    Transcribe audio file using faster-whisper.
    
    Args:
        audio_path: Path to audio file (wav, mp3, m4a, mp4)
        language: Optional language code (e.g., "en", "es"). Auto-detected if None.
    
    Returns:
        {
            "text": "Full transcript...",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.2,
                    "text": "Hello world"
                },
                ...
            ],
            "language": "en",
            "duration": 120.5
        }
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    model = get_whisper_model()
    
    log.info(f"  → Transcribing with Whisper {WHISPER_MODEL_SIZE}...")
    
    # Transcribe
    # beam_size=5 is a good balance between speed and accuracy
    # vad_filter=True removes silence, improving accuracy
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    
    # Convert generator to list and extract data
    segments_list = []
    full_text = []
    
    for segment in segments:
        segments_list.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        })
        full_text.append(segment.text.strip())
    
    result = {
        "text": " ".join(full_text),
        "segments": segments_list,
        "language": info.language,
        "duration": info.duration if hasattr(info, 'duration') else None,
    }
    
    log.info(f"  ✓ Transcribed: {len(segments_list)} segments, "
          f"{len(result['text'])} chars, language: {info.language}")
    
    return result


def save_transcript(audio_path: str, transcript: dict) -> str:
    """
    Save transcript as JSON file next to audio file.
    
    Args:
        audio_path: Original audio file path
        transcript: Transcript dict from transcribe_audio()
    
    Returns:
        Path to saved transcript JSON file
    """
    transcript_path = f"{audio_path}.transcript.json"
    
    # Add source file to transcript
    transcript_with_meta = {
        "source_audio": audio_path,
        "source_filename": Path(audio_path).name,
        **transcript
    }
    
    with open(transcript_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_with_meta, f, indent=2, ensure_ascii=False)
    
    log.info(f"  ✓ Saved transcript: {transcript_path}")
    return transcript_path


def load_transcript(audio_path: str) -> Optional[dict]:
    """
    Load existing transcript JSON if it exists.
    
    Args:
        audio_path: Original audio file path
    
    Returns:
        Transcript dict or None if not found
    """
    transcript_path = f"{audio_path}.transcript.json"
    
    if not os.path.exists(transcript_path):
        return None
    
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load transcript: {e}")
        return None


def transcribe_and_save(audio_path: str, force: bool = False) -> dict:
    """
    Transcribe audio and save transcript, or load existing transcript.
    
    Args:
        audio_path: Path to audio file
        force: If True, re-transcribe even if transcript exists
    
    Returns:
        Transcript dict
    """
    # Check for existing transcript
    if not force:
        existing = load_transcript(audio_path)
        if existing:
            log.info(f"  → Using cached transcript")
            return existing
    
    # Transcribe
    transcript = transcribe_audio(audio_path)
    
    # Save
    save_transcript(audio_path, transcript)
    
    return transcript


# ── Utility Functions ──────────────────────────────────────────────────────

def format_timestamp(seconds: float) -> str:
    """
    Format seconds as MM:SS or HH:MM:SS.
    
    Args:
        seconds: Time in seconds
    
    Returns:
        Formatted string like "01:23" or "1:23:45"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_segment_at_time(transcript: dict, time: float) -> Optional[dict]:
    """
    Get the segment that contains a specific timestamp.
    
    Args:
        transcript: Transcript dict from transcribe_audio()
        time: Time in seconds
    
    Returns:
        Segment dict or None if not found
    """
    for segment in transcript["segments"]:
        if segment["start"] <= time <= segment["end"]:
            return segment
    return None


# ── Testing ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        log.info("Usage: python audio_transcriber.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    log.info(f"Transcribing: {audio_file}")
    transcript = transcribe_and_save(audio_file)
    
    log.info("\n" + "="*60)
    log.info("TRANSCRIPT")
    log.info("="*60)
    log.info(f"Language: {transcript['language']}")
    log.info(f"Duration: {transcript.get('duration', 'unknown')}s")
    log.info(f"Segments: {len(transcript['segments'])}")
    log.info("\n" + transcript['text'])
    log.info("\n" + "="*60)
    log.info("SEGMENTS")
    log.info("="*60)
    for seg in transcript['segments'][:5]:  # Show first 5
        log.info(f"[{format_timestamp(seg['start'])} → {format_timestamp(seg['end'])}] {seg['text']}")
    if len(transcript['segments']) > 5:
        log.info(f"... and {len(transcript['segments']) - 5} more segments")
