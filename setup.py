#!/usr/bin/env python3
"""
Setup script for the RAG Restaurant Q&A System
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")

def check_ollama():
    """Check if Ollama is installed"""
    print("🤖 Checking Ollama installation...")
    result = run_command("ollama --version", "Checking Ollama version")
    if result:
        print(f"✅ Ollama is installed: {result.strip()}")
        return True
    else:
        print("❌ Ollama is not installed")
        print("📥 Please install Ollama from: https://ollama.ai/download")
        return False

def install_ollama_model(model_name="tinyllama:latest"):
    """Install Ollama model"""
    print(f"📦 Installing Ollama model: {model_name}")
    result = run_command(f"ollama pull {model_name}", f"Pulling {model_name}")
    if result:
        print(f"✅ Model {model_name} installed successfully")
        return True
    else:
        print(f"❌ Failed to install model {model_name}")
        return False

def create_virtual_environment():
    """Create and activate virtual environment"""
    print("📦 Creating virtual environment...")
    
    if platform.system() == "Windows":
        venv_activate = "venv\\Scripts\\activate"
        python_cmd = "python"
    else:
        venv_activate = "venv/bin/activate"
        python_cmd = "python3"
    
    # Create virtual environment
    if not run_command(f"{python_cmd} -m venv venv", "Creating virtual environment"):
        return False
    
    print(f"✅ Virtual environment created")
    print(f"💡 To activate: {venv_activate}")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Upgrade pip first
    if not run_command("pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        "data",
        "chroma_db", 
        "logs",
        "uploads",
        "static"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_sample_files():
    """Create sample configuration files"""
    print("📄 Creating sample files...")
    
    # Create sample .env file
    env_content = """# RAG System Configuration

# Directories
DATA_DIR=data
CHROMA_DB_DIR=chroma_db
LOG_DIR=logs

# Ollama Settings
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=tinyllama:latest

# LLM Parameters
TEMPERATURE=0.7
MAX_TOKENS=500

# RAG Parameters
SIMILARITY_TOP_K=3
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Performance
REQUEST_TIMEOUT=30
MAX_FILE_SIZE_MB=10

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Logging
LOG_LEVEL=INFO
LOG_ROTATION=1 day
LOG_RETENTION=7 days

# Development
DEBUG=False
RELOAD=False
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    print("✅ Created .env file")
    
    # Create sample data file
    sample_data = """# Sample Restaurant Data

## Menu Items

### Appetizers
- **Bruschetta** - Fresh tomatoes, basil, and mozzarella on toasted bread - $8.99
- **Calamari Rings** - Crispy fried squid with marinara sauce - $12.99
- **Spinach Artichoke Dip** - Creamy dip served with tortilla chips - $9.99

### Main Courses
- **Grilled Salmon** - Fresh Atlantic salmon with lemon herb butter - $24.99
- **Chicken Parmesan** - Breaded chicken breast with marinara and mozzarella - $18.99
- **Beef Tenderloin** - 8oz filet mignon with garlic mashed potatoes - $32.99

### Desserts
- **Tiramisu** - Classic Italian dessert with coffee and mascarpone - $7.99
- **Chocolate Lava Cake** - Warm chocolate cake with vanilla ice cream - $6.99

## Restaurant Information

### Hours
- Monday - Thursday: 11:00 AM - 9:00 PM
- Friday - Saturday: 11:00 AM - 10:00 PM
- Sunday: 12:00 PM - 8:00 PM

### Contact
- Phone: (555) 123-4567
- Email: info@restaurant.com
- Address: 123 Main Street, City, State 12345

### Policies
- Reservations recommended for parties of 6 or more
- 18% gratuity added to parties of 8 or more
- Happy hour: Monday-Friday 4:00-6:00 PM
- We accommodate most dietary restrictions with advance notice
"""
    
    data_dir = Path("data")
    with open(data_dir / "sample_restaurant_data.txt", "w") as f:
        f.write(sample_data)
    print("✅ Created sample restaurant data")

def create_startup_script():
    """Create startup script"""
    print("🚀 Creating startup script...")
    
    startup_script = """#!/bin/bash
# RAG System Startup Script

echo "🚀 Starting RAG Restaurant Q&A System..."

# Check if Ollama is running
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "🤖 Starting Ollama server..."
    ollama serve &
    sleep 3
fi

# Check if model is available
if ! ollama list | grep -q "tinyllama:latest"; then
    echo "📦 Pulling tinyllama model..."
    ollama pull tinyllama:latest
fi

# Start the application
echo "🌐 Starting FastAPI application..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

echo "✅ Application started at http://localhost:8000"
"""
    
    with open("start.sh", "w") as f:
        f.write(startup_script)
    
    # Make executable on Unix systems
    if platform.system() != "Windows":
        os.chmod("start.sh", 0o755)
    
    print("✅ Created startup script (start.sh)")

def main():
    """Main setup function"""
    print("🏗️  Setting up RAG Restaurant Q&A System")
    print("=" * 50)
    
    # Step 1: Check Python version
    check_python_version()
    
    # Step 2: Check Ollama
    ollama_installed = check_ollama()
    
    # Step 3: Create virtual environment
    if "--skip-venv" not in sys.argv:
        create_virtual_environment()
    
    # Step 4: Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Step 5: Create directories
    create_directories()
    
    # Step 6: Create sample files
    create_sample_files()
    
    # Step 7: Create startup script
    create_startup_script()
    
    # Step 8: Install Ollama model if Ollama is available
    if ollama_installed:
        install_ollama_model()
    
    print("\n✅ Setup completed successfully!")
    print("=" * 50)