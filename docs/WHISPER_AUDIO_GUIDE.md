# Audio Transcription with Whisper - Complete Guide

## 🎙️ Overview

The system now uses **OpenAI's Whisper** (via faster-whisper) to transcribe audio files locally. This allows you to search for **spoken content** in audio files, not just sound characteristics.

### What This Enables

- Audio → Transcribe with Whisper → Text embeddings → Search spoken content
- Example: "machine learning" finds audio where those words were spoken
- Benefit: full-text-style retrieval across meetings, podcasts, and lectures

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
uv pip install -r requirements.txt
```

### 2. Install ffmpeg (System Level)

**macOS**:
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
- **Fastest**: Run `winget install ffmpeg` in PowerShell.
- **Manual**: Download from https://ffmpeg.org/download.html, extract, and add the `bin` folder to your System PATH.
- **Verification**: Run `ffmpeg -version` in a new terminal.

### 3. GPU Acceleration (Optional but Highly Recommended)

Whisper transcription is **10-20x faster** on a GPU.

**NVIDIA GPU (Windows/Linux)**:
```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**Apple Silicon (macOS)**:
Uses MPS (Metal Performance Shaders) automatically.

### 4. Start Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first run, Whisper will download the model (~1.5GB for medium).

### 4. Index Audio Files

1. Go to frontend: `http://localhost:5173`
2. Navigate to "Folders" tab
3. Add folder containing audio files
4. Click "Sync"
5. Watch transcription progress in backend logs

## 📊 How It Works

### Architecture

```
Audio File (podcast.mp3)
    ↓
Transcribe with Whisper medium
    ↓
Full Transcript + Timestamps
    [0:00-0:30] "Welcome to the show..."
    [0:30-1:00] "Today we discuss AI..."
    [1:00-1:30] "Machine learning has..."
    ↓
Chunk Transcript (semantic, like PDFs)
    Chunk 1: "Welcome to the show... Today we discuss AI..."
    Chunk 2: "Today we discuss AI... Machine learning has..."
    ↓
Embed Chunks with Ollama (text embeddings)
    ↓
Store in ChromaDB with metadata:
    - text: chunk content
    - start_time: 0.0
    - end_time: 60.0
    - audio_file: path
    - language: "en"
```

### Search Flow

```
User searches: "machine learning"
    ↓
Embed query with Ollama (text embedding)
    ↓
Search audio_transcripts collection
    ↓
Find matching transcript chunks
    ↓
Return results with:
    - Transcript snippet
    - Audio file path
    - Time range (start_time, end_time)
    - Language detected
    ↓
Frontend displays:
    - Audio player
    - Highlighted matched segment (green box)
    - Timestamp range
    - Full transcript text
```

## 🎯 Features

### 1. **Automatic Transcription**
- Runs on first index
- Cached for subsequent syncs
- Saved as `.transcript.json` next to audio file

### 2. **Semantic Chunking**
- Transcript chunked like PDF text (500 chars, 80 char overlap)
- Preserves context across chunk boundaries
- Each chunk tracks its time range

### 3. **Time-Stamped Results**
- Every result shows exact time range
- Jump to specific moment in audio
- Highlighted matched segment in UI

### 4. **Language Detection**
- Whisper auto-detects language
- Supports 99+ languages
- Stored in metadata

### 5. **Full Transcript Storage**
- Complete transcript saved as JSON
- Includes all segments with timestamps
- Can be viewed/exported separately

## 📁 File Structure

### Transcript JSON Format

When you index `podcast.mp3`, a `podcast.mp3.transcript.json` file is created:

```json
{
  "source_audio": "/path/to/podcast.mp3",
  "source_filename": "podcast.mp3",
  "text": "Welcome to the show. Today we discuss machine learning...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Welcome to the show."
    },
    {
      "start": 5.2,
      "end": 12.8,
      "text": "Today we discuss machine learning and its applications."
    },
    ...
  ],
  "language": "en",
  "duration": 1800.5
}
```

### ChromaDB Storage

**Collection**: `localfind_audio_transcripts`

**Each chunk**:
```python
{
    "id": "path_to_audio__chunk0",
    "embedding": [0.23, -0.45, ...],  # 768 dimensions (Ollama)
    "document": "Welcome to the show. Today we discuss...",
    "metadata": {
        "source": "/path/to/podcast.mp3",
        "file_name": "podcast.mp3",
        "modality": "audio_transcript",
        "chunk_index": 0,
        "start_time": 0.0,
        "end_time": 60.5,
        "language": "en",
        "duration": 1800.5,
        "folder_id": 1
    }
}
```

## 🔧 Configuration

### Model Selection

In `audio_transcriber.py`:

```python
WHISPER_MODEL_SIZE = "medium"  # Options: tiny, base, small, medium, large
```

**Model Comparison**:

| Model  | Size  | Speed | Accuracy | Use Case |
|--------|-------|-------|----------|----------|
| tiny   | 75MB  | 32x   | Good     | Quick tests |
| base   | 142MB | 16x   | Better   | Fast transcription |
| small  | 466MB | 6x    | Great    | Balanced |
| **medium** | **1.5GB** | **2x** | **Excellent** | **Recommended** |
| large  | 2.9GB | 1x    | Best     | Maximum accuracy |

### Device Selection

```python
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
```

**Performance**:
- **GPU (CUDA)**: ~10-20x faster than CPU
- **CPU (int8)**: Slower but works on any machine
- **Apple Silicon**: Uses CPU with optimizations

### Chunking Configuration

In `multimodal_indexer.py`:

```python
CHUNK_SIZE = 500  # Characters per chunk
CHUNK_OVERLAP = 80  # Overlap between chunks
```

## 🎨 UI Features

### Audio Result Card

When you search and find audio results:

1. **Audio Player**
   - Play/pause controls
   - Seek bar
   - Volume control

2. **Matched Segment Box** (Green/Purple highlight)
   - Shows exact time range
   - Displays matched transcript text
   - Formatted timestamps (MM:SS)

3. **Metadata Badges**
   - Total duration
   - Language detected
   - File format

4. **Clickable File Path**
   - Opens audio file in system player
   - Hover to see full path

## 📝 Usage Examples

### Example 1: Podcast Search

**Scenario**: You have 50 podcast episodes and want to find where "neural networks" was discussed.

```
1. Index podcast folder
2. Search: "neural networks"
3. Results show:
   - Episode 23: [12:30 → 15:45] "...neural networks are..."
   - Episode 31: [08:15 → 10:20] "...deep neural networks..."
4. Click play, audio starts at matched segment
```

### Example 2: Meeting Recordings

**Scenario**: Find action items from team meetings.

```
1. Index meetings folder
2. Search: "action item" or "to-do" or "follow up"
3. Results show exact moments when tasks were assigned
4. Export transcript for meeting notes
```

### Example 3: Lecture Notes

**Scenario**: Search across recorded lectures for specific topics.

```
1. Index lecture recordings
2. Search: "quantum mechanics" or "thermodynamics"
3. Jump to exact explanation in lecture
4. Review transcript for study notes
```

## ⚡ Performance

### Transcription Speed

**CPU (Apple M1/M2)**:
- ~1-2x realtime (1 hour audio = 30-60 min transcription)

**CPU (Intel i7)**:
- ~0.5-1x realtime (1 hour audio = 60-120 min transcription)

**GPU (CUDA)**:
- ~10-20x realtime (1 hour audio = 3-6 min transcription)

### Search Speed

- **Text search in transcripts**: ~30-50ms
- Same speed as PDF text search
- Instant once indexed

### Storage

- **Audio file**: Original size (unchanged)
- **Transcript JSON**: ~1-2KB per minute of audio
- **ChromaDB embeddings**: ~2KB per chunk

Example: 1 hour podcast
- Audio: 50MB (MP3)
- Transcript: 60-120KB
- Embeddings: ~20KB
- **Total overhead**: ~80-140KB (0.16% of audio size)

## 🐛 Troubleshooting

### Issue: Whisper Model Download Fails

**Symptoms**: "Failed to download model" error

**Solutions**:
1. Check internet connection
2. Verify disk space (~2GB free)
3. Check firewall/proxy settings
4. Manual download:
   ```bash
   python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
   ```

### Issue: Transcription is Slow

**Symptoms**: Taking hours to transcribe

**Solutions**:
1. Use smaller model (base or small)
2. Check CPU usage (should be 100%)
3. Close other applications
4. Consider GPU if available

### Issue: Poor Transcription Quality

**Symptoms**: Incorrect words, gibberish

**Solutions**:
1. Check audio quality (clear speech, low noise)
2. Use larger model (large instead of medium)
3. Specify language manually:
   ```python
   transcribe_audio(path, language="en")
   ```
4. Pre-process audio (noise reduction, normalization)

### Issue: Empty Transcripts

**Symptoms**: "Empty transcript, skipping"

**Solutions**:
1. Verify audio file plays correctly
2. Check audio format is supported
3. Ensure audio contains speech (not just music/noise)
4. Try different audio file

### Issue: Wrong Language Detected

**Symptoms**: Transcript in wrong language

**Solutions**:
1. Specify language explicitly in `audio_transcriber.py`:
   ```python
   transcript = transcribe_audio(audio_path, language="en")
   ```
2. Use larger model (better language detection)

## 🔬 Advanced Usage

### Manual Transcription

Test transcription on a single file:

```bash
cd backend
python audio_transcriber.py /path/to/audio.mp3
```

Output:
```
Transcribing: /path/to/audio.mp3
🔄 Loading Whisper medium model...
✓ Whisper medium loaded
  → Transcribing with Whisper medium...
  ✓ Transcribed: 45 segments, 2341 chars, language: en
  ✓ Saved transcript: /path/to/audio.mp3.transcript.json

============================================================
TRANSCRIPT
============================================================
Language: en
Duration: 180.5s
Segments: 45

Welcome to the podcast. Today we're discussing...
[full transcript]

============================================================
SEGMENTS
============================================================
[00:00 → 00:05] Welcome to the podcast.
[00:05 → 00:12] Today we're discussing machine learning.
...
```

### Batch Transcription

Transcribe all audio files in a folder:

```python
import os
from audio_transcriber import transcribe_and_save

audio_folder = "/path/to/audio/files"
for file in os.listdir(audio_folder):
    if file.endswith(('.mp3', '.wav', '.m4a')):
        path = os.path.join(audio_folder, file)
        print(f"Transcribing: {file}")
        transcribe_and_save(path)
```

### Export Transcripts

Extract all transcripts to text files:

```python
import json
import glob

for transcript_file in glob.glob("**/*.transcript.json", recursive=True):
    with open(transcript_file) as f:
        data = json.load(f)
    
    txt_file = transcript_file.replace('.transcript.json', '.txt')
    with open(txt_file, 'w') as f:
        f.write(data['text'])
    
    print(f"Exported: {txt_file}")
```

## 🎓 Best Practices

### 1. **Audio Quality Matters**
- Clear speech > background music
- Good microphone > phone recording
- Quiet environment > noisy cafe

### 2. **Choose Right Model**
- Start with `medium` (best balance)
- Use `small` if speed critical
- Use `large` if accuracy critical

### 3. **Organize Audio Files**
- Group by topic/project in folders
- Use descriptive filenames
- Keep original audio files

### 4. **Monitor Transcription**
- Check backend logs for errors
- Verify transcript quality on samples
- Re-transcribe if needed (delete .transcript.json)

### 5. **Search Tips**
- Use specific terms ("neural networks" not "AI")
- Try synonyms if no results
- Check language matches audio

## 🔮 Future Enhancements

Potential improvements:

1. **Speaker Diarization**: Identify who said what
2. **Keyword Extraction**: Auto-tag important topics
3. **Summary Generation**: AI-generated summaries
4. **Sentiment Analysis**: Detect tone/emotion
5. **Multi-language Support**: Better language handling
6. **Real-time Transcription**: Live audio indexing
7. **Audio Editing**: Clip/export matched segments

## 📞 Support

### Common Questions

**Q: Does audio search work on spoken content or sound effects?**
A: The current pipeline is transcript-based, so it works best for spoken content rather than raw sound-effect similarity.

**Q: Does this work offline?**
A: Yes! 100% local, no internet needed after model download.

**Q: What audio formats are supported?**
A: MP3, WAV, FLAC, M4A, OGG, AAC, MP4 (audio track)

**Q: Can I transcribe video files?**
A: Yes! Whisper extracts audio from MP4/video files automatically.

**Q: How accurate is Whisper?**
A: Very accurate for clear speech. ~95%+ word accuracy with medium model.

**Q: Can I edit transcripts?**
A: Yes! Edit the `.transcript.json` file and re-index.

---

**Status**: ✅ Fully Implemented
**Last Updated**: May 11, 2026
**Version**: 2.1 (Whisper-based Audio)
