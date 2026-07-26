# Multimodal Agent Guide

## Overview

The LocalFind agent supports **multimodal search results**, allowing it to analyze text documents, view images, and read audio transcripts from your indexed files.

## Architecture

```
User Query
    ↓
Agent (Gemma / Ollama)
    ↓
MCP Server (search_documents tool)
    ↓
Backend API (/api/search)
    ↓
ChromaDB (3 collections)
    ↓
Results (top 2 from each modality)
    ↓
Agent analyzes:
    - Text chunks
    - Image files (can view)
    - Audio transcripts (text)
```

## Key Changes

### 1. **Multimodal Results**

The agent now receives results in three categories:

```python
{
    "query": "machine learning",
    "text_results": [
        {
            "text": "Machine learning is...",
            "file_name": "ml_intro.pdf",
            "score": 0.89,
            "chunk_index": 5
        },
        # ... up to 2 text results
    ],
    "image_results": [
        {
            "file_path": "/path/to/neural_network.png",
            "file_name": "neural_network.png",
            "score": 0.85,
            "metadata": {
                "width": 1920,
                "height": 1080,
                "format": "PNG"
            }
        },
        # ... up to 2 image results
    ],
    "audio_results": [
        {
            "text": "Today we discuss machine learning...",  # Transcript
            "file_name": "podcast_ep23.mp3",
            "score": 0.92,
            "metadata": {
                "start_time": 45.2,
                "end_time": 120.5,
                "language": "en",
                "duration": 1800.0
            }
        },
        # ... up to 2 audio results
    ],
    "total_results": {
        "text": 5,
        "images": 3,
        "audio": 2
    }
}
```

### 2. **Vision-Capable Model**

**Default**: `gemma4:e4b`

**Alternatives**:
- `llama3.1:8b` - Smaller and faster
- `mistral:7b` - Smaller general-purpose option
- Any Ollama-compatible chat model you prefer

**Install**:
```bash
ollama pull gemma4:e4b
```

### 3. **Result Limits**

- **Top K per modality**: 2 (configurable, max 5)
- **Total results**: Up to 6 (2 text + 2 images + 2 audio)
- **Rationale**: Keeps context manageable for agent

### 4. **Audio Handling**

**Important**: Audio results are **transcript text**, not audio files.

The agent receives:
- ✅ Transcript text
- ✅ Timestamps (start_time, end_time)
- ✅ Language detected
- ✅ File name
- ❌ NOT actual audio data

## Usage

### Start the Agent

```bash
cd frontend
npm run dev
```

Then open `http://localhost:5173` and switch from `Search` to `Agent`.

### Example Conversations

#### Example 1: Text Search
```
You: What is machine learning?

Agent: Based on your documents, I found information about machine learning:

From ml_intro.pdf (text):
"Machine learning is a subset of artificial intelligence that enables 
systems to learn and improve from experience..."

From podcast_ep23.mp3 (audio transcript, 0:45 - 2:00):
"Today we discuss machine learning and its applications in modern AI systems..."

Would you like me to search for more specific aspects?
```

#### Example 2: Image Search
```
You: Show me neural network diagrams

Agent: I found 2 relevant images:

1. neural_network_architecture.png (score: 0.89)
   [Agent views image]
   This diagram shows a multi-layer neural network with input layer, 
   3 hidden layers, and output layer. The connections show forward 
   propagation with weights indicated.

2. cnn_diagram.jpg (score: 0.85)
   [Agent views image]
   This is a convolutional neural network architecture diagram showing
   convolution layers, pooling layers, and fully connected layers.

Both images are from your ml_papers folder.
```

#### Example 3: Mixed Results
```
You: Tell me about quantum computing

Agent: I found information across multiple sources:

TEXT (quantum_intro.pdf):
"Quantum computing leverages quantum mechanical phenomena..."

IMAGE (qubit_diagram.png):
[Agent views image]
This diagram illustrates a qubit's superposition state on the Bloch sphere.

AUDIO (lecture_05.mp3 transcript, 12:30 - 15:45):
"In quantum computing, we use qubits instead of classical bits, 
allowing for superposition and entanglement..."

The information spans theoretical concepts (text), visual representations 
(image), and lecture explanations (audio transcript).
```

## Configuration

### Change Model

Edit `backend/config.py` or your root `.env`:

```python
AGENT_MODEL = "gemma4:e4b"
```

**Model Options**:

| Model | Approx Size | Vision | Speed | Best For |
|-------|-------------|--------|-------|----------|
| gemma4:e4b | Large | Via LocalFind image path flow | Slower | Best built-in quality |
| llama3.1:8b | Medium | Via LocalFind image path flow | Faster | Lower-resource setups |
| mistral:7b | Medium | Via LocalFind image path flow | Faster | General use |

### Change Result Limit

Edit `mcp_server/server.py`:

```python
async def search_documents(query: str, top_k: int = 2) -> dict:
    # Change default from 2 to your preference (max 5)
```

### Customize System Prompt

Edit `backend/agent_service.py`:

```python
SYSTEM_PROMPT = """Your custom instructions here..."""
```

## How It Works

### 1. **User Query**
User asks: "What is machine learning?"

### 2. **Agent Calls Tool**
```python
search_documents(query="machine learning", top_k=2)
```

### 3. **MCP Server Fetches**
```python
GET /search?q=machine+learning&top_k=2
```

### 4. **Backend Searches**
- Embeds query with Ollama
- Searches text collection
- Searches image collection (with CLIP)
- Searches audio collection (transcripts)
- Returns top 2 from each

### 5. **MCP Server Formats**
```python
{
    "text_results": [...],  # Top 2 text
    "image_results": [...], # Top 2 images
    "audio_results": [...]  # Top 2 audio transcripts
}
```

### 6. **Agent Analyzes**
- Reads text chunks
- Views images (if vision model)
- Reads audio transcripts
- Synthesizes answer

### 7. **Agent Responds**
Provides comprehensive answer citing all sources.

## Image Handling

### How Agent Views Images

The agent receives image file paths:
```python
{
    "file_path": "/Users/you/docs/diagram.png",
    "file_name": "diagram.png"
}
```

**With vision model** (LLaVA):
- Agent can load and analyze the image
- Describes visual content
- Relates image to query

**Without vision model**:
- Agent only sees file path and metadata
- Cannot describe image content
- Can still cite the image as relevant

### Image Metadata

```python
{
    "width": 1920,
    "height": 1080,
    "format": "PNG"
}
```

Agent can mention dimensions and format even without viewing.

## Audio Handling

### Transcript Format

```python
{
    "text": "Full transcript text here...",
    "metadata": {
        "start_time": 45.2,      # Seconds
        "end_time": 120.5,       # Seconds
        "language": "en",
        "duration": 1800.0       # Total audio duration
    }
}
```

### What Agent Sees

- ✅ **Transcript text**: Full text of matched segment
- ✅ **Timestamps**: When in the audio this occurs
- ✅ **Language**: Detected language
- ✅ **File name**: Original audio file

### What Agent Doesn't See

- ❌ **Audio waveform**: Not included
- ❌ **Audio data**: Not sent to agent
- ❌ **Speaker info**: Not available (yet)

### Agent Response Example

```
From podcast_ep23.mp3 (audio transcript):
At 12:30 - 15:45 in the recording, the speaker discusses:
"Machine learning algorithms can be categorized into supervised, 
unsupervised, and reinforcement learning..."
```

## Performance

### Response Time
- **Search**: ~50-100ms
- **Agent processing**: ~2-5 seconds
- **Total**: ~3-6 seconds

### Token Usage
- **Text results**: ~200-500 tokens
- **Image results**: ~100-300 tokens (metadata)
- **Audio results**: ~200-500 tokens (transcript)
- **Total input**: ~500-1300 tokens per query

### Memory
- **Agent**: ~4-8GB (model dependent)
- **MCP Server**: ~100MB
- **Backend**: ~500MB-1GB

## Limitations

### 1. **Result Limit**
- Only top 2 results per modality
- May miss relevant content
- Increase `top_k` if needed (max 5)

### 2. **Image Analysis**
- Requires vision-capable model
- Model must be downloaded
- Slower than text-only models

### 3. **Audio Transcripts**
- Agent sees text, not audio
- Cannot hear tone/emotion
- Timestamps help locate in original

### 4. **Context Window**
- Limited by model's context size
- LLaVA 7B: ~4K tokens
- May truncate long results

## Troubleshooting

### Issue: Agent can't view images

**Cause**: Non-vision model or model not downloaded

**Solution**:
```bash
ollama pull gemma4:e4b
```

Edit `backend/config.py` or your root `.env`:
```python
AGENT_MODEL = "gemma4:e4b"
```

### Issue: No image results

**Cause**: No images indexed or query doesn't match

**Solution**:
1. Verify images are indexed (check frontend)
2. Try more descriptive query
3. Check image collection: `python backend/inspect_collections.py`

### Issue: Audio results are empty

**Cause**: Audio not transcribed or query doesn't match transcript

**Solution**:
1. Verify audio files are indexed
2. Check transcripts exist: `ls backend/*.transcript.json`
3. Try query related to spoken content

### Issue: Agent response is slow

**Cause**: Large model or many results

**Solution**:
1. Use smaller model: `llava-phi3`
2. Reduce `top_k` to 1
3. Use faster hardware

### Issue: "Connection refused" error

**Cause**: Backend not running

**Solution**:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Advanced Usage

### Custom Result Processing

Edit `mcp_server/server.py` to customize result formatting:

```python
# Add custom fields
formatted = {
    "query": query,
    "text_results": [...],
    "image_results": [...],
    "audio_results": [...],
    "summary": {
        "total_found": total,
        "best_modality": best,
        "confidence": avg_score
    }
}
```

### Multi-Turn Conversations

The agent maintains context across turns:

```
You: What is machine learning?
Agent: [Provides answer from documents]

You: Show me diagrams about it
Agent: [Searches for images, shows neural network diagrams]

You: Explain the first diagram
Agent: [Analyzes the specific image from previous results]
```

### Filtering by Modality

Modify the tool call to search specific modalities:

```python
# In agent.py, you could add modality parameter
search_documents(query="sunset", modalities=["image"])
```

## Best Practices

### 1. **Use Specific Queries**
- ❌ "Tell me about AI"
- ✅ "Explain neural network backpropagation"

### 2. **Leverage Multimodal**
- Ask for diagrams when available
- Reference audio timestamps
- Combine text and visual info

### 3. **Cite Sources**
- Agent should always cite file names
- Mention modality (text/image/audio)
- Include timestamps for audio

### 4. **Manage Context**
- Keep conversations focused
- Start new session for new topics
- Don't overload with too many results

## Future Enhancements

Potential improvements:

1. **Speaker Diarization**: Identify who said what in audio
2. **Video Support**: Extract frames and audio from videos
3. **OCR**: Extract text from images
4. **Cross-Modal Reasoning**: Connect info across modalities
5. **Result Ranking**: Smarter ranking across modalities
6. **Streaming**: Stream agent responses
7. **Memory**: Remember previous searches

## Summary

✅ **Multimodal search**: Text, images, audio transcripts
✅ **Vision-capable**: Agent can view images
✅ **Transcript analysis**: Agent reads audio transcripts
✅ **Limited results**: Top 2 per modality (configurable)
✅ **Fast**: ~3-6 second response time
✅ **Local**: 100% private, no cloud APIs

The agent now provides comprehensive answers by analyzing content across all three modalities in your indexed documents.

---

**Status**: ✅ Implemented
**Model**: LLaVA 7B (vision-capable)
**Result Limit**: 2 per modality (max 5)
**Audio**: Transcript text only (not audio data)
