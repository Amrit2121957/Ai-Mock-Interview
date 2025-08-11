#!/usr/bin/env python3
"""
TalentMate Mock Interview - Quick Start Runner
This script helps you get started with the TalentMate application quickly.
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {platform.python_version()}")
        return False
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies!")
        return False

def create_directories():
    """Create necessary directories"""
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    print("📁 Directories created successfully!")

def run_application():
    """Run the Flask application"""
    print("\n🚀 Starting TalentMate Mock Interview...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError:
        print("❌ Could not import the Flask app. Make sure app.py exists!")
    except KeyboardInterrupt:
        print("\n👋 TalentMate server stopped!")

def main():
    """Main runner function"""
    print("=" * 50)
    print("🧠 TalentMate - AI Mock Interview")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Run the application
    run_application()

if __name__ == "__main__":
    main() 