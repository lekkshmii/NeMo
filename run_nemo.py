#!/usr/bin/env python3

import sys
import os
import subprocess
from pathlib import Path

def main():
    print("🧠 NeMo Financial Research Assistant")
    print("="*50)
    
    options = {
        '1': ('📊 Run Demo Notebook', 'jupyter notebook notebooks/nemo_demo.ipynb'),
        '2': ('🚀 Quick Start Notebook', 'jupyter notebook notebooks/quick_start.ipynb'),
        '3': ('🌐 Start API Server', 'cd src/api && python main.py'),
        '4': ('🏢 Competitive Analysis Example', 'python examples/competitive_analysis.py'),
        '5': ('📞 Earnings Analysis Example', 'python examples/earnings_analysis.py'),
        '6': ('🧪 Run Tests', 'python tests/test_nemo.py'),
        '7': ('⚙️ Setup Environment', 'python setup.py'),
        '8': ('📋 Show Project Structure', 'show_structure'),
        '9': ('❓ Help & Documentation', 'show_help')
    }
    
    print("\nChoose an option:")
    for key, (description, _) in options.items():
        print(f"  {key}. {description}")
    
    choice = input("\nEnter your choice (1-9): ").strip()
    
    if choice not in options:
        print("❌ Invalid choice")
        return
    
    description, command = options[choice]
    print(f"\n🚀 Running: {description}")
    
    if command == 'show_structure':
        show_project_structure()
    elif command == 'show_help':
        show_help()
    else:
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running command: {e}")
        except KeyboardInterrupt:
            print("\n⏹️ Operation cancelled")

def show_project_structure():
    print("\n📁 NeMo Project Structure:")
    print("""
nemo/
├── 📊 notebooks/           # Jupyter demos
│   ├── nemo_demo.ipynb    # Main demonstration
│   └── quick_start.ipynb  # Quick start guide
├── 🧠 src/                # Core components
│   ├── ingestion/         # Document processing
│   ├── extraction/        # Financial metrics
│   ├── embeddings/        # Vector storage
│   ├── reasoning/         # AI query engine
│   ├── data_sources/      # SEC API integration
│   ├── api/              # FastAPI server
│   └── utils/            # Helper functions
├── 🎯 examples/           # Usage examples
│   ├── competitive_analysis.py
│   └── earnings_analysis.py
├── 🧪 tests/             # Test suite
├── 📊 data/              # Local data storage
├── ⚙️ config/            # Configuration
└── 📋 requirements.txt   # Dependencies
    """)

def show_help():
    print("\n❓ NeMo Help & Documentation")
    print("-" * 40)
    
    print("\n🚀 Getting Started:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Copy .env.template to .env and add your API keys")
    print("3. Run setup.py to initialize the environment")
    print("4. Try the demo notebook: notebooks/nemo_demo.ipynb")
    
    print("\n🔑 Required API Keys (optional):")
    print("• ANTHROPIC_API_KEY - For Claude integration")
    print("• OPENAI_API_KEY - For GPT integration")
    print("• GOOGLE_API_KEY - For Gemini integration")
    print("• SEC_API_KEY - For enhanced SEC data access")
    
    print("\n📊 Key Features:")
    print("• Multi-modal document processing (text, tables, images)")
    print("• Automated financial metrics extraction")
    print("• AI-powered Q&A with citations")
    print("• SEC EDGAR filing integration")
    print("• Real-time market event monitoring")
    print("• Semantic search across documents")
    
    print("\n🎯 Use Cases:")
    print("• Investment Banking: Due diligence automation")
    print("• Private Equity: Deal sourcing and analysis")
    print("• Venture Capital: Startup research")
    print("• Quantitative Finance: Alternative data extraction")
    
    print("\n📞 Support:")
    print("• GitHub Issues: Report bugs and feature requests")
    print("• Documentation: README.md")
    print("• Examples: Check examples/ directory")
    
    print("\n💡 Tips:")
    print("• Start with quick_start.ipynb for basic usage")
    print("• Use nemo_demo.ipynb for comprehensive demonstration")
    print("• Check examples/ for real-world use cases")
    print("• Run tests to verify installation")

if __name__ == "__main__":
    main()
