#!/usr/bin/env python3
"""
Benchmark image captioning backends.

Usage:
    python scripts/benchmark_captioning.py /path/to/images [--count 3] [--models qwen2.5vl:3b gemma4:e2b gemma4:e4b]

Each model is tested in isolation: the previous model is fully unloaded from
memory before the next one loads, so timings reflect real-world single-model
performance. The first image per model (cold start / load time) is reported
separately from the warm-run average.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx is required: uv pip install httpx")
    sys.exit(1)

OLLAMA_BASE = "http://localhost:11434"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
DEFAULT_MODELS = ["qwen2.5vl:3b", "gemma4:e2b", "gemma4:e4b"]
PROMPT = (
    "Describe this image in detail. Include the main subjects, setting, colors, "
    "any visible text, and spatial layout. Be specific."
)


def list_local_models(client: httpx.Client) -> list[str]:
    try:
        return [m["name"] for m in client.get(f"{OLLAMA_BASE}/api/tags", timeout=5).json().get("models", [])]
    except Exception:
        return []


def is_available(model: str, local_models: list[str]) -> bool:
    base = model.split(":")[0]
    return any(m == model or m.startswith(base + ":") for m in local_models)


def unload_model(model: str, client: httpx.Client) -> None:
    """Tell Ollama to evict this model from memory immediately."""
    try:
        client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=10.0,
        )
    except Exception:
        pass  # best-effort


def caption(model: str, path: Path, client: httpx.Client) -> tuple[str, float]:
    b64 = base64.b64encode(path.read_bytes()).decode()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT, "images": [b64]}],
        "stream": False,
        "keep_alive": -1,  # stay loaded until we explicitly unload
    }
    t0 = time.perf_counter()
    resp = client.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=300.0)
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip(), elapsed


def main():
    parser = argparse.ArgumentParser(description="Benchmark image captioning backends")
    parser.add_argument("folder", help="Folder containing test images")
    parser.add_argument("--count", type=int, default=3, metavar="N",
                        help="Images to test per model (default: 3)")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                        metavar="MODEL", help="Models to benchmark")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Not a directory: {folder}")
        sys.exit(1)

    images = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in IMAGE_EXTS]
    if not images:
        print(f"No images found in {folder}  (supported: {', '.join(sorted(IMAGE_EXTS))})")
        sys.exit(1)

    sample = images[: args.count]
    print(f"\nImages ({len(sample)}): {[p.name for p in sample]}")
    print(f"Models: {args.models}")
    print("Each model is unloaded from memory before the next one starts.\n")

    # cold = first image time (includes model load), warm = rest
    cold_times: dict[str, float] = {}
    warm_times: dict[str, list[float]] = {}

    with httpx.Client() as client:
        try:
            client.get(f"{OLLAMA_BASE}/api/tags", timeout=3).raise_for_status()
        except Exception:
            print("Ollama is not running. Start it with: ollama serve")
            sys.exit(1)

        local = list_local_models(client)

        for model in args.models:
            print(f"── {model} " + "─" * max(0, 50 - len(model)))
            if not is_available(model, local):
                print(f"   not installed — skip  (ollama pull {model})\n")
                continue

            warm: list[float] = []
            for i, img in enumerate(sample):
                label = "cold" if i == 0 else f"warm {i}"
                try:
                    text, elapsed = caption(model, img, client)
                    preview = text[:80].replace("\n", " ")
                    print(f"   [{label}] {img.name:<28} {elapsed:5.1f}s  {preview}…")
                    if i == 0:
                        cold_times[model] = elapsed
                    else:
                        warm.append(elapsed)
                except httpx.HTTPStatusError as e:
                    print(f"   [{label}] {img.name:<28} HTTP {e.response.status_code}")
                except Exception as e:
                    print(f"   [{label}] {img.name:<28} ERROR: {e}")

            warm_times[model] = warm

            print(f"   Unloading {model} from memory…")
            unload_model(model, client)
            print()

    tested = [m for m in args.models if m in cold_times]
    if not tested:
        print("No results — make sure Ollama is running and at least one model is pulled.")
        return

    col = 26
    print("─" * 66)
    print(f"{'Model':<{col}} {'Cold (load)':>11}  {'Warm avg':>9}  {'Warm min':>9}")
    print("─" * 66)

    def sort_key(m):
        warms = warm_times.get(m, [])
        return sum(warms) / len(warms) if warms else cold_times.get(m, 9999)

    ranked = sorted(tested, key=sort_key)
    for i, model in enumerate(ranked):
        cold = cold_times.get(model)
        warms = warm_times.get(model, [])
        warm_avg = f"{sum(warms)/len(warms):.1f}s" if warms else "  n/a"
        warm_min = f"{min(warms):.1f}s" if warms else "  n/a"
        cold_str = f"{cold:.1f}s" if cold is not None else "  n/a"
        flag = "  ← fastest (warm)" if i == 0 and warms else ("  ← fastest" if i == 0 else "")
        print(f"{model:<{col}} {cold_str:>11}  {warm_avg:>9}  {warm_min:>9}{flag}")

    print("─" * 66)
    print("\nCold = first image, includes model load time.")
    print("Warm = subsequent images, model already in memory — this is what matters day-to-day.")
    print(f"\nSet in .env:  IMAGE_CAPTIONING_BACKEND={ranked[0]}")


if __name__ == "__main__":
    main()
