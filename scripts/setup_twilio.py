"""
Script interactif de configuration Twilio
"""

import os
import sys
from pathlib import Path

def print_header():
    """Affiche l'en-tête du script"""
    print("="*60)
    print("🏥 CONFIGURATION TWILIO - HÔPITAL GÉNÉRAL DOUALA")
    print("="*60)
    print()

def check_env_file():
    """Vérifie si le fichier .env existe"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        if env_example.exists():
            print("📋 Création du fichier .env à partir de .env.example...")
            with open(env_example, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Fichier .env créé")
        else:
            print("❌ Fichier .env.example introuvable")
            return False
    else:
        print("✅ Fichier .env trouvé")
    
    return True

def get_user_input(prompt, default=None, required=True):
    """Récupère une entrée utilisateur avec validation"""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if user_input or not required:
            return user_input
        
        print("❌ Cette information est requise")

def collect_twilio_credentials():
    """Collecte les credentials Twilio"""
    print("\n📱 CONFIGURATION TWILIO")
    print("-" * 30)
    
    print("\n1. Créez un compte sur https://www.twilio.com/")
    print("2. Vérifiez votre numéro de téléphone")
    print("3. Obtenez vos credentials dans la Console Twilio")
    
    input("\nAppuyez sur Entrée quand vous êtes prêt...")
    
    credentials = {}
    
    print("\n🔑 Credentials Twilio:")
    credentials['TWILIO_ACCOUNT_SID'] = get_user_input(
        "Account SID (commence par AC)"
    )
    
    credentials['TWILIO_AUTH_TOKEN'] = get_user_input(
        "Auth Token (32 caractères)"
    )
    
    credentials['TWILIO_PHONE_NUMBER'] = get_user_input(
        "Numéro Twilio (format: +1234567890)"
    )
    
    print("\n📞 Numéro de test:")
    credentials['TEST_PHONE_NUMBER'] = get_user_input(
        "Votre numéro camerounais (format: +237XXXXXXXX)",
        required=False
    )
    
    return credentials

def update_env_file(credentials):
    """Met à jour le fichier .env avec les credentials"""
    env_file = Path('.env')
    
    # Lire le contenu actuel
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Mettre à jour les lignes
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0]
            if key in credentials:
                updated_lines.append(f"{key}={credentials[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line + '\n')
        else:
            updated_lines.append(line + '\n')
    
    # Ajouter les nouvelles clés si elles n'existent pas
    for key, value in credentials.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Écrire le fichier mis à jour
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print("✅ Fichier .env mis à jour")

def test_configuration():
    """Test la configuration Twilio"""
    print("\n🧪 TEST DE CONFIGURATION")
    print("-" * 30)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Vérifier les variables d'environnement
        required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Variables manquantes: {missing_vars}")
            return False
        
        # Tester la connexion Twilio
        from twilio.rest import Client
        
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        # Vérifier le compte
        account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
        print(f"✅ Connexion Twilio réussie")
        print(f"   Compte: {account.friendly_name}")
        print(f"   Status: {account.status}")
        
        # Vérifier le numéro
        phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        try:
            number = client.incoming_phone_numbers.list(
                phone_number=phone_number
            )[0]
            print(f"✅ Numéro Twilio validé: {number.phone_number}")
            print(f"   Capacités: SMS={number.capabilities['sms']}, Voice={number.capabilities['voice']}")
        except:
            print(f"⚠️  Impossible de valider le numéro: {phone_number}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("   Exécutez: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        print("   Vérifiez vos credentials Twilio")
        return False

def run_communication_tests():
    """Lance les tests de communication"""
    print("\n🚀 TESTS DE COMMUNICATION")
    print("-" * 30)
    
    test_choice = input("\nVoulez-vous lancer les tests automatiques? (o/N): ").strip().lower()
    
    if test_choice in ['o', 'oui', 'y', 'yes']:
        print("\nLancement des tests...")
        os.system("python test_communication.py")
    
    sms_choice = input("\nVoulez-vous envoyer un SMS de test? (o/N): ").strip().lower()
    
    if sms_choice in ['o', 'oui', 'y', 'yes']:
        test_phone = os.getenv('TEST_PHONE_NUMBER')
        if test_phone:
            print(f"\nEnvoi SMS de test vers {test_phone}...")
            try:
                from communication_service import CommunicationManager
                comm = CommunicationManager()
                result = comm.test_communication(test_phone)
                print("✅ SMS de test envoyé")
                print(f"   Résultat: {result}")
            except Exception as e:
                print(f"❌ Erreur envoi SMS: {e}")
        else:
            print("❌ TEST_PHONE_NUMBER non configuré")

def show_next_steps():
    """Affiche les prochaines étapes"""
    print("\n🎯 PROCHAINES ÉTAPES")
    print("-" * 30)
    print("1. Démarrer le serveur Flask:")
    print("   python app.py")
    print()
    print("2. Tester les endpoints:")
    print("   http://localhost:5000")
    print("   http://localhost:5000/test/twiml")
    print()
    print("3. Configurer les webhooks (optionnel):")
    print("   - Installer ngrok: https://ngrok.com/")
    print("   - Exposer le serveur: ngrok http 5000")
    print("   - Configurer dans Twilio Console")
    print()
    print("4. Intégrer avec les modèles de données")
    print()
    print("📚 Documentation complète: CONFIGURATION_TWILIO.md")

def main():
    """Fonction principale"""
    print_header()
    
    # Vérifier le fichier .env
    if not check_env_file():
        sys.exit(1)
    
    # Collecter les credentials
    credentials = collect_twilio_credentials()
    
    # Mettre à jour le fichier .env
    update_env_file(credentials)
    
    # Tester la configuration
    if test_configuration():
        print("\n🎉 Configuration Twilio réussie!")
        
        # Proposer les tests
        run_communication_tests()
        
        # Afficher les prochaines étapes
        show_next_steps()
    else:
        print("\n❌ Configuration échouée")
        print("Consultez CONFIGURATION_TWILIO.md pour plus d'aide")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Configuration interrompue")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)