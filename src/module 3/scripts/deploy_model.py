#!/usr/bin/env python3
"""
Script de déploiement du modèle ML
"""

import os
import sys
import shutil
import json
import subprocess
import requests
from datetime import datetime
import argparse
import time

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ModelDeployer:
    """Gestionnaire de déploiement des modèles"""
    
    def __init__(self, config: dict = None):
        self.config = config or self.get_default_config()
        self.deployment_info = {}
        
    def get_default_config(self) -> dict:
        """Configuration par défaut"""
        return {
            'model_path': 'models/ensemble',
            'api_path': 'src/api',
            'deployment_path': 'deployment/model_service',
            'docker_image': 'blood-stock-ml-service',
            'docker_tag': 'latest',
            'port': 8000,
            'health_check_timeout': 60,
            'platforms': {
                'docker': True,
                'huggingface': False,
                'gcp': False
            }
        }
    
    def validate_models(self) -> bool:
        """Valide que les modèles sont prêts pour le déploiement"""
        print("🔍 Validation des modèles...")
        
        required_paths = [
            self.config['model_path'],
            self.config['api_path'],
            'models/preprocessor'
        ]
        
        for path in required_paths:
            if not os.path.exists(path):
                print(f"❌ Chemin manquant: {path}")
                return False
        
        # Vérifier les fichiers de modèles essentiels
        ensemble_files = [
            f"{self.config['model_path']}/ensemble_model.pkl"
        ]
        
        for file_path in ensemble_files:
            if not os.path.exists(file_path):
                print(f"❌ Fichier de modèle manquant: {file_path}")
                return False
        
        print("✅ Validation des modèles réussie")
        return True
    
    def prepare_deployment_package(self) -> bool:
        """Prépare le package de déploiement"""
        print("📦 Préparation du package de déploiement...")
        
        deployment_path = self.config['deployment_path']
        
        # Créer le répertoire de déploiement
        if os.path.exists(deployment_path):
            shutil.rmtree(deployment_path)
        os.makedirs(deployment_path, exist_ok=True)
        
        # Copier les fichiers nécessaires
        files_to_copy = [
            ('src/', f'{deployment_path}/src/'),
            ('models/', f'{deployment_path}/models/'),
            ('requirements.txt', f'{deployment_path}/requirements.txt'),
            ('Dockerfile', f'{deployment_path}/Dockerfile'),
            ('docker-entrypoint.sh', f'{deployment_path}/docker-entrypoint.sh')
        ]
        
        for src, dst in files_to_copy:
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                print(f"✅ Copié: {src} -> {dst}")
            except Exception as e:
                print(f"❌ Erreur copie {src}: {str(e)}")
                return False
        
        # Créer un fichier de métadonnées de déploiement
        metadata = {
            'deployment_timestamp': datetime.now().isoformat(),
            'model_version': '1.0.0',
            'api_version': '1.0.0',
            'config': self.config
        }
        
        with open(f'{deployment_path}/deployment_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Package de déploiement créé: {deployment_path}")
        return True
    
    def build_docker_image(self) -> bool:
        """Construit l'image Docker"""
        if not self.config['platforms']['docker']:
            print("🐳 Déploiement Docker désactivé")
            return True
            
        print("🐳 Construction de l'image Docker...")
        
        deployment_path = self.config['deployment_path']
        image_name = self.config['docker_image']
        tag = self.config['docker_tag']
        
        # Commande de build
        build_cmd = [
            'docker', 'build',
            '-t', f'{image_name}:{tag}',
            '-f', f'{deployment_path}/Dockerfile',
            deployment_path
        ]
        
        try:
            result = subprocess.run(build_cmd, capture_output=True, text=True, check=True)
            print("✅ Image Docker construite avec succès")
            
            # Vérifier la taille de l'image
            inspect_cmd = ['docker', 'inspect', f'{image_name}:{tag}', '--format={{.Size}}']
            size_result = subprocess.run(inspect_cmd, capture_output=True, text=True)
            if size_result.returncode == 0:
                size_bytes = int(size_result.stdout.strip())
                size_mb = size_bytes / (1024 * 1024)
                print(f"📏 Taille de l'image: {size_mb:.1f} MB")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur construction Docker: {e.stderr}")
            return False
    
    def test_docker_deployment(self) -> bool:
        """Teste le déploiement Docker localement"""
        if not self.config['platforms']['docker']:
            return True
            
        print("🧪 Test du déploiement Docker...")
        
        image_name = self.config['docker_image']
        tag = self.config['docker_tag']
        port = self.config['port']
        container_name = f'{image_name}-test'
        
        # Arrêter le conteneur s'il existe
        stop_cmd = ['docker', 'stop', container_name]
        subprocess.run(stop_cmd, capture_output=True)
        
        remove_cmd = ['docker', 'rm', container_name]
        subprocess.run(remove_cmd, capture_output=True)
        
        # Lancer le conteneur
        run_cmd = [
            'docker', 'run',
            '-d',
            '--name', container_name,
            '-p', f'{port}:{port}',
            '-e', 'ENVIRONMENT=test',
            f'{image_name}:{tag}'
        ]
        
        try:
            result = subprocess.run(run_cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            print(f"✅ Conteneur lancé: {container_id[:12]}")
            
            # Attendre que le service soit prêt
            print("⏳ Attente du démarrage du service...")
            max_wait = self.config['health_check_timeout']
            
            for i in range(max_wait):
                try:
                    response = requests.get(f'http://localhost:{port}/health', timeout=5)
                    if response.status_code == 200:
                        print("✅ Service démarré et opérationnel")
                        
                        # Test de prédiction
                        test_data = {
                            'data': [{
                                'hospital': 'Test Hospital',
                                'blood_type': 'O+',
                                'stock_initial': 50,
                                'demand': 10,
                                'supply': 5,
                                'temperature': 4.0,
                                'days_to_expiry': 15,
                                'quality_score': 95.0,
                                'quality_comment': 'Test'
                            }]
                        }
                        
                        pred_response = requests.post(
                            f'http://localhost:{port}/predict',
                            json=test_data,
                            timeout=10
                        )
                        
                        if pred_response.status_code == 200:
                            print("✅ Test de prédiction réussi")
                            result_data = pred_response.json()
                            print(f"📊 Prédiction: {result_data.get('predictions', [])}")
                        else:
                            print(f"⚠️ Test de prédiction échoué: {pred_response.status_code}")
                        
                        break
                        
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    if i % 10 == 0:
                        print(f"⏳ Attente... ({i}/{max_wait}s)")
            else:
                print("❌ Timeout: le service n'a pas démarré à temps")
                return False
            
            # Arrêter le conteneur de test
            subprocess.run(stop_cmd, capture_output=True)
            subprocess.run(remove_cmd, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lancement conteneur: {e.stderr}")
            return False
    
    def deploy_to_huggingface(self) -> bool:
        """Déploie sur HuggingFace Spaces"""
        if not self.config['platforms']['huggingface']:
            print("🤗 Déploiement HuggingFace désactivé")
            return True
            
        print("🤗 Déploiement vers HuggingFace Spaces...")
        
        # Ici, vous implémenteriez le déploiement HuggingFace
        # Par exemple, en utilisant l'API HuggingFace ou git
        
        print("⚠️ Déploiement HuggingFace non implémenté dans cette démo")
        return True
    
    def deploy_to_gcp(self) -> bool:
        """Déploie sur Google Cloud Run"""
        if not self.config['platforms']['gcp']:
            print("☁️ Déploiement GCP désactivé")
            return True
            
        print("☁️ Déploiement vers Google Cloud Run...")
        
        # Ici, vous implémenteriez le déploiement GCP
        # Par exemple, en utilisant gcloud CLI
        
        print("⚠️ Déploiement GCP non implémenté dans cette démo")
        return True
    
    def create_deployment_report(self) -> dict:
        """Crée un rapport de déploiement"""
        report = {
            'deployment_timestamp': datetime.now().isoformat(),
            'status': 'success',
            'platforms': {},
            'config': self.config,
            'deployment_info': self.deployment_info
        }
        
        # Statut par plateforme
        for platform in self.config['platforms']:
            if self.config['platforms'][platform]:
                report['platforms'][platform] = 'deployed'
            else:
                report['platforms'][platform] = 'disabled'
        
        return report
    
    def save_deployment_report(self, report: dict):
        """Sauvegarde le rapport de déploiement"""
        os.makedirs('deployment', exist_ok=True)
        
        with open('deployment/deployment_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("✅ Rapport de déploiement sauvegardé: deployment/deployment_report.json")
    
    def deploy(self) -> bool:
        """Lance le processus de déploiement complet"""
        print("🚀 DÉMARRAGE DU DÉPLOIEMENT")
        print("="*50)
        
        # Étape 1: Validation
        if not self.validate_models():
            print("❌ Échec de la validation")
            return False
        
        # Étape 2: Préparation du package
        if not self.prepare_deployment_package():
            print("❌ Échec de la préparation du package")
            return False
        
        # Étape 3: Construction Docker
        if not self.build_docker_image():
            print("❌ Échec de la construction Docker")
            return False
        
        # Étape 4: Test Docker
        if not self.test_docker_deployment():
            print("❌ Échec du test Docker")
            return False
        
        # Étape 5: Déploiements sur les plateformes
        if not self.deploy_to_huggingface():
            print("❌ Échec du déploiement HuggingFace")
            return False
        
        if not self.deploy_to_gcp():
            print("❌ Échec du déploiement GCP")
            return False
        
        # Étape 6: Rapport final
        report = self.create_deployment_report()
        self.save_deployment_report(report)
        
        print("\n🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS!")
        print("="*50)
        
        return True

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Script de déploiement des modèles ML")
    parser.add_argument('--config', type=str, help="Fichier de configuration JSON")
    parser.add_argument('--docker-only', action='store_true', help="Déploiement Docker uniquement")
    parser.add_argument('--skip-tests', action='store_true', help="Ignorer les tests")
    parser.add_argument('--port', type=int, default=8000, help="Port pour le service")
    
    args = parser.parse_args()
    
    # Charger la configuration
    config = None
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Créer le déployeur
    deployer = ModelDeployer(config)
    
    # Ajuster la configuration selon les arguments
    if args.docker_only:
        deployer.config['platforms'] = {'docker': True, 'huggingface': False, 'gcp': False}
    
    if args.port:
        deployer.config['port'] = args.port
    
    # Lancer le déploiement
    success = deployer.deploy()
    
    if success:
        print("\n📋 INFORMATIONS DE DÉPLOIEMENT:")
        print(f"🐳 Image Docker: {deployer.config['docker_image']}:{deployer.config['docker_tag']}")
        print(f"🌐 Port local: {deployer.config['port']}")
        print(f"📁 Package: {deployer.config['deployment_path']}")
        
        if deployer.config['platforms']['docker']:
            print("\n🚀 Pour lancer le service:")
            print(f"docker run -p {deployer.config['port']}:{deployer.config['port']} {deployer.config['docker_image']}:{deployer.config['docker_tag']}")
        
        sys.exit(0)
    else:
        print("❌ Déploiement échoué")
        sys.exit(1)

if __name__ == "__main__":
    main()