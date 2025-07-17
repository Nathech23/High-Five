"""
Test simple de l'API de rappels
"""

import requests
import json
from datetime import datetime, timedelta

def test_api_health():
    """Test de l'endpoint de santé"""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def test_api_root():
    """Test de l'endpoint racine"""
    try:
        response = requests.get("http://localhost:8000/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def test_api_docs():
    """Test de l'endpoint de documentation"""
    try:
        response = requests.get("http://localhost:8000/docs")
        print(f"Status Code: {response.status_code}")
        print(f"Documentation accessible: {response.status_code == 200}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def main():
    print("=== Test de l'API de Rappels ===")
    print()
    
    print("1. Test de l'endpoint racine:")
    test_api_root()
    print()
    
    print("2. Test de l'endpoint de santé:")
    test_api_health()
    print()
    
    print("3. Test de l'endpoint de documentation:")
    test_api_docs()
    print()
    
    print("✅ Tests terminés !")
    print("📊 Documentation interactive disponible sur: http://localhost:8000/docs")
    print("🔧 API de santé disponible sur: http://localhost:8000/health")

if __name__ == "__main__":
    main()