# LocalFind - Deployment Checklist

Use this checklist to ensure everything is set up correctly before using LocalFind.

## ✅ Pre-Installation Checklist

### System Requirements
- [ ] **Operating System**: macOS, Linux, or Windows
- [ ] **Python**: Version 3.10 or higher installed
- [ ] **Node.js**: Version 18 or higher installed
- [ ] **RAM**: At least 8GB (16GB recommended)
- [ ] **Disk Space**: At least 10GB free
- [ ] **Internet**: For initial model downloads

### Verify Installations
```bash
# Check Python version
python --version  # Should be 3.10+

# Check Node.js version
node --version    # Should be 18+

# Check npm version
npm --version     # Should be 8+

# Check pip
pip --version
```

---

## ✅ Installation Checklist

### 1. Install ffmpeg (Required for Audio)
- [ ] **macOS**: `brew install ffmpeg`
- [ ] **Linux**: `sudo apt install ffmpeg`
- [ ] **Windows**: Download from https://ffmpeg.org/download.html
- [ ] **Verify**: `ffmpeg -version`

### 2. Install Ollama (Required)
- [ ] Download from https://ollama.ai
- [ ] Install Ollama
- [ ] Start Ollama: `ollama serve`
- [ ] Verify: `ollama list`

### 3. Pull Required Models
```bash
# Text embeddings (required)
ollama pull nomic-embed-text

# Agent model (optional, for built-in agent / Claude workflows)
ollama pull gemma4:e4b
```
- [ ] nomic-embed-text downloaded (~275MB)
- [ ] gemma4:e4b downloaded (optional)

### 4. Clone Repository
```bash
git clone https://github.com/nonsodev/localfind.git
cd localfind
```
- [ ] Repository cloned
- [ ] In project directory

### 5. Install Backend Dependencies
```bash
cd backend
uv pip install -r requirements.txt
```
- [ ] All Python packages installed
- [ ] No error messages

### 6. Install Frontend Dependencies
```bash
cd ../frontend
npm install
```
- [ ] All npm packages installed
- [ ] No error messages

### 7. Install MCP Server Dependencies (Optional)
```bash
cd ../mcp_server
uv pip install -r requirements.txt
```
- [ ] MCP server dependencies installed

---

## ✅ First Run Checklist

### 1. Start Ollama
```bash
ollama serve
```
- [ ] Ollama running
- [ ] No error messages
- [ ] Accessible at http://localhost:11434

### 2. Start LocalFind Server
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- [ ] Server started successfully
- [ ] Running on port 8000
- [ ] No error messages
- [ ] Health check: `curl http://localhost:8000/health`

### 3. Start Main UI (Optional)
```bash
cd frontend
npm run dev
```
- [ ] Frontend started
- [ ] Running on port 5173
- [ ] Accessible at http://localhost:5173
- [ ] No console errors

### 4. Index First Folder
- [ ] Open http://localhost:5173
- [ ] Go to Folders tab
- [ ] Add a test folder
- [ ] Click Sync
- [ ] Wait for indexing to complete
- [ ] Check stats show indexed files

### 5. Test Search
- [ ] Go to Search tab
- [ ] Enter a search query
- [ ] Results appear
- [ ] Can filter by modality
- [ ] Result cards display correctly

### 6. Test Audio (If You Have Audio Files)
- [ ] Search for audio content
- [ ] Audio results appear
- [ ] Click audio result
- [ ] Waveform displays
- [ ] Green highlight shows matched segment
- [ ] Audio plays correctly
- [ ] "Jump to Match" works

---

## ✅ Agent / Claude Setup Checklist (Optional)

### 1. Verify LocalFind Server Running
- [ ] LocalFind server is running on port 8000
- [ ] Can access http://localhost:8000/health

### 2. Verify Ollama and Model
- [ ] Ollama is running
- [ ] Agent model installed: `ollama list`

### 3. Use the Built-In Agent in the UI
```bash
cd frontend
npm run dev
```
- [ ] Frontend running on port 5173
- [ ] Search page loads
- [ ] Agent mode is available in the UI

### 4. Optional: Configure Claude Desktop
```bash
cd mcp_server
uv pip install -r requirements.txt
```
- [ ] MCP server dependencies installed
- [ ] Claude Desktop MCP config added
- [ ] `BACKEND_URL` points at `http://localhost:8000`
- [ ] Filesystem connector enabled if image inspection is needed

### 5. Test Agent Chat
- [ ] Open http://localhost:5173
- [ ] Switch from Search to Agent
- [ ] Send a simple message: "Hello"
- [ ] Agent responds
- [ ] Send a search query: "What files do I have?"
- [ ] Agent searches and responds with results
- [ ] Conversation history maintained

---

## ✅ Performance Verification

### Backend Performance
- [ ] Search responds in < 100ms
- [ ] Indexing completes without errors
- [ ] Memory usage reasonable (< 1GB)
- [ ] No memory leaks over time

### Frontend Performance
- [ ] UI loads quickly (< 2s)
- [ ] Search results appear quickly
- [ ] No lag when typing
- [ ] Smooth animations

### Audio Performance
- [ ] Transcription completes (check terminal logs)
- [ ] Waveform renders smoothly
- [ ] Audio playback has no stuttering
- [ ] Seeking works instantly

### Agent Performance
- [ ] Chat responses in < 5s
- [ ] Search integration works
- [ ] No timeout errors
- [ ] Memory usage reasonable

---

## ✅ Feature Verification

### Text Search
- [ ] Can search PDF files
- [ ] Can search DOCX files
- [ ] Can search TXT files
- [ ] Can search MD files
- [ ] Results show relevant chunks
- [ ] Similarity scores displayed
- [ ] Can click file paths

### Image Search
- [ ] Can search images
- [ ] Image thumbnails display
- [ ] Can click to view full size
- [ ] Metadata shows (size, format)
- [ ] Similarity scores displayed

### Audio Search
- [ ] Audio files transcribed
- [ ] Can search transcript content
- [ ] Timestamps displayed
- [ ] Waveform shows
- [ ] Green highlight on matched segment
- [ ] "Jump to Match" works
- [ ] Audio plays correctly

### Agent Features
- [ ] Can chat naturally
- [ ] Automatically searches when needed
- [ ] Cites sources in responses
- [ ] Can inspect images in the built-in agent or Claude Desktop
- [ ] Handles audio transcripts
- [ ] Conversation context maintained

---

## ✅ Troubleshooting Verification

### If Backend Won't Start
- [ ] Check port 8000 not in use: `lsof -i :8000`
- [ ] Check Python version: `python --version`
- [ ] Check dependencies installed: `pip list`
- [ ] Check Ollama running: `curl http://localhost:11434/api/tags`

### If Frontend Won't Start
- [ ] Check port 5173 not in use: `lsof -i :5173`
- [ ] Check Node.js version: `node --version`
- [ ] Check dependencies installed: `npm list`
- [ ] Clear cache: `rm -rf node_modules && npm install`

### If Search Not Working
- [ ] Backend is running
- [ ] Folders are indexed
- [ ] ChromaDB exists: `ls backend/chroma_db`
- [ ] Ollama is running
- [ ] nomic-embed-text model installed

### If Audio Not Working
- [ ] ffmpeg installed: `ffmpeg -version`
- [ ] Audio files in supported format (MP3, WAV, FLAC)
- [ ] Whisper model downloaded (check first run logs)
- [ ] Transcripts generated: `ls backend/*.transcript.json`

### If Agent Not Working
- [ ] LocalFind server running
- [ ] Frontend running
- [ ] Ollama running
- [ ] Agent model installed
- [ ] If using Claude Desktop, MCP config is correct

---

## ✅ Security Verification

### Privacy
- [ ] No external API calls made
- [ ] All processing happens locally
- [ ] No telemetry or tracking
- [ ] Data stays on your machine

### Access Control
- [ ] Backend only accesses indexed folders
- [ ] CORS configured for localhost only
- [ ] No authentication (single-user design)
- [ ] File paths validated

---

## ✅ Documentation Verification

### User Documentation
- [ ] README.md is clear and complete
- [ ] QUICK_REFERENCE.md works
- [ ] WHISPER_AUDIO_GUIDE.md is helpful
- [ ] AGENT_QUICKSTART.md is clear

### Technical Documentation
- [ ] ARCHITECTURE.md is accurate
- [ ] PROJECT_STRUCTURE.md is up-to-date
- [ ] API endpoints documented
- [ ] Configuration options documented

### Developer Documentation
- [ ] CONTRIBUTING.md exists
- [ ] Code is commented
- [ ] Setup instructions work
- [ ] Troubleshooting guide helps

---

## ✅ Production Readiness

### Code Quality
- [ ] No syntax errors
- [ ] No runtime errors
- [ ] Error handling in place
- [ ] Logging configured

### Stability
- [ ] Runs for extended periods
- [ ] No memory leaks
- [ ] Handles errors gracefully
- [ ] Can recover from failures

### Usability
- [ ] UI is intuitive
- [ ] Error messages are helpful
- [ ] Loading states are clear
- [ ] Feedback is immediate

### Performance
- [ ] Search is fast (< 100ms)
- [ ] Indexing is reasonable
- [ ] Memory usage is acceptable
- [ ] CPU usage is reasonable

---

## ✅ GitHub Readiness

### Repository
- [ ] .gitignore configured
- [ ] LICENSE file present (MIT)
- [ ] README.md professional
- [ ] No sensitive data committed
- [ ] No large binary files

### Documentation
- [ ] All docs present
- [ ] Links work
- [ ] Images display (if any)
- [ ] Code examples work

### Structure
- [ ] Clean directory structure
- [ ] No temp files
- [ ] No IDE-specific files
- [ ] Organized and logical

---

## ✅ Final Checks

### Before First Use
- [ ] All dependencies installed
- [ ] All services running
- [ ] Test folder indexed
- [ ] Test search works
- [ ] Documentation read

### Before Sharing
- [ ] All features tested
- [ ] Documentation complete
- [ ] No known bugs
- [ ] Performance acceptable
- [ ] Security verified

### Before GitHub Push
- [ ] Code reviewed
- [ ] Docs reviewed
- [ ] .gitignore configured
- [ ] LICENSE present
- [ ] README professional

---

## 🎉 Deployment Complete!

If all items are checked, your LocalFind installation is complete and ready to use!

### Next Steps:
1. **Index Your Documents**: Add folders and sync
2. **Explore Features**: Try all search modalities
3. **Use the Agent**: Chat with your documents
4. **Use Claude Desktop**: Optional MCP integration
5. **Share**: Push to GitHub if desired

---

## 📞 Support

If any checklist items fail:
1. Review the relevant documentation
2. Check the troubleshooting section
3. Review terminal logs for errors
4. Verify all prerequisites are met
5. Try restarting services

---

**Deployment Checklist Version**: 2.0  
**Last Updated**: May 2026

**Happy Deploying! 🚀**
