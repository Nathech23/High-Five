import requests
import json

def test_communication_endpoint():
    """Test de l'endpoint /test/communication avec simulation"""
    
    url = "http://localhost:5000/test/communication"
    
    # Test avec simulation (par défaut)
    test_data = {
        "phone": "+237675123456",
        "language": "fr",
        "simulate_only": True
    }
    
    try:
        print("🧪 Test de l'endpoint /test/communication en mode simulation...")
        print(f"URL: {url}")
        print(f"Données: {json.dumps(test_data, indent=2)}")
        print("\n" + "="*60)
        
        response = requests.post(
            url, 
            json=test_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("\n✅ Test réussi - Pas de timeout!")
        else:
            print(f"\n❌ Test échoué - Status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("\n❌ Timeout détecté!")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")

if __name__ == "__main__":
    test_communication_endpoint()