from chromadb import PersistentClient
from config import AppConfig

config = AppConfig()
client = PersistentClient(path=config.chroma_db_dir)

# List all collections
collections = client.list_collections()

if not collections:
    print("🚫 No collections found in the Chroma vector database.")
else:
    print("📦 Available collections:")
    for col in collections:
        print(f"- {col.name}")
