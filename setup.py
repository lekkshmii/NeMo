#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_requirements():
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_environment():
    env_template = Path(".env.template")
    env_file = Path(".env")
    
    if not env_file.exists() and env_template.exists():
        print("🔧 Creating .env file from template...")
        env_file.write_text(env_template.read_text())
        print("✅ .env file created - please add your API keys")
    else:
        print("ℹ️ .env file already exists")

def create_data_directories():
    print("📁 Creating data directories...")
    directories = [
        "data",
        "data/chroma_db",
        "data/documents",
        "data/cache",
        "results"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Data directories created")

def test_imports():
    print("🧪 Testing imports...")
    try:
        sys.path.append('src')
        
        from ingestion.document_processor import DocumentProcessor
        from extraction.financial_extractor import FinancialExtractor
        from embeddings.vector_store import VectorStore
        from reasoning.query_engine import QueryEngine
        from data_sources.sec_api import SECDataSource
        
        print("✅ All imports successful")
        
        print("🧠 Initializing components...")
        processor = DocumentProcessor()
        extractor = FinancialExtractor()
        
        print("✅ NeMo components initialized successfully")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Some dependencies may be missing")
    except Exception as e:
        print(f"⚠️ Warning during initialization: {e}")
        print("This is normal - some models may download on first use")

def main():
    print("🚀 Setting up NeMo Financial Research Assistant...\n")
    
    check_python_version()
    install_requirements()
    setup_environment()
    create_data_directories()
    test_imports()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: jupyter notebook notebooks/nemo_demo.ipynb")
    print("3. Or start API server: cd src/api && python main.py")
    print("\n📚 Documentation: README.md")

if __name__ == "__main__":
    main()
