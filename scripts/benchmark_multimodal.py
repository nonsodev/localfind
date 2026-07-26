"""
benchmark_multimodal.py — Performance benchmarking for multimodal RAG.

Tests embedding speed and search latency for each modality.

Run: python benchmark_multimodal.py
"""
import time
import numpy as np
from pathlib import Path
from PIL import Image
import io

import multimodal_indexer

def benchmark_text_embedding():
    """Benchmark text embedding speed."""
    print("\n📄 Benchmarking Text Embeddings (Ollama)")
    print("-" * 60)
    
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "The sunset painted the sky in shades of orange and pink.",
        "Climate change is one of the most pressing issues of our time.",
        "Python is a versatile programming language used in many domains.",
    ] * 10  # 50 texts total
    
    # Warmup
    _ = multimodal_indexer.embed_texts_ollama([texts[0]])
    
    # Benchmark
    start = time.time()
    embeddings = multimodal_indexer.embed_texts_ollama(texts)
    elapsed = time.time() - start
    
    print(f"   Texts: {len(texts)}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Speed: {len(texts)/elapsed:.1f} texts/sec")
    print(f"   Embedding dim: {len(embeddings[0])}")
    
    return elapsed, len(texts)


def benchmark_image_embedding():
    """Benchmark image embedding speed."""
    print("\n🖼️  Benchmarking Image Embeddings (OpenCLIP)")
    print("-" * 60)
    
    # Create dummy images
    images = []
    for i in range(20):
        # Create random RGB image
        img_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        images.append(img)
    
    # Warmup
    _ = multimodal_indexer.embed_images_clip([images[0]])
    
    # Benchmark
    start = time.time()
    embeddings = multimodal_indexer.embed_images_clip(images)
    elapsed = time.time() - start
    
    print(f"   Images: {len(images)}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Speed: {len(images)/elapsed:.1f} images/sec")
    print(f"   Embedding dim: {len(embeddings[0])}")
    
    return elapsed, len(images)


def benchmark_audio_embedding():
    """Benchmark audio embedding speed."""
    print("\n🎵 Benchmarking Audio Embeddings (CLAP)")
    print("-" * 60)
    
    # Create dummy audio (5 seconds at 48kHz)
    sample_rate = 48000
    duration = 5
    audio_samples = []
    
    for i in range(10):
        # Create random audio waveform
        waveform = np.random.randn(sample_rate * duration).astype(np.float32)
        audio_samples.append((waveform, sample_rate))
    
    # Warmup
    _ = multimodal_indexer.embed_audio_clap([audio_samples[0]])
    
    # Benchmark
    start = time.time()
    embeddings = multimodal_indexer.embed_audio_clap(audio_samples)
    elapsed = time.time() - start
    
    print(f"   Audio files: {len(audio_samples)}")
    print(f"   Duration each: {duration}s")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Speed: {len(audio_samples)/elapsed:.1f} files/sec")
    print(f"   Embedding dim: {len(embeddings[0])}")
    
    return elapsed, len(audio_samples)


def benchmark_text_search():
    """Benchmark text query embedding for search."""
    print("\n🔍 Benchmarking Search Query Embeddings")
    print("-" * 60)
    
    queries = [
        "sunset beach",
        "jazz piano music",
        "mountain landscape",
        "machine learning tutorial",
        "happy birthday song",
    ]
    
    # Text embedding (for text collection)
    start = time.time()
    for query in queries:
        _ = multimodal_indexer.embed_texts_ollama([query])
    text_time = time.time() - start
    
    # CLIP text embedding (for image collection)
    start = time.time()
    for query in queries:
        _ = multimodal_indexer.embed_text_clip([query])
    clip_time = time.time() - start
    
    # CLAP text embedding (for audio collection)
    start = time.time()
    for query in queries:
        _ = multimodal_indexer.embed_text_clap([query])
    clap_time = time.time() - start
    
    print(f"   Queries: {len(queries)}")
    print(f"\n   Text embedding (Ollama):")
    print(f"      Time: {text_time:.2f}s")
    print(f"      Avg: {text_time/len(queries)*1000:.0f}ms per query")
    
    print(f"\n   CLIP text embedding:")
    print(f"      Time: {clip_time:.2f}s")
    print(f"      Avg: {clip_time/len(queries)*1000:.0f}ms per query")
    
    print(f"\n   CLAP text embedding:")
    print(f"      Time: {clap_time:.2f}s")
    print(f"      Avg: {clap_time/len(queries)*1000:.0f}ms per query")
    
    total_time = text_time + clip_time + clap_time
    print(f"\n   Total for multimodal search: {total_time:.2f}s")
    print(f"   Avg per query: {total_time/len(queries)*1000:.0f}ms")
    
    return total_time, len(queries)


def benchmark_chromadb():
    """Benchmark ChromaDB operations."""
    print("\n💾 Benchmarking ChromaDB Operations")
    print("-" * 60)
    
    # Get collections
    text_coll = multimodal_indexer.get_collection(multimodal_indexer.TEXT_COLLECTION)
    image_coll = multimodal_indexer.get_collection(multimodal_indexer.IMAGE_COLLECTION)
    audio_coll = multimodal_indexer.get_collection(multimodal_indexer.AUDIO_COLLECTION)
    
    print(f"   Text collection: {text_coll.count()} items")
    print(f"   Image collection: {image_coll.count()} items")
    print(f"   Audio collection: {audio_coll.count()} items")
    
    if text_coll.count() > 0:
        # Benchmark query
        query_embedding = multimodal_indexer.embed_texts_ollama(["test query"])[0]
        
        start = time.time()
        results = text_coll.query(
            query_embeddings=[query_embedding],
            n_results=10,
        )
        elapsed = time.time() - start
        
        print(f"\n   Query latency: {elapsed*1000:.1f}ms")
        print(f"   Results returned: {len(results['ids'][0])}")


def main():
    print("=" * 60)
    print("  Multimodal RAG Performance Benchmark")
    print("=" * 60)
    
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n🖥️  Device: {device.upper()}")
    
    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Run benchmarks
    try:
        text_time, text_count = benchmark_text_embedding()
        image_time, image_count = benchmark_image_embedding()
        audio_time, audio_count = benchmark_audio_embedding()
        search_time, query_count = benchmark_text_search()
        benchmark_chromadb()
        
        # Summary
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        
        print(f"\n📊 Embedding Throughput:")
        print(f"   Text: {text_count/text_time:.1f} items/sec")
        print(f"   Images: {image_count/image_time:.1f} items/sec")
        print(f"   Audio: {audio_count/audio_time:.1f} items/sec")
        
        print(f"\n🔍 Search Latency:")
        print(f"   Avg per query: {search_time/query_count*1000:.0f}ms")
        print(f"   (includes all 3 embedding models)")
        
        print(f"\n💡 Tips:")
        if device == "cpu":
            print("   • Use a GPU for 5-10x faster embeddings")
        print("   • Batch processing improves throughput")
        print("   • First run is slower (model loading)")
        print("   • ChromaDB uses HNSW for fast similarity search")
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        print("\nMake sure:")
        print("  1. Ollama is running: ollama serve")
        print("  2. Model is pulled: ollama pull nomic-embed-text")
        print("  3. Dependencies installed: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
