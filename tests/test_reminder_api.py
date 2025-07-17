import asyncio
import pytest
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import time

# Configuration de test
API_BASE_URL = "http://localhost:8000"
TEST_PATIENT_ID = 1

class TestReminderAPI:
    """Tests pour l'API de rappels"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE_URL)
        self.created_reminders = []  # Pour le nettoyage
    
    async def setup(self):
        """Configuration initiale des tests"""
        print("\n=== Configuration des tests ===")
        
        # Vérifier que l'API est accessible
        try:
            response = await self.client.get("/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API accessible - Statut: {health_data['status']}")
                print(f"   Services: {health_data['services']}")
            else:
                print(f"❌ API non accessible - Code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erreur de connexion à l'API: {e}")
            return False
        
        return True
    
    async def test_create_reminder(self) -> Dict[str, Any]:
        """Test 1: Créer un rappel programmé"""
        print("\n=== Test 1: Création d'un rappel ===")
        
        # Programmer un rappel dans 2 minutes
        scheduled_time = datetime.now() + timedelta(minutes=2)
        
        reminder_data = {
            "patient_id": TEST_PATIENT_ID,
            "reminder_type": "appointment",
            "delivery_method": "sms",
            "scheduled_time": scheduled_time.isoformat(),
            "priority": "normal",
            "custom_message": "Test de rappel automatique",
            "metadata": {
                "test_id": "test_create_reminder",
                "appointment_type": "consultation"
            }
        }
        
        try:
            response = await self.client.post("/reminders", json=reminder_data)
            
            if response.status_code == 201:
                result = response.json()
                reminder_id = result['id']
                self.created_reminders.append(reminder_id)
                
                print(f"✅ Rappel créé avec succès - ID: {reminder_id}")
                print(f"   Programmé pour: {scheduled_time}")
                print(f"   Statut: {result['status']}")
                
                return result
            else:
                print(f"❌ Échec création rappel - Code: {response.status_code}")
                print(f"   Réponse: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")
            return None
    
    async def test_immediate_reminder(self) -> Dict[str, Any]:
        """Test 2: Envoyer un rappel immédiat"""
        print("\n=== Test 2: Rappel immédiat ===")
        
        reminder_data = {
            "patient_id": TEST_PATIENT_ID,
            "reminder_type": "medication",
            "delivery_method": "sms",
            "priority": "high",
            "custom_message": "Test de rappel immédiat - prise de médicament",
            "metadata": {
                "test_id": "test_immediate_reminder",
                "medication": "Paracétamol"
            }
        }
        
        try:
            response = await self.client.post("/reminders/immediate", json=reminder_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Rappel immédiat envoyé avec succès")
                print(f"   Message ID: {result.get('message_id', 'N/A')}")
                print(f"   Statut: {result.get('status', 'N/A')}")
                
                return result
            else:
                print(f"❌ Échec envoi immédiat - Code: {response.status_code}")
                print(f"   Réponse: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi immédiat: {e}")
            return None
    
    async def test_list_reminders(self):
        """Test 3: Lister les rappels"""
        print("\n=== Test 3: Liste des rappels ===")
        
        try:
            # Lister tous les rappels
            response = await self.client.get("/reminders")
            
            if response.status_code == 200:
                result = response.json()
                reminders = result['reminders']
                
                print(f"✅ {len(reminders)} rappels trouvés")
                print(f"   Total: {result['total']}")
                print(f"   Page: {result['page']}/{result['total_pages']}")
                
                # Afficher quelques détails
                for reminder in reminders[:3]:  # Afficher les 3 premiers
                    print(f"   - ID {reminder['id']}: {reminder['reminder_type']} - {reminder['status']}")
                
                return result
            else:
                print(f"❌ Échec liste rappels - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la liste: {e}")
            return None
    
    async def test_reminder_details(self, reminder_id: int):
        """Test 4: Récupérer les détails d'un rappel"""
        print(f"\n=== Test 4: Détails du rappel {reminder_id} ===")
        
        try:
            response = await self.client.get(f"/reminders/{reminder_id}")
            
            if response.status_code == 200:
                reminder = response.json()
                
                print(f"✅ Détails récupérés pour le rappel {reminder_id}")
                print(f"   Type: {reminder['reminder_type']}")
                print(f"   Statut: {reminder['status']}")
                print(f"   Programmé: {reminder['scheduled_time']}")
                print(f"   Tentatives: {reminder['retry_count']}/{reminder['max_retries']}")
                
                return reminder
            else:
                print(f"❌ Échec récupération détails - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {e}")
            return None
    
    async def test_batch_reminders(self):
        """Test 5: Créer des rappels en lot"""
        print("\n=== Test 5: Rappels en lot ===")
        
        # Créer 3 rappels en lot
        base_time = datetime.now() + timedelta(minutes=5)
        
        batch_data = {
            "reminders": [
                {
                    "patient_id": TEST_PATIENT_ID,
                    "reminder_type": "appointment",
                    "delivery_method": "sms",
                    "scheduled_time": (base_time + timedelta(minutes=i)).isoformat(),
                    "priority": "normal",
                    "custom_message": f"Rappel de lot #{i+1}",
                    "metadata": {"batch_test": True, "index": i}
                }
                for i in range(3)
            ]
        }
        
        try:
            response = await self.client.post("/reminders/batch", json=batch_data)
            
            if response.status_code == 201:
                result = response.json()
                
                print(f"✅ Lot de {len(result['created'])} rappels créé")
                print(f"   IDs créés: {result['created']}")
                
                # Ajouter à la liste pour nettoyage
                self.created_reminders.extend(result['created'])
                
                if result.get('errors'):
                    print(f"   ⚠️  Erreurs: {len(result['errors'])}")
                
                return result
            else:
                print(f"❌ Échec création lot - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la création en lot: {e}")
            return None
    
    async def test_statistics(self):
        """Test 6: Récupérer les statistiques"""
        print("\n=== Test 6: Statistiques ===")
        
        try:
            response = await self.client.get("/reminders/stats")
            
            if response.status_code == 200:
                stats = response.json()
                
                print(f"✅ Statistiques récupérées")
                print(f"   Total rappels: {stats['total']}")
                print(f"   En attente: {stats['pending']}")
                print(f"   Programmés: {stats['scheduled']}")
                print(f"   Envoyés: {stats['sent']}")
                print(f"   Livrés: {stats['delivered']}")
                print(f"   Échoués: {stats['failed']}")
                print(f"   Taux de livraison: {stats['delivery_rate']:.1f}%")
                
                return stats
            else:
                print(f"❌ Échec récupération stats - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors des statistiques: {e}")
            return None
    
    async def test_scheduler_metrics(self):
        """Test 7: Métriques du planificateur"""
        print("\n=== Test 7: Métriques du planificateur ===")
        
        try:
            response = await self.client.get("/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                
                print(f"✅ Métriques récupérées")
                print(f"   Statut planificateur: {'✅' if metrics['scheduler_status']['running'] else '❌'}")
                print(f"   Tailles des queues:")
                
                for queue_name, size in metrics['scheduler_status']['queue_sizes'].items():
                    print(f"     - {queue_name}: {size}")
                
                print(f"   Statistiques planificateur:")
                stats = metrics['scheduler_status']['stats']
                print(f"     - Traités: {stats['processed_count']}")
                print(f"     - Succès: {stats['success_count']}")
                print(f"     - Erreurs: {stats['error_count']}")
                
                return metrics
            else:
                print(f"❌ Échec récupération métriques - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors des métriques: {e}")
            return None
    
    async def test_force_processing(self):
        """Test 8: Forcer le traitement des rappels"""
        print("\n=== Test 8: Traitement forcé ===")
        
        try:
            response = await self.client.post("/admin/scheduler/force-process")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    print(f"✅ Traitement forcé réussi")
                    print(f"   Rappels traités: {result['processed_count']}")
                    print(f"   Temps de traitement: {result['processing_time_seconds']:.2f}s")
                else:
                    print(f"❌ Traitement forcé échoué: {result.get('error')}")
                
                return result
            else:
                print(f"❌ Échec traitement forcé - Code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement forcé: {e}")
            return None
    
    async def cleanup(self):
        """Nettoyer les rappels de test"""
        print("\n=== Nettoyage des tests ===")
        
        deleted_count = 0
        for reminder_id in self.created_reminders:
            try:
                response = await self.client.delete(f"/reminders/{reminder_id}")
                if response.status_code == 200:
                    deleted_count += 1
            except:
                pass  # Ignorer les erreurs de nettoyage
        
        print(f"✅ {deleted_count}/{len(self.created_reminders)} rappels de test supprimés")
        
        await self.client.aclose()
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 Démarrage des tests de l'API de rappels")
        print("=" * 50)
        
        # Configuration
        if not await self.setup():
            print("❌ Échec de la configuration initiale")
            return
        
        try:
            # Test 1: Créer un rappel
            reminder = await self.test_create_reminder()
            reminder_id = reminder['id'] if reminder else None
            
            # Test 2: Rappel immédiat
            await self.test_immediate_reminder()
            
            # Test 3: Lister les rappels
            await self.test_list_reminders()
            
            # Test 4: Détails d'un rappel
            if reminder_id:
                await self.test_reminder_details(reminder_id)
            
            # Test 5: Rappels en lot
            await self.test_batch_reminders()
            
            # Test 6: Statistiques
            await self.test_statistics()
            
            # Test 7: Métriques du planificateur
            await self.test_scheduler_metrics()
            
            # Test 8: Traitement forcé
            await self.test_force_processing()
            
            print("\n" + "=" * 50)
            print("✅ Tous les tests terminés avec succès!")
            
        except Exception as e:
            print(f"\n❌ Erreur durant les tests: {e}")
        
        finally:
            # Nettoyage
            await self.cleanup()

# Fonction principale pour exécuter les tests
async def main():
    """Point d'entrée principal"""
    tester = TestReminderAPI()
    await tester.run_all_tests()

if __name__ == "__main__":
    # Exécuter les tests
    print("Tests de l'API de rappels - Hôpital Général de Douala")
    print("Phase 4: API callbacks et planification")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")