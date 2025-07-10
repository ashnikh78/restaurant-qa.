import os
from sentence_transformers import SentenceTransformer

# Define the model name and target save path
model_name = "sentence-transformers/all-MiniLM-L6-v2"
save_path = "models/all-MiniLM-L6-v2"

try:
    # Ensure the save directory exists
    os.makedirs(save_path, exist_ok=True)

    # Load model from Hugging Face
    print(f"📥 Downloading model: {model_name}")
    model = SentenceTransformer(model_name)

    # Save model locally
    model.save(save_path)
    print(f"✅ Model saved successfully to '{save_path}'")

except Exception as e:
    print(f"❌ Failed to download or save the model: {e}")
