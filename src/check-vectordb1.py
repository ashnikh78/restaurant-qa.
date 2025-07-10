#!/usr/bin/env python3
"""
Debug script for RAG Pipeline
Run this to diagnose issues with your RAG system
"""

import sys
import traceback
from pathlib import Path
from loguru import logger

# Add your project path
sys.path.append('.')

try:
    from config import load_config
    from rag_pipeline import RAGPipeline
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)

def debug_rag_system():
    """Comprehensive debugging of RAG system"""
    
    print("🔍 Starting RAG System Debug...")
    print("=" * 50)
    
    try:
        # Step 1: Load configuration
        print("\n1. Loading Configuration...")
        config = load_config()
        print(f"✅ Configuration loaded")
        print(f"   - Data directory: {config.data_dir}")
        print(f"   - ChromaDB directory: {config.chroma_db_dir}")
        print(f"   - Model: {config.model_name}")
        print(f"   - Ollama host: {config.ollama_host}")
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Step 2: Initialize RAG Pipeline
        print("\n2. Initializing RAG Pipeline...")
        rag = RAGPipeline(config)
        print(f"✅ RAG Pipeline initialized")
        
    except Exception as e:
        print(f"❌ RAG Pipeline initialization failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Step 3: Check system health
        print("\n3. Health Check...")
        health = rag.health_check()
        for component, status in health.items():
            print(f"   {component}: {status}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        traceback.print_exc()
    
    try:
        # Step 4: Get system stats
        print("\n4. System Statistics...")
        stats = rag.get_stats()
        print(f"   - Documents processed: {stats.get('documents_processed', 0)}")
        print(f"   - Chunks in vectorstore: {stats.get('chunks_in_vectorstore', 0)}")
        print(f"   - Collection name: {stats.get('collection_name', 'unknown')}")
        print(f"   - Model: {stats.get('model_name', 'unknown')}")
        
        if stats.get('processed_files'):
            print(f"   - Processed files:")
            for file in stats['processed_files'][:5]:  # Show first 5
                print(f"     • {Path(file).name}")
            if len(stats['processed_files']) > 5:
                print(f"     ... and {len(stats['processed_files']) - 5} more")
        
    except Exception as e:
        print(f"❌ Stats retrieval failed: {e}")
        traceback.print_exc()
    
    try:
        # Step 5: Debug vectorstore
        print("\n5. VectorStore Debug...")
        debug_info = rag.debug_vectorstore()
        print(f"   - Collection: {debug_info.get('collection_name', 'unknown')}")
        print(f"   - Document count: {debug_info.get('document_count', 0)}")
        print(f"   - Sample documents: {len(debug_info.get('sample_documents', []))}")
        
        for i, doc in enumerate(debug_info.get('sample_documents', [])[:3]):
            print(f"   Sample {i+1}:")
            print(f"     Content: {doc['content'][:100]}...")
            print(f"     Source: {doc['metadata'].get('filename', 'unknown')}")
        
    except Exception as e:
        print(f"❌ VectorStore debug failed: {e}")
        traceback.print_exc()
    
    try:
        # Step 6: Test queries
        print("\n6. Testing Queries...")
        test_queries = [
            "What is a loan?",
            "Tell me about interest rates",
            "What are the requirements for a loan?",
            "How to apply for a loan?",
            "What documents do I need?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   Test Query {i}: {query}")
            try:
                answer, sources = rag.answer_query(query)
                print(f"   ✅ Answer: {answer[:150]}...")
                print(f"   📄 Sources: {sources}")
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
                
    except Exception as e:
        print(f"❌ Query testing failed: {e}")
        traceback.print_exc()
    
    try:
        # Step 7: Check data directory
        print("\n7. Data Directory Check...")
        data_dir = Path(config.data_dir)
        if data_dir.exists():
            files = list(data_dir.rglob("*"))
            doc_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.txt', '.pdf', '.docx', '.doc', '.md']]
            print(f"   - Total files in data directory: {len(files)}")
            print(f"   - Document files: {len(doc_files)}")
            
            if doc_files:
                print(f"   - Document files found:")
                for file in doc_files[:10]:  # Show first 10
                    size = file.stat().st_size
                    print(f"     • {file.name} ({size} bytes)")
                if len(doc_files) > 10:
                    print(f"     ... and {len(doc_files) - 10} more")
        else:
            print(f"   ❌ Data directory not found: {data_dir}")
            
    except Exception as e:
        print(f"❌ Data directory check failed: {e}")
        traceback.print_exc()
    
    try:
        # Step 8: ChromaDB inspection
        print("\n8. ChromaDB Inspection...")
        import chromadb
        client = chromadb.PersistentClient(path=config.chroma_db_dir)
        collections = client.list_collections()
        
        print(f"   - Available collections: {len(collections)}")
        for collection in collections:
            print(f"     • {collection.name}: {collection.count()} documents")
            
    except Exception as e:
        print(f"❌ ChromaDB inspection failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🏁")