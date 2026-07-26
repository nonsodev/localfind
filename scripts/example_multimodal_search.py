"""
example_multimodal_search.py — Example script demonstrating multimodal search.

This script shows how to use the multimodal RAG system programmatically.

Run: python example_multimodal_search.py
"""
import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def add_folder(folder_path):
    """Add a folder to the system."""
    print(f"\n📁 Adding folder: {folder_path}")
    response = requests.post(
        f"{API_BASE}/folders",
        json={"path": folder_path}
    )
    if response.ok:
        data = response.json()
        print(f"   ✓ Added with ID: {data['id']}")
        return data['id']
    else:
        print(f"   ❌ Failed: {response.text}")
        return None

def sync_folder(folder_id):
    """Trigger indexing for a folder."""
    print(f"\n🔄 Syncing folder {folder_id}...")
    response = requests.post(f"{API_BASE}/sync/{folder_id}")
    if response.ok:
        print("   ✓ Sync started")
        
        # Poll for status
        import time
        while True:
            status_response = requests.get(f"{API_BASE}/sync/{folder_id}/status")
            if status_response.ok:
                status = status_response.json()
                if status['status'] == 'done':
                    result = status['result']
                    print(f"\n   ✓ Sync complete!")
                    print(f"      - Total scanned: {result['total_scanned']}")
                    print(f"      - Indexed: {result['indexed_new']} new, {result['indexed_updated']} updated")
                    print(f"      - By modality: {result['by_modality']}")
                    print(f"      - Skipped: {result['skipped_unchanged']}")
                    if result['failed'] > 0:
                        print(f"      - Failed: {result['failed']}")
                    break
                elif status['status'] == 'error':
                    print(f"   ❌ Sync failed: {status['result']}")
                    break
                elif status['status'] == 'syncing':
                    print("   ⏳ Still syncing...")
                    time.sleep(2)
            else:
                print(f"   ❌ Status check failed")
                break
    else:
        print(f"   ❌ Failed to start sync: {response.text}")

def search(query, modalities=None, top_k=5):
    """Perform a multimodal search."""
    print(f"\n🔍 Searching for: '{query}'")
    if modalities:
        print(f"   Modalities: {modalities}")
    
    url = f"{API_BASE}/search?q={query}&top_k={top_k}"
    if modalities:
        url += f"&modalities={modalities}"
    
    response = requests.get(url)
    if response.ok:
        data = response.json()
        
        # Count results
        text_count = len(data['results'].get('text', []))
        image_count = len(data['results'].get('image', []))
        audio_count = len(data['results'].get('audio', []))
        total = text_count + image_count + audio_count
        
        print(f"\n   Found {total} results:")
        print(f"      📄 Text: {text_count}")
        print(f"      🖼️  Images: {image_count}")
        print(f"      🎵 Audio: {audio_count}")
        
        # Show top results from each modality
        if text_count > 0:
            print(f"\n   Top text results:")
            for i, result in enumerate(data['results']['text'][:3], 1):
                print(f"      {i}. {result['file_name']} (score: {result['score']:.3f})")
                preview = result['text'][:80] + "..." if len(result['text']) > 80 else result['text']
                print(f"         {preview}")
        
        if image_count > 0:
            print(f"\n   Top image results:")
            for i, result in enumerate(data['results']['image'][:3], 1):
                print(f"      {i}. {result['file_name']} (score: {result['score']:.3f})")
                if result.get('metadata'):
                    meta = result['metadata']
                    if 'width' in meta and 'height' in meta:
                        print(f"         {meta['width']}×{meta['height']}")
        
        if audio_count > 0:
            print(f"\n   Top audio results:")
            for i, result in enumerate(data['results']['audio'][:3], 1):
                print(f"      {i}. {result['file_name']} (score: {result['score']:.3f})")
                if result.get('metadata'):
                    meta = result['metadata']
                    if 'duration_seconds' in meta:
                        mins = int(meta['duration_seconds'] // 60)
                        secs = int(meta['duration_seconds'] % 60)
                        print(f"         Duration: {mins}:{secs:02d}")
        
        return data
    else:
        print(f"   ❌ Search failed: {response.text}")
        return None

def get_stats():
    """Get system statistics."""
    response = requests.get(f"{API_BASE}/stats")
    if response.ok:
        data = response.json()
        print(f"\n📊 System Statistics:")
        print(f"   Folders: {data['total_folders']}")
        print(f"   Files: {data['total_files']}")
        print(f"   Chunks: {data['total_chunks']}")
        if data['last_sync']:
            print(f"   Last sync: {data['last_sync']}")
        return data
    else:
        print(f"   ❌ Failed to get stats")
        return None

def main():
    print_section("Multimodal RAG Example")
    
    print("\nThis script demonstrates the multimodal RAG system.")
    print("Make sure the backend is running: python main.py")
    
    # Check health
    try:
        response = requests.get(f"{API_BASE}/health")
        if not response.ok:
            print("\n❌ Backend is not responding. Start it with: python main.py")
            return
        print("\n✓ Backend is running")
    except:
        print("\n❌ Cannot connect to backend. Start it with: python main.py")
        return
    
    # Get current stats
    get_stats()
    
    print_section("Example 1: Search Everything")
    search("sunset beach", top_k=5)
    
    print_section("Example 2: Search Only Images")
    search("mountain landscape", modalities="image", top_k=5)
    
    print_section("Example 3: Search Only Audio")
    search("jazz piano", modalities="audio", top_k=5)
    
    print_section("Example 4: Search Text and Images")
    search("nature", modalities="text,image", top_k=3)
    
    print_section("Example 5: Complex Query")
    search("melancholic rainy evening", top_k=5)
    
    print("\n" + "="*60)
    print("✅ Examples complete!")
    print("\nTo add your own folder:")
    print("  1. Uncomment the lines below")
    print("  2. Replace with your folder path")
    print("  3. Run this script again")
    print("\n# folder_id = add_folder('/path/to/your/media')")
    print("# sync_folder(folder_id)")
    print("="*60)

if __name__ == "__main__":
    main()
