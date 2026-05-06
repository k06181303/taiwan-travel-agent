"""
scripts/seed.py

讀取 data/attractions.json 與 data/foods.json，
產生 bge-m3 embedding 後批次寫入 ChromaDB。
執行方式：python scripts/seed.py
"""

import io
import json
import sys
from pathlib import Path

# Windows 終端機強制 UTF-8 輸出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT))

from app.rag.embeddings import embed_texts
from app.rag.vector_store import (
    COLLECTION_ATTRACTIONS,
    COLLECTION_FOODS,
    count_documents,
    upsert_documents,
)

BATCH_SIZE = 16  # 每批 embed 的筆數，避免 OOM


def build_attraction_text(item: dict) -> str:
    """將景點資料拼成一段供 embedding 的描述文字"""
    keywords = "、".join(item.get("keywords", []))
    tags = "、".join(item.get("tags", []))
    return (
        f"{item['name']} {' '.join(item.get('aliases', []))} "
        f"{item['description']} "
        f"類型：{item['type']} 城市：{item['city']} {item['district']} "
        f"關鍵字：{keywords} 標籤：{tags}"
    )


def build_food_text(item: dict) -> str:
    """將美食資料拼成一段供 embedding 的描述文字"""
    keywords = "、".join(item.get("keywords", []))
    tags = "、".join(item.get("tags", []))
    must_try = "、".join(item.get("must_try", []))
    return (
        f"{item['name']} {' '.join(item.get('aliases', []))} "
        f"{item['description']} "
        f"類別：{item['category']} 城市：{item['city']} {item['district']} "
        f"必點：{must_try} 關鍵字：{keywords} 標籤：{tags}"
    )


def build_attraction_metadata(item: dict) -> dict:
    """只保留 ChromaDB 支援的純量 metadata 欄位"""
    return {
        "name": item["name"],
        "city": item["city"],
        "district": item["district"],
        "type": item["type"],
        "price_level": item["price_level"],
        "rating": item["rating"],
        "indoor": item["indoor"],
        "kid_friendly": item["kid_friendly"],
        "pet_friendly": item["pet_friendly"],
        "wheelchair_friendly": item["wheelchair_friendly"],
        "has_parking": item["has_parking"],
        "popularity": item["popularity"],
    }


def build_food_metadata(item: dict) -> dict:
    """只保留 ChromaDB 支援的純量 metadata 欄位"""
    return {
        "name": item["name"],
        "city": item["city"],
        "district": item["district"],
        "category": item["category"],
        "price_level": item["price_level"],
        "price_range_min": item["price_range_min"],
        "price_range_max": item["price_range_max"],
        "rating": item["rating"],
        "vegetarian_type": item["vegetarian_type"],
        "halal": item["halal"],
        "pet_friendly": item["pet_friendly"],
        "queue_level": item["queue_level"],
        "popularity": item["popularity"],
    }


def seed_collection(
    json_path: Path,
    collection_name: str,
    text_builder,
    metadata_builder,
) -> None:
    print(f"\n📂 載入 {json_path.name}...")
    items: list[dict] = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"   共 {len(items)} 筆")

    ids = [item["id"] for item in items]
    documents = [text_builder(item) for item in items]
    metadatas = [metadata_builder(item) for item in items]

    # 分批 embed，印出進度
    all_embeddings: list[list[float]] = []
    for start in range(0, len(documents), BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        print(f"   embedding {start + 1}~{start + len(batch)} / {len(documents)}...")
        all_embeddings.extend(embed_texts(batch))

    print(f"   寫入 ChromaDB collection: {collection_name}...")
    upsert_documents(
        collection_name=collection_name,
        ids=ids,
        embeddings=all_embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    count = count_documents(collection_name)
    print(f"   ✅ {collection_name} 現有 {count} 筆")


def main() -> None:
    print("=" * 45)
    print("  ChromaDB Seed Script")
    print("=" * 45)

    seed_collection(
        DATA_DIR / "attractions.json",
        COLLECTION_ATTRACTIONS,
        build_attraction_text,
        build_attraction_metadata,
    )

    seed_collection(
        DATA_DIR / "foods.json",
        COLLECTION_FOODS,
        build_food_text,
        build_food_metadata,
    )

    print("\n✅ Seed 完成！可以啟動 server 測試 RAG。")


if __name__ == "__main__":
    main()
