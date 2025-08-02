#!/usr/bin/env python3
"""
Collecteur de données médicales de l'Organisation Mondiale de la Santé (OMS/WHO)
Collecte automatisée de fiches techniques, directives et publications médicales
"""

import requests
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MedicalDocument:
    """Structure pour un document médical collecté"""
    title: str
    content: str
    url: str
    source: str
    category: str
    language: str
    publication_date: Optional[datetime]
    last_updated: Optional[datetime]
    document_type: str
    specialty: Optional[str]
    keywords: List[str]
    reliability_score: float
    file_hash: str
    metadata: Dict[str, Any]

class WHOCollector:
    """Collecteur spécialisé pour les données de l'OMS"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', 'https://www.who.int')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        })
        self.collected_documents = []
        self.failed_urls = []
        
        # Délai entre les requêtes pour respecter le serveur
        self.request_delay = config.get('request_delay', 1.0)
        
        # Catégories prioritaires pour le Cameroun/Afrique
        self.priority_topics = [
            'malaria', 'tuberculosis', 'hiv', 'aids', 'maternal-health',
            'child-health', 'nutrition', 'infectious-diseases', 'vaccines',
            'emergency-preparedness', 'mental-health', 'noncommunicable-diseases',
            'hypertension', 'diabetes', 'cancer', 'respiratory-diseases'
        ]
    
    def collect_fact_sheets(self, max_documents: int = 50) -> List[MedicalDocument]:
        """Collecte les fiches techniques de l'OMS"""
        logger.info("🔍 Collecte des fiches techniques OMS...")
        
        fact_sheets_url = urljoin(self.base_url, '/news-room/fact-sheets')
        
        try:
            response = self.session.get(fact_sheets_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trouver tous les liens vers les fiches techniques
            fact_sheet_links = self._extract_fact_sheet_links(soup)
            
            logger.info(f"📄 Trouvé {len(fact_sheet_links)} fiches techniques")
            
            collected = 0
            for link_info in fact_sheet_links[:max_documents]:
                if collected >= max_documents:
                    break
                
                try:
                    document = self._collect_single_fact_sheet(link_info)
                    if document:
                        self.collected_documents.append(document)
                        collected += 1
                        logger.info(f"✅ Collecté: {document.title[:60]}...")
                    
                    # Respecter le délai entre requêtes
                    time.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la collecte de {link_info.get('url', 'URL inconnue')}: {e}")
                    self.failed_urls.append(link_info.get('url', ''))
                    continue
            
            logger.info(f"📊 Collecte terminée: {collected} documents collectés")
            return self.collected_documents
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte des fiches techniques: {e}")
            return []
    
    def _extract_fact_sheet_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrait les liens vers les fiches techniques"""
        links = []
        
        # Chercher les liens dans la structure typique de l'OMS
        for link_element in soup.find_all('a', href=True):
            href = link_element.get('href', '')
            
            # Filtrer les liens vers les fiches techniques
            if '/fact-sheets/' in href or '/news-room/fact-sheets/' in href:
                full_url = urljoin(self.base_url, href)
                title = link_element.get_text(strip=True)
                
                # Vérifier si c'est un sujet prioritaire
                is_priority = any(topic in href.lower() or topic in title.lower() 
                                for topic in self.priority_topics)
                
                links.append({
                    'url': full_url,
                    'title': title,
                    'is_priority': is_priority
                })
        
        # Trier par priorité
        links.sort(key=lambda x: x['is_priority'], reverse=True)
        
        # Supprimer les doublons
        seen_urls = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        return unique_links
    
    def _collect_single_fact_sheet(self, link_info: Dict[str, str]) -> Optional[MedicalDocument]:
        """Collecte une seule fiche technique"""
        url = link_info['url']
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire le titre
            title = self._extract_title(soup, link_info.get('title', ''))
            
            # Extraire le contenu principal
            content = self._extract_content(soup)
            
            if not content or len(content) < 200:
                logger.warning(f"⚠️ Contenu trop court pour {url}")
                return None
            
            # Extraire les métadonnées
            metadata = self._extract_metadata(soup, url)
            
            # Déterminer la catégorie et spécialité
            category, specialty = self._categorize_document(title, content, url)
            
            # Extraire les mots-clés
            keywords = self._extract_keywords(title, content, metadata)
            
            # Calculer le hash du contenu
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Créer le document
            document = MedicalDocument(
                title=title,
                content=content,
                url=url,
                source="WHO",
                category=category,
                language=self._detect_language(content),
                publication_date=metadata.get('publication_date'),
                last_updated=metadata.get('last_updated'),
                document_type="fact-sheet",
                specialty=specialty,
                keywords=keywords,
                reliability_score=0.95,  # OMS = très fiable
                file_hash=content_hash,
                metadata=metadata
            )
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte de {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, fallback_title: str) -> str:
        """Extrait le titre du document"""
        # Essayer différents sélecteurs pour le titre
        title_selectors = [
            'h1.page-heading',
            'h1',
            '.page-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title and len(title) > 5:
                    return title
        
        return fallback_title or "Document OMS sans titre"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extrait le contenu principal du document"""
        # Supprimer les éléments non pertinents
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Essayer différents sélecteurs pour le contenu principal
        content_selectors = [
            '.page-content',
            '.main-content',
            '.content',
            'main',
            'article',
            '.text-content'
        ]
        
        content = ""
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(separator='\n', strip=True)
                if len(content) > 500:  # Contenu substantiel
                    break
        
        # Si aucun sélecteur spécifique ne fonctionne, prendre le body
        if not content or len(content) < 200:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        # Nettoyer le contenu
        content = self._clean_content(content)
        
        return content
    
    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu extrait"""
        import re
        
        # Supprimer les lignes vides multiples
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Supprimer les espaces en début/fin de lignes
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)
        
        # Supprimer les caractères de contrôle
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', content)
        
        return content.strip()
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait les métadonnées du document"""
        metadata = {
            'url': url,
            'collected_at': datetime.now(),
            'source_domain': urlparse(url).netloc
        }
        
        # Chercher les métadonnées dans les balises meta
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name in ['description', 'keywords', 'author', 'date']:
                metadata[name] = content
            elif property_attr.startswith('og:'):
                metadata[property_attr] = content
            elif name == 'dcterms.created':
                metadata['creation_date'] = content
            elif name == 'dcterms.modified':
                metadata['modification_date'] = content
        
        # Chercher les dates dans le contenu
        date_patterns = [
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        text_content = soup.get_text()
        for pattern in date_patterns:
            import re
            matches = re.findall(pattern, text_content)
            if matches:
                metadata['found_dates'] = matches[:3]  # Garder les 3 premières
                break
        
        return metadata
    
    def _categorize_document(self, title: str, content: str, url: str) -> tuple[str, Optional[str]]:
        """Détermine la catégorie et spécialité du document"""
        title_lower = title.lower()
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Mapping des catégories
        category_keywords = {
            'maladies_infectieuses': ['malaria', 'tuberculosis', 'hiv', 'aids', 'hepatitis', 'dengue', 'cholera', 'meningitis'],
            'maladies_chroniques': ['diabetes', 'hypertension', 'cancer', 'cardiovascular', 'chronic'],
            'sante_maternelle': ['maternal', 'pregnancy', 'childbirth', 'prenatal', 'postnatal'],
            'pediatrie': ['child', 'children', 'infant', 'pediatric', 'vaccination'],
            'nutrition': ['nutrition', 'malnutrition', 'food', 'diet', 'obesity'],
            'sante_mentale': ['mental health', 'depression', 'anxiety', 'suicide', 'psychological'],
            'urgences': ['emergency', 'outbreak', 'epidemic', 'pandemic', 'disaster'],
            'prevention': ['prevention', 'vaccine', 'immunization', 'screening', 'health promotion']
        }
        
        # Spécialités médicales
        specialty_keywords = {
            'Cardiologie': ['heart', 'cardiovascular', 'cardiac', 'hypertension'],
            'Pneumologie': ['respiratory', 'lung', 'tuberculosis', 'pneumonia'],
            'Infectiologie': ['infectious', 'virus', 'bacteria', 'infection', 'antimicrobial'],
            'Pédiatrie': ['child', 'children', 'infant', 'pediatric', 'neonatal'],
            'Gynécologie': ['maternal', 'women', 'reproductive', 'pregnancy'],
            'Psychiatrie': ['mental', 'psychological', 'depression', 'anxiety'],
            'Oncologie': ['cancer', 'tumor', 'oncology', 'chemotherapy']
        }
        
        # Déterminer la catégorie
        category = 'general'
        max_score = 0
        
        for cat, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords 
                       if keyword in title_lower or keyword in content_lower[:1000])
            if score > max_score:
                max_score = score
                category = cat
        
        # Déterminer la spécialité
        specialty = None
        max_specialty_score = 0
        
        for spec, keywords in specialty_keywords.items():
            score = sum(1 for keyword in keywords 
                       if keyword in title_lower or keyword in content_lower[:1000])
            if score > max_specialty_score:
                max_specialty_score = score
                specialty = spec
        
        return category, specialty if max_specialty_score > 0 else None
    
    def _extract_keywords(self, title: str, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Extrait les mots-clés du document"""
        keywords = []
        
        # Mots-clés des métadonnées
        if 'keywords' in metadata:
            meta_keywords = metadata['keywords'].split(',')
            keywords.extend([kw.strip() for kw in meta_keywords if kw.strip()])
        
        # Mots-clés médicaux importants
        medical_terms = [
            'diagnostic', 'traitement', 'symptômes', 'prévention', 'vaccination',
            'médicament', 'thérapie', 'chirurgie', 'examen', 'dépistage',
            'épidémiologie', 'pathologie', 'clinique', 'hospitalisation'
        ]
        
        content_lower = content.lower()
        for term in medical_terms:
            if term in content_lower:
                keywords.append(term)
        
        # Limiter à 10 mots-clés maximum
        return list(set(keywords))[:10]
    
    def _detect_language(self, content: str) -> str:
        """Détecte la langue du contenu"""
        try:
            from langdetect import detect
            detected = detect(content[:1000])  # Analyser les premiers 1000 caractères
            return detected
        except:
            # Détection simple basée sur des mots courants
            french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'mais', 'donc']
            english_words = ['the', 'and', 'or', 'but', 'of', 'in', 'to', 'for', 'with', 'by']
            
            content_lower = content.lower()
            french_count = sum(1 for word in french_words if f' {word} ' in content_lower)
            english_count = sum(1 for word in english_words if f' {word} ' in content_lower)
            
            if french_count > english_count:
                return 'fr'
            elif english_count > 0:
                return 'en'
            else:
                return 'unknown'
    
    def save_documents(self, output_path: Path) -> bool:
        """Sauvegarde les documents collectés"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder chaque document
            for i, doc in enumerate(self.collected_documents):
                filename = f"who_document_{i+1:03d}_{doc.file_hash[:8]}.json"
                filepath = output_path / filename
                
                # Convertir en dictionnaire pour la sérialisation
                doc_dict = {
                    'title': doc.title,
                    'content': doc.content,
                    'url': doc.url,
                    'source': doc.source,
                    'category': doc.category,
                    'language': doc.language,
                    'publication_date': doc.publication_date.isoformat() if doc.publication_date else None,
                    'last_updated': doc.last_updated.isoformat() if doc.last_updated else None,
                    'document_type': doc.document_type,
                    'specialty': doc.specialty,
                    'keywords': doc.keywords,
                    'reliability_score': doc.reliability_score,
                    'file_hash': doc.file_hash,
                    'metadata': {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v 
                               for k, v in doc.metadata.items()}
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(doc_dict, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder le résumé
            summary = {
                'collection_date': datetime.now().isoformat(),
                'total_documents': len(self.collected_documents),
                'failed_urls': self.failed_urls,
                'categories': {},
                'languages': {},
                'specialties': {}
            }
            
            # Statistiques par catégorie
            for doc in self.collected_documents:
                summary['categories'][doc.category] = summary['categories'].get(doc.category, 0) + 1
                summary['languages'][doc.language] = summary['languages'].get(doc.language, 0) + 1
                if doc.specialty:
                    summary['specialties'][doc.specialty] = summary['specialties'].get(doc.specialty, 0) + 1
            
            summary_path = output_path / "who_collection_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Documents sauvegardés dans {output_path}")
            logger.info(f"📊 Résumé: {summary_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de collecte"""
        if not self.collected_documents:
            return {'total': 0}
        
        stats = {
            'total_documents': len(self.collected_documents),
            'failed_urls': len(self.failed_urls),
            'success_rate': len(self.collected_documents) / (len(self.collected_documents) + len(self.failed_urls)) * 100,
            'categories': {},
            'languages': {},
            'specialties': {},
            'avg_content_length': sum(len(doc.content) for doc in self.collected_documents) / len(self.collected_documents)
        }
        
        for doc in self.collected_documents:
            stats['categories'][doc.category] = stats['categories'].get(doc.category, 0) + 1
            stats['languages'][doc.language] = stats['languages'].get(doc.language, 0) + 1
            if doc.specialty:
                stats['specialties'][doc.specialty] = stats['specialties'].get(doc.specialty, 0) + 1
        
        return stats

def main():
    """Fonction principale pour tester le collecteur"""
    config = {
        'base_url': 'https://www.who.int',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'request_delay': 2.0
    }
    
    collector = WHOCollector(config)
    
    logger.info("🚀 Démarrage de la collecte OMS...")
    documents = collector.collect_fact_sheets(max_documents=10)  # Test avec 10 documents
    
    if documents:
        output_path = Path("../data/raw/who")
        collector.save_documents(output_path)
        
        stats = collector.get_collection_stats()
        logger.info(f"📈 Statistiques: {stats}")
    else:
        logger.error("❌ Aucun document collecté")

if __name__ == "__main__":
    main()