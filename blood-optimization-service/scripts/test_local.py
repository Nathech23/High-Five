#!/usr/bin/env python3
"""Script de test local"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def run_command(cmd, cwd=None):
    """Exécute une commande"""
    print(f"🔄 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        return False
    
    print(f"✅ Command succeeded: {cmd}")
    return True

def test_local_setup():
    """Test setup local"""
    
    print("🧪 Testing local setup...")
    
    # Test 1: Dependencies
    if not run_command("pip install -r requirements.txt"):
        return False
    
    # Test 2: Python imports
    if not run_command("python -c 'from src.api.main import app; print(\"✅ Imports OK\")'"):
        return False
    
    # Test 3: Tests unitaires
    if not run_command("python -m pytest tests/ -v"):
        return False
    
    # Test 4: Docker build
    if not run_command("docker build -t blood-optimization-test ."):
        return False
    
    print("🎉 All local tests passed!")
    return True

if __name__ == "__main__":
    success = test_local_setup()
    sys.exit(0 if success else 1)