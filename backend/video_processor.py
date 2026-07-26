"""
video_processor.py — Turn a video file into a set of keyframes for indexing.

A video is indexed as two things LocalFind already understands:
  1. Keyframes — still images sampled at scene changes, each captioned like a
     photo by the vision model (see multimodal_indexer.upsert_video).
  2. Speech — the audio track transcribed by Whisper (see audio_transcriber).

This module only handles (1): pulling a small, meaningful set of frames out of
the video with ffmpeg, each tagged with its timestamp. We use scene-change
detection so that long static footage doesn't produce hundreds of near-identical
frames — a 10-minute video typically yields a few dozen keyframes, not hundreds.

Requires ffmpeg/ffprobe on PATH (already a documented prerequisite).
"""
import os
import re
import glob
import shutil
import subprocess

from logging_config import get_logger

log = get_logger("video")

VIDEO_EXTENSIONS = {
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".webm": "video",
    ".avi": "video",
    ".m4v": "video",
}


def ffmpeg_available() -> bool:
    """True if both ffmpeg and ffprobe are callable."""
    return bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))


def get_video_duration(video_path: str) -> float:
    """Duration in seconds via ffprobe, or 0.0 if it can't be determined."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=60,
        )
        return float(out.stdout.strip())
    except (ValueError, subprocess.SubprocessError) as e:
        log.warning("Could not read duration of %s: %s", os.path.basename(video_path), e)
        return 0.0


def _downsample(items: list, max_items: int) -> list:
    """Evenly pick at most max_items from a list, preserving order."""
    if max_items <= 0 or len(items) <= max_items:
        return items
    step = len(items) / max_items
    return [items[int(i * step)] for i in range(max_items)]


def _apply_min_gap(frames: list[tuple[float, str]], min_gap: float) -> list[tuple[float, str]]:
    """Drop frames closer than min_gap seconds to the previously kept one."""
    if min_gap <= 0:
        return frames
    kept: list[tuple[float, str]] = []
    last_t = None
    for ts, path in frames:
        if last_t is None or (ts - last_t) >= min_gap:
            kept.append((ts, path))
            last_t = ts
        else:
            # too close to the previous keyframe — discard the file
            try:
                os.remove(path)
            except OSError:
                pass
    return kept


def _extract_scene_frames(video_path: str, out_dir: str, scene_threshold: float) -> list[tuple[float, str]]:
    """
    Run ffmpeg's scene filter, writing one JPEG per detected scene change.

    The `showinfo` filter prints a `pts_time:<seconds>` line to stderr for every
    frame it emits, in the same order the files are written, so we pair sorted
    output files with parsed timestamps positionally.
    """
    pattern = os.path.join(out_dir, "frame_%05d.jpg")
    # eq(n,0) always keeps the very first frame (scene detection skips frame 0).
    vf = f"select='eq(n\\,0)+gt(scene\\,{scene_threshold})',showinfo"
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostdin", "-y",
            "-i", video_path,
            "-vf", vf,
            "-vsync", "vfr",
            "-qscale:v", "3",
            pattern,
        ],
        capture_output=True, text=True, timeout=900,
    )
    times = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", proc.stderr)]
    files = sorted(glob.glob(os.path.join(out_dir, "frame_*.jpg")))
    # Pair positionally; tolerate a length mismatch by zipping to the shorter.
    return [(round(t, 2), f) for t, f in zip(times, files)]


def _extract_interval_frames(video_path: str, out_dir: str, count: int) -> list[tuple[float, str]]:
    """
    Fallback for videos where scene detection finds nothing (very static or very
    short clips): grab `count` frames at even intervals, each seeked individually.
    """
    duration = get_video_duration(video_path)
    if duration <= 0:
        count = 1
        duration = 1.0
    frames: list[tuple[float, str]] = []
    for i in range(count):
        ts = duration * (i + 0.5) / count
        out_path = os.path.join(out_dir, f"frame_i{i:05d}.jpg")
        proc = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-nostdin", "-y",
                "-ss", f"{ts:.3f}", "-i", video_path,
                "-frames:v", "1", "-qscale:v", "3", out_path,
            ],
            capture_output=True, text=True, timeout=120,
        )
        if os.path.exists(out_path):
            frames.append((round(ts, 2), out_path))
    return frames


def extract_keyframes(
    video_path: str,
    out_dir: str,
    scene_threshold: float = 0.4,
    max_frames: int = 40,
    min_gap: float = 1.5,
) -> list[tuple[float, str]]:
    """
    Extract keyframes from a video.

    Returns a list of (timestamp_seconds, frame_jpeg_path), sorted by time and
    capped at max_frames. Frames are written into out_dir, which is recreated
    fresh on each call so re-indexing a changed video doesn't leave stale frames.
    """
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg/ffprobe not found on PATH — required for video indexing")

    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    log.info("Extracting keyframes from %s (scene>%.2f, max %d)",
             os.path.basename(video_path), scene_threshold, max_frames)
    frames = _extract_scene_frames(video_path, out_dir, scene_threshold)
    log.debug("Scene detection found %d frame(s)", len(frames))

    if not frames:
        # No scene changes detected — fall back to even-interval sampling.
        fallback_count = min(max_frames, 8)
        log.info("No scene changes detected — falling back to %d interval frames", fallback_count)
        frames = _extract_interval_frames(video_path, out_dir, fallback_count)

    frames.sort(key=lambda x: x[0])
    before_gap = len(frames)
    frames = _apply_min_gap(frames, min_gap)

    if len(frames) > max_frames:
        log.debug("Capping %d frames to max_frames=%d", len(frames), max_frames)
        dropped = _downsample(frames, max_frames)
        kept_paths = {p for _, p in dropped}
        for _, path in frames:
            if path not in kept_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass
        frames = dropped

    log.info("Keyframes ready: %d kept (%d before min-gap dedup)", len(frames), before_gap)
    return frames
