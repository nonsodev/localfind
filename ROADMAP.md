# Roadmap

LocalFind is a private, local, multimodal semantic search tool. This file tracks where it's headed. It's a living document — open an issue to propose, discuss, or claim anything here.

## Now

- Stabilise the core: indexing, search, and the local agent across documents, images, and audio.
- Model-agnostic configuration — any Ollama chat/vision model as the agent or captioning backend.
- Clear docs for first-run setup and model selection.

## Next

- **Easier install** — a single setup script (or container) that checks prerequisites, pulls models, and starts both services.
- **More file formats** — EPUB, HTML, PPTX, and richer PDF extraction (tables, embedded images).
- **Incremental re-indexing** — detect changed/deleted files and update the index without a full re-sync.
- **Search quality** — hybrid keyword + vector ranking, result re-ranking, and per-modality filters in the UI.
- **Model presets** — named hardware tiers in `.env.example` so users pick "low RAM / balanced / max quality" instead of memorising tags.

## Later / exploring

- **One-click desktop build** — package backend + frontend for non-technical users.
- **Folder watching** — background sync that indexes new files as they land.
- **Pluggable model backends** beyond Ollama (llama.cpp, OpenAI-compatible endpoints) behind the same config surface.
- **Export & sharing** — export search results or a curated set of matches.

## Non-goals

- Sending your data to a cloud service by default. The local path stays the default and the privacy guarantee. Cloud options (the Claude Desktop integration, cloud model tags) remain strictly opt-in and clearly labelled.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Issues labelled **good first issue** are the easiest place to start.
