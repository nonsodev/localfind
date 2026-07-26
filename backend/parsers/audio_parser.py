"""
audio_parser.py — Parse audio files by transcribing them with Whisper.

Returns transcript text for embedding and indexing.
"""
import librosa
from pathlib import Path


def parse_audio(file_path: str) -> str:
    """
    Parse audio file by transcribing it.
    
    This is a placeholder that will be called by multimodal_indexer.
    The actual transcription happens in audio_transcriber.py.
    
    Args:
        file_path: Path to audio file
    
    Returns:
        Empty string (transcription handled separately)
    """
    # This function is kept for compatibility but not used
    # Transcription is handled in multimodal_indexer.py
    return ""


def get_audio_metadata(file_path: str) -> dict:
    """
    Extract audio file metadata.
    
    Args:
        file_path: Path to audio file
    
    Returns:
        Dict with duration, sample_rate, channels
    """
    try:
        # Load audio to get metadata (doesn't load full audio into memory)
        duration = librosa.get_duration(path=file_path)
        
        # Get sample rate and channels
        y, sr = librosa.load(file_path, sr=None, mono=False, duration=1.0)
        
        channels = 1 if y.ndim == 1 else y.shape[0]
        
        return {
            "duration_seconds": round(duration, 2),
            "sample_rate": sr,
            "channels": channels,
            "format": Path(file_path).suffix[1:].upper(),
        }
    except Exception as e:
        print(f"  ⚠️  Failed to extract audio metadata: {e}")
        return {
            "duration_seconds": None,
            "sample_rate": None,
            "channels": None,
            "format": Path(file_path).suffix[1:].upper(),
        }
