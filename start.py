#!/usr/bin/env python3
"""
Simple starter for SkillMate AI Mock Interview
"""

import os
import sys

def main():
    print("🚀 Starting SkillMate AI Mock Interview...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    # Create directories if they don't exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 SkillMate server stopped!")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main() 