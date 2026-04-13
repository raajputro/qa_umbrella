#!/usr/bin/env python
"""
Helper script to start Ollama and ensure required models are available.
"""
import os
import subprocess
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def is_ollama_running(url="http://localhost:11434"):
    """Check if Ollama service is running."""
    try:
        response = requests.get(f"{url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_ollama():
    """Start Ollama service."""
    print("Starting Ollama service...")
    try:
        # Try to start Ollama on Windows
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Ollama startup command sent...")
        
        # Wait for service to be ready
        print("Waiting for Ollama to start (up to 30 seconds)...")
        for i in range(30):
            time.sleep(1)
            if is_ollama_running():
                print("✓ Ollama is running!")
                return True
            if i % 5 == 0:
                print(f"  Still waiting... ({i}s)")
        
        print("✗ Ollama did not start within 30 seconds")
        return False
    except FileNotFoundError:
        print("✗ Ollama not found. Please install Ollama from https://ollama.ai")
        return False
    except Exception as e:
        print(f"✗ Error starting Ollama: {e}")
        return False

def pull_model(model_name):
    """Pull required model from Ollama."""
    print(f"\nPulling model: {model_name}")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✓ Model {model_name} is ready!")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to pull model {model_name}")
        return False
    except FileNotFoundError:
        print("✗ Ollama not found")
        return False

def main():
    """Main setup routine."""
    model = os.getenv("PPAI_LLM_MODEL", "qwen2.5-coder:7b")
    
    print("=" * 60)
    print("PPAI Ollama Setup")
    print("=" * 60)
    
    # Check if Ollama is already running
    if is_ollama_running():
        print("✓ Ollama is already running!")
    else:
        print("Ollama is not running, attempting to start...")
        if not start_ollama():
            print("\n⚠ Could not start Ollama automatically.")
            print("Please start Ollama manually:")
            print("  1. Open a new terminal")
            print("  2. Run: ollama serve")
            print("  3. Come back to this terminal and press Enter")
            input("Press Enter once Ollama is running...")
            
            if not is_ollama_running():
                print("✗ Ollama still not available. Exiting.")
                sys.exit(1)
            print("✓ Ollama is now running!")
    
    # Check and pull model
    print(f"\nConfigured model: {model}")
    try:
        # Try to get list of models
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models_data = response.json()
        available_models = [m.get("name", "") for m in models_data.get("models", [])]
        
        if model in available_models:
            print(f"✓ Model {model} is already available!")
        else:
            print(f"Model {model} not found. Pulling...")
            pull_model(model)
    except Exception as e:
        print(f"Could not check models: {e}")
        print(f"Attempting to pull {model}...")
        pull_model(model)
    
    print("\n" + "=" * 60)
    print("✓ Setup complete! Ollama is ready to use.")
    print("=" * 60)

if __name__ == "__main__":
    main()
