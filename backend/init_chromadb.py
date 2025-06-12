#!/usr/bin/env python3
"""Simple ChromaDB initialization script."""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


async def simple_init() -> None:
    """Simple ChromaDB initialization."""

    print("🚀 Setting up ChromaDB...")

    try:
        # Create the data directory first
        data_dir = "./data/chromadb"
        os.makedirs(data_dir, exist_ok=True)
        print(f"📁 Created directory: {data_dir}")

        # Test direct ChromaDB creation
        import chromadb

        # Create client directly
        client = chromadb.PersistentClient(path=data_dir)
        print("✅ ChromaDB client created")

        # Create or get collection
        collection = client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document chunks for Q&A chatbot"},
        )
        print(f"✅ Collection created/found: {collection.name}")
        print(f"   Current count: {collection.count()}")

        # Now test our service
        from app.services.vector_store import vector_store_service

        stats = await vector_store_service.get_collection_stats()
        print(f"✅ Vector store service: {stats}")

        print("\n🎉 ChromaDB is ready!")
        print("\nNext steps:")
        print("1. Add OPENAI_API_KEY to your .env file")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Upload documents and ask questions!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")

        # Try to fix common issues
        print("\n🔧 Trying to fix...")

        try:
            # Delete and recreate
            import shutil

            if os.path.exists("./data/chromadb"):
                shutil.rmtree("./data/chromadb")
                print("🗑️ Deleted old ChromaDB data")

            # Recreate
            os.makedirs("./data/chromadb", exist_ok=True)

            import chromadb

            client = chromadb.PersistentClient(path="./data/chromadb")
            collection = client.create_collection("documents")
            print(f"✅ Fresh ChromaDB created: {collection.count()} items")

        except Exception as e2:
            print(f"❌ Still failing: {e2}")
            print("\nTry manually:")
            print("1. pip install --upgrade chromadb")
            print("2. rm -rf ./data/chromadb")
            print("3. Run this script again")


if __name__ == "__main__":
    asyncio.run(simple_init())
