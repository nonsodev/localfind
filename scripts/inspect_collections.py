"""
inspect_collections.py — Utility to inspect ChromaDB collections.

Shows what's indexed in each modality collection.

Run: python inspect_collections.py
"""
import multimodal_indexer
from collections import defaultdict

print("🔍 ChromaDB Collection Inspector\n")
print("=" * 60)

# Get all collections
collections = {
    "Text": multimodal_indexer.TEXT_COLLECTION,
    "Images": multimodal_indexer.IMAGE_COLLECTION,
    "Audio": multimodal_indexer.AUDIO_COLLECTION,
}

total_items = 0

for name, coll_name in collections.items():
    print(f"\n📊 {name} Collection ({coll_name})")
    print("-" * 60)
    
    try:
        collection = multimodal_indexer.get_collection(coll_name)
        count = collection.count()
        total_items += count
        
        if count == 0:
            print("   Empty — no items indexed yet")
            continue
        
        print(f"   Total items: {count}")
        
        # Get sample items
        sample_size = min(5, count)
        sample = collection.get(
            limit=sample_size,
            include=["metadatas", "documents"]
        )
        
        # Analyze by file type
        file_types = defaultdict(int)
        folders = defaultdict(int)
        
        all_data = collection.get(include=["metadatas"])
        for meta in all_data["metadatas"]:
            file_types[meta.get("file_type", "unknown")] += 1
            folders[meta.get("folder_id", "unknown")] += 1
        
        print(f"\n   By file type:")
        for ftype, fcount in sorted(file_types.items(), key=lambda x: -x[1]):
            print(f"      {ftype}: {fcount}")
        
        print(f"\n   By folder:")
        for fid, fcount in sorted(folders.items(), key=lambda x: -x[1]):
            print(f"      Folder {fid}: {fcount} items")
        
        print(f"\n   Sample items:")
        for i, (doc, meta) in enumerate(zip(sample["documents"], sample["metadatas"]), 1):
            fname = meta.get("file_name", "unknown")
            score_preview = doc[:60] + "..." if len(doc) > 60 else doc
            print(f"      {i}. {fname}")
            print(f"         {score_preview}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print(f"📈 Total items across all collections: {total_items}")

if total_items == 0:
    print("\n💡 No items indexed yet. To get started:")
    print("   1. Add a folder: POST /folders")
    print("   2. Sync it: POST /sync/{folder_id}")
    print("   3. Run this script again to see indexed items")
else:
    print("\n✅ Collections are populated and ready for search!")
    print("\nTry a search:")
    print('   curl "http://localhost:8000/search?q=your+query"')
