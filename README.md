# 🍽️ Restaurant Q&A System

A modern RAG (Retrieval-Augmented Generation) based question answering system specifically designed for restaurant information management. Upload your restaurant documents and get instant, accurate answers to customer questions.

## ✨ Features

- **🚀 Modern Web Interface**: Beautiful, responsive UI with drag-and-drop file upload
- **📄 Multi-format Support**: PDF, DOCX, TXT, and Markdown files
- **🤖 AI-Powered**: Uses Ollama for local LLM inference
- **🔍 Smart Search**: Vector-based similarity search with ChromaDB
- **📊 Monitoring**: Built-in Prometheus metrics and health checks
- **🔒 Secure**: File validation and size limits
- **⚡ Fast**: Optimized for performance with async processing
- **🛠️ Production Ready**: Comprehensive error handling and logging

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  FastAPI Server │    │   Ollama LLM    │
│    (HTML/JS)    │◄──►│   (Python)      │◄──►│   (Local AI)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   RAG Pipeline  │◄──►│   ChromaDB      │
                       │   (LangChain)   │    │ (Vector Store)  │
                       └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai) installed and running
- 4GB+ RAM (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd restaurant-qa-system
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Start the application**
   ```bash
   python -m uvicorn src.main: