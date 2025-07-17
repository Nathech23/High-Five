import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000"
TEST_PATIENT = {
    "name": "Marie Dubois",
    "phone": "+237675934861",
    "preferred_language": "fr",
    "doctor_name": "Dr. Kamga",
    "appointment_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
    "appointment_time": "14:30",
    "department": "Cardiologie",
    "medication_name": "Aspirine",
    "dosage": "100mg",
    "room_number": "205",
    "emergency_contact": "+237699123456"
}

def test_endpoint(endpoint, method="GET", data=None):
    """Test un endpoint et retourne le résultat"""
    try:
        url = f"{BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print("\n" + "="*60)
    print("🎨 TESTS PHASE 3: TEMPLATES ET PERSONNALISATION")
    print("="*60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL de base: {BASE_URL}")
    print("="*60)
    
    tests = [
        {
            "name": "Page d'accueil Phase 3",
            "endpoint": "/",
            "method": "GET"
        },
        {
            "name": "Validation des templates",
            "endpoint": "/api/templates/validate",
            "method": "GET"
        },
        {
            "name": "SMS personnalisé - Rendez-vous",
            "endpoint": "/api/templates/sms",
            "method": "POST",
            "data": {
                "patient_data": TEST_PATIENT,
                "message_type": "appointment_reminder"
            }
        },
        {
            "name": "Appel personnalisé - Médicament",
            "endpoint": "/api/templates/call",
            "method": "POST",
            "data": {
                "patient_data": TEST_PATIENT,
                "message_type": "medication_reminder"
            }
        },
        {
            "name": "Test complet du système",
            "endpoint": "/api/templates/test",
            "method": "POST",
            "data": {
                "patient_data": TEST_PATIENT
            }
        },
        {
            "name": "Statut de santé Phase 3",
            "endpoint": "/health",
            "method": "GET"
        }
    ]
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f"\n🧪 Test {i}: {test['name']}")
        print("-" * 40)
        
        result = test_endpoint(
            test['endpoint'], 
            test['method'], 
            test.get('data')
        )
        
        if result['success']:
            print(f"✅ RÉUSSI (Status: {result['status_code']})")
            if isinstance(result['data'], dict):
                if 'message' in result['data']:
                    print(f"   Message: {result['data']['message'][:100]}...")
                if 'status' in result['data']:
                    print(f"   Statut: {result['data']['status']}")
                if 'features' in result['data']:
                    print(f"   Fonctionnalités: {len(result['data']['features'])}")
        else:
            print(f"❌ ÉCHOUÉ")
            if 'error' in result:
                print(f"   Erreur: {result['error']}")
            else:
                print(f"   Status: {result['status_code']}")
        
        results.append({
            "test": test['name'],
            "success": result['success'],
            "details": result
        })
    
    # Résumé final
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS PHASE 3")
    print("="*60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"Tests réussis: {passed}/{total}")
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("\n🎉 PHASE 3 VALIDÉE AVEC SUCCÈS!")
        print("✅ Le système de templates et personnalisation fonctionne correctement")
    elif success_rate >= 60:
        print("\n⚠️ PHASE 3 PARTIELLEMENT VALIDÉE")
        print("🔧 Quelques ajustements nécessaires")
    else:
        print("\n❌ PHASE 3 NÉCESSITE DES CORRECTIONS")
        print("🛠️ Vérifiez la configuration et les erreurs")
    
    # Sauvegarde des résultats
    with open('test_phase3_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "success_rate": success_rate,
            "total_tests": total,
            "passed_tests": passed,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés dans: test_phase3_results.json")
    print("\n🔗 Endpoints Phase 3 disponibles:")
    print("   - http://localhost:5000/ (Page d'accueil)")
    print("   - http://localhost:5000/api/templates/validate (Validation)")
    print("   - http://localhost:5000/health (Statut système)")

if __name__ == "__main__":
    main()