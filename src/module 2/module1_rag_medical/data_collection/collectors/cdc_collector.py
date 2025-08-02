#!/usr/bin/env python3
"""
Collecteur de données médicales du CDC (Centers for Disease Control and Prevention)
Collecte automatisée de directives, recommandations et informations de santé publique
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
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CDCDocument:
    """Structure pour un document CDC collecté"""
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
    cdc_topic: Optional[str]
    target_audience: str

class CDCCollector:
    """Collecteur spécialisé pour les données du CDC"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', 'https://www.cdc.gov')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        })
        self.collected_documents = []
        self.failed_urls = []
        
        # Délai entre les requêtes
        self.request_delay = config.get('request_delay', 1.5)
        
        # Sujets prioritaires pour l'Afrique/contexte international
        self.priority_topics = [
            'infectious-diseases', 'malaria', 'tuberculosis', 'hiv-aids',
            'vaccines', 'immunization', 'travel-health', 'global-health',
            'maternal-health', 'child-health', 'nutrition', 'emergency-preparedness',
            'outbreak-investigation', 'disease-surveillance', 'prevention',
            'chronic-diseases', 'diabetes', 'hypertension', 'mental-health'
        ]
        
        # Endpoints principaux du CDC
        self.main_endpoints = [
            '/diseases-conditions',
            '/healthy-living',
            '/vaccines',
            '/travel',
            '/globalhealth',
            '/injury-prevention',
            '/chronic-disease-prevention'
        ]
    
    def collect_disease_information(self, max_documents: int = 40) -> List[CDCDocument]:
        """Collecte les informations sur les maladies du CDC"""
        logger.info("🔍 Collecte des informations sur les maladies CDC...")
        
        diseases_url = urljoin(self.base_url, '/diseases-conditions')
        
        try:
            response = self.session.get(diseases_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire les liens vers les pages de maladies
            disease_links = self._extract_disease_links(soup)
            
            logger.info(f"🦠 Trouvé {len(disease_links)} pages de maladies")
            
            collected = 0
            for link_info in disease_links[:max_documents]:
                if collected >= max_documents:
                    break
                
                try:
                    document = self._collect_single_disease_page(link_info)
                    if document:
                        self.collected_documents.append(document)
                        collected += 1
                        logger.info(f"✅ Collecté: {document.title[:60]}...")
                    
                    time.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la collecte de {link_info.get('url', 'URL inconnue')}: {e}")
                    self.failed_urls.append(link_info.get('url', ''))
                    continue
            
            logger.info(f"📊 Collecte maladies terminée: {collected} documents")
            return self.collected_documents
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte des maladies CDC: {e}")
            return []
    
    def collect_vaccine_information(self, max_documents: int = 30) -> List[CDCDocument]:
        """Collecte les informations sur les vaccins"""
        logger.info("💉 Collecte des informations sur les vaccins CDC...")
        
        vaccines_url = urljoin(self.base_url, '/vaccines')
        
        try:
            response = self.session.get(vaccines_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            vaccine_links = self._extract_vaccine_links(soup)
            
            logger.info(f"💉 Trouvé {len(vaccine_links)} pages de vaccins")
            
            collected = 0
            for link_info in vaccine_links[:max_documents]:
                if collected >= max_documents:
                    break
                
                try:
                    document = self._collect_single_vaccine_page(link_info)
                    if document:
                        self.collected_documents.append(document)
                        collected += 1
                        logger.info(f"✅ Collecté: {document.title[:60]}...")
                    
                    time.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur vaccination {link_info.get('url', 'URL inconnue')}: {e}")
                    self.failed_urls.append(link_info.get('url', ''))
                    continue
            
            logger.info(f"📊 Collecte vaccins terminée: {collected} documents")
            return self.collected_documents
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte des vaccins CDC: {e}")
            return []
    
    def collect_travel_health(self, max_documents: int = 25) -> List[CDCDocument]:
        """Collecte les informations de santé voyage (important pour l'Afrique)"""
        logger.info("✈️ Collecte des informations santé voyage CDC...")
        
        travel_url = urljoin(self.base_url, '/travel')
        
        try:
            response = self.session.get(travel_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            travel_links = self._extract_travel_links(soup)
            
            logger.info(f"✈️ Trouvé {len(travel_links)} pages santé voyage")
            
            collected = 0
            for link_info in travel_links[:max_documents]:
                if collected >= max_documents:
                    break
                
                try:
                    document = self._collect_single_travel_page(link_info)
                    if document:
                        self.collected_documents.append(document)
                        collected += 1
                        logger.info(f"✅ Collecté: {document.title[:60]}...")
                    
                    time.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Erreur voyage {link_info.get('url', 'URL inconnue')}: {e}")
                    self.failed_urls.append(link_info.get('url', ''))
                    continue
            
            logger.info(f"📊 Collecte voyage terminée: {collected} documents")
            return self.collected_documents
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte santé voyage CDC: {e}")
            return []
    
    def _extract_disease_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrait les liens vers les pages de maladies"""
        links = []
        
        # Chercher les liens dans la structure CDC
        for link_element in soup.find_all('a', href=True):
            href = link_element.get('href', '')
            
            # Filtrer les liens vers les maladies
            if any(pattern in href.lower() for pattern in 
                   ['/diseases-conditions/', '/disease/', '/condition/', '/health-topics/']):
                
                full_url = urljoin(self.base_url, href)
                title = link_element.get_text(strip=True)
                
                # Vérifier si c'est un sujet prioritaire
                is_priority = any(topic in href.lower() or topic in title.lower() 
                                for topic in self.priority_topics)
                
                # Extraire la catégorie depuis l'URL
                category = self._extract_category_from_url(href)
                
                links.append({
                    'url': full_url,
                    'title': title,
                    'is_priority': is_priority,
                    'category': category,
                    'type': 'disease'
                })
        
        return self._filter_and_sort_links(links)
    
    def _extract_vaccine_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrait les liens vers les pages de vaccins"""
        links = []
        
        for link_element in soup.find_all('a', href=True):
            href = link_element.get('href', '')
            
            if any(pattern in href.lower() for pattern in 
                   ['/vaccines/', '/vaccination/', '/immunization/']):
                
                full_url = urljoin(self.base_url, href)
                title = link_element.get_text(strip=True)
                
                # Priorité pour les vaccins importants en Afrique
                priority_vaccines = ['malaria', 'yellow-fever', 'meningitis', 'hepatitis', 
                                   'measles', 'polio', 'tuberculosis', 'covid']
                is_priority = any(vaccine in href.lower() or vaccine in title.lower() 
                                for vaccine in priority_vaccines)
                
                links.append({
                    'url': full_url,
                    'title': title,
                    'is_priority': is_priority,
                    'category': 'vaccination',
                    'type': 'vaccine'
                })
        
        return self._filter_and_sort_links(links)
    
    def _extract_travel_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrait les liens vers les pages de santé voyage"""
        links = []
        
        for link_element in soup.find_all('a', href=True):
            href = link_element.get('href', '')
            
            if any(pattern in href.lower() for pattern in 
                   ['/travel/', '/destinations/', '/travel-health/']):
                
                full_url = urljoin(self.base_url, href)
                title = link_element.get_text(strip=True)
                
                # Priorité pour l'Afrique
                africa_keywords = ['africa', 'cameroon', 'central-africa', 'sub-saharan']
                is_priority = any(keyword in href.lower() or keyword in title.lower() 
                                for keyword in africa_keywords)
                
                links.append({
                    'url': full_url,
                    'title': title,
                    'is_priority': is_priority,
                    'category': 'travel_health',
                    'type': 'travel'
                })
        
        return self._filter_and_sort_links(links)
    
    def _filter_and_sort_links(self, links: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Filtre et trie les liens par priorité"""
        # Supprimer les doublons
        seen_urls = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen_urls and len(link['title']) > 5:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        # Trier par priorité
        unique_links.sort(key=lambda x: x['is_priority'], reverse=True)
        
        return unique_links
    
    def _extract_category_from_url(self, url: str) -> str:
        """Extrait la catégorie depuis l'URL"""
        url_lower = url.lower()
        
        if 'infectious' in url_lower or 'infection' in url_lower:
            return 'maladies_infectieuses'
        elif 'chronic' in url_lower or 'diabetes' in url_lower or 'hypertension' in url_lower:
            return 'maladies_chroniques'
        elif 'vaccine' in url_lower or 'immunization' in url_lower:
            return 'prevention'
        elif 'travel' in url_lower:
            return 'sante_voyage'
        elif 'mental' in url_lower or 'behavioral' in url_lower:
            return 'sante_mentale'
        elif 'injury' in url_lower or 'safety' in url_lower:
            return 'securite'
        else:
            return 'general'
    
    def _collect_single_disease_page(self, link_info: Dict[str, str]) -> Optional[CDCDocument]:
        """Collecte une seule page de maladie"""
        return self._collect_single_page(link_info, 'disease-info')
    
    def _collect_single_vaccine_page(self, link_info: Dict[str, str]) -> Optional[CDCDocument]:
        """Collecte une seule page de vaccin"""
        return self._collect_single_page(link_info, 'vaccine-info')
    
    def _collect_single_travel_page(self, link_info: Dict[str, str]) -> Optional[CDCDocument]:
        """Collecte une seule page de santé voyage"""
        return self._collect_single_page(link_info, 'travel-health')
    
    def _collect_single_page(self, link_info: Dict[str, str], doc_type: str) -> Optional[CDCDocument]:
        """Collecte une seule page CDC"""
        url = link_info['url']
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire le titre
            title = self._extract_title(soup, link_info.get('title', ''))
            
            # Extraire le contenu principal
            content = self._extract_content(soup)
            
            if not content or len(content) < 300:
                logger.warning(f"⚠️ Contenu trop court pour {url}")
                return None
            
            # Extraire les métadonnées
            metadata = self._extract_metadata(soup, url)
            
            # Déterminer la catégorie et spécialité
            category = link_info.get('category', 'general')
            specialty = self._determine_specialty(title, content)
            
            # Extraire les mots-clés
            keywords = self._extract_keywords(title, content, metadata)
            
            # Déterminer l'audience cible
            target_audience = self._determine_target_audience(content, url)
            
            # Calculer le hash du contenu
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Créer le document
            document = CDCDocument(
                title=title,
                content=content,
                url=url,
                source="CDC",
                category=category,
                language="en",  # CDC principalement en anglais
                publication_date=metadata.get('publication_date'),
                last_updated=metadata.get('last_updated'),
                document_type=doc_type,
                specialty=specialty,
                keywords=keywords,
                reliability_score=0.93,  # CDC = très fiable
                file_hash=content_hash,
                metadata=metadata,
                cdc_topic=link_info.get('type'),
                target_audience=target_audience
            )
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte de {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, fallback_title: str) -> str:
        """Extrait le titre du document CDC"""
        title_selectors = [
            'h1.page-title',
            'h1.content-title', 
            'h1',
            '.page-heading',
            'title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title and len(title) > 5 and 'CDC' not in title[:10]:
                    return title
        
        return fallback_title or "Document CDC sans titre"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extrait le contenu principal du document CDC"""
        # Supprimer les éléments non pertinents
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', '.sidebar']):
            element.decompose()
        
        # Sélecteurs spécifiques au CDC
        content_selectors = [
            '.content-area',
            '.main-content',
            '.page-content',
            '#content',
            'main',
            'article',
            '.syndicate'
        ]
        
        content = ""
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(separator='\n', strip=True)
                if len(content) > 500:
                    break
        
        # Fallback vers le body si nécessaire
        if not content or len(content) < 300:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        return self._clean_content(content)
    
    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu extrait"""
        # Supprimer les mentions CDC répétitives
        content = re.sub(r'CDC\s*[-–]?\s*', '', content)
        content = re.sub(r'Centers for Disease Control and Prevention\s*[-–]?\s*', '', content)
        
        # Supprimer les lignes vides multiples
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Supprimer les espaces en début/fin de lignes
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)
        
        # Supprimer les caractères de contrôle
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', content)
        
        return content.strip()
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait les métadonnées du document CDC"""
        metadata = {
            'url': url,
            'collected_at': datetime.now(),
            'source_domain': 'cdc.gov'
        }
        
        # Métadonnées des balises meta
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name in ['description', 'keywords', 'author', 'date', 'last-modified']:
                metadata[name] = content
            elif property_attr.startswith('og:'):
                metadata[property_attr] = content
            elif name == 'cdc:last_updated':
                metadata['cdc_last_updated'] = content
            elif name == 'cdc:content_id':
                metadata['cdc_content_id'] = content
        
        # Chercher les dates de mise à jour CDC
        date_text = soup.get_text()
        date_patterns = [
            r'Last Reviewed:\s*([A-Za-z]+ \d{1,2}, \d{4})',
            r'Last Updated:\s*([A-Za-z]+ \d{1,2}, \d{4})',
            r'Updated\s*([A-Za-z]+ \d{1,2}, \d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                metadata['found_update_date'] = match.group(1)
                break
        
        return metadata
    
    def _determine_specialty(self, title: str, content: str) -> Optional[str]:
        """Détermine la spécialité médicale"""
        text = (title + ' ' + content[:1000]).lower()
        
        specialty_keywords = {
            'Infectiologie': ['infectious', 'infection', 'virus', 'bacteria', 'antimicrobial', 'outbreak'],
            'Cardiologie': ['heart', 'cardiovascular', 'cardiac', 'hypertension', 'stroke'],
            'Pneumologie': ['respiratory', 'lung', 'tuberculosis', 'pneumonia', 'asthma'],
            'Pédiatrie': ['child', 'children', 'infant', 'pediatric', 'adolescent'],
            'Gynécologie': ['women', 'reproductive', 'pregnancy', 'maternal'],
            'Psychiatrie': ['mental', 'behavioral', 'depression', 'anxiety', 'suicide'],
            'Médecine Préventive': ['prevention', 'vaccine', 'screening', 'health promotion'],
            'Médecine du Voyage': ['travel', 'international', 'destination', 'traveler'],
            'Urgences': ['emergency', 'urgent', 'acute', 'crisis']
        }
        
        max_score = 0
        best_specialty = None
        
        for specialty, keywords in specialty_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > max_score:
                max_score = score
                best_specialty = specialty
        
        return best_specialty if max_score > 0 else None
    
    def _determine_target_audience(self, content: str, url: str) -> str:
        """Détermine l'audience cible"""
        content_lower = content.lower()
        url_lower = url.lower()
        
        if any(term in content_lower for term in ['healthcare provider', 'clinician', 'physician']):
            return 'healthcare_providers'
        elif any(term in url_lower for term in ['travelers', 'travel']):
            return 'travelers'
        elif any(term in content_lower for term in ['parents', 'family', 'patient']):
            return 'patients_families'
        else:
            return 'general_public'
    
    def _extract_keywords(self, title: str, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Extrait les mots-clés du document"""
        keywords = []
        
        # Mots-clés des métadonnées
        if 'keywords' in metadata:
            meta_keywords = metadata['keywords'].split(',')
            keywords.extend([kw.strip() for kw in meta_keywords if kw.strip()])
        
        # Termes médicaux CDC importants
        cdc_terms = [
            'prevention', 'treatment', 'symptoms', 'diagnosis', 'vaccine',
            'outbreak', 'surveillance', 'guidelines', 'recommendations',
            'public health', 'epidemiology', 'infection control'
        ]
        
        content_lower = content.lower()
        for term in cdc_terms:
            if term in content_lower:
                keywords.append(term)
        
        return list(set(keywords))[:10]
    
    def save_documents(self, output_path: Path) -> bool:
        """Sauvegarde les documents CDC collectés"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            for i, doc in enumerate(self.collected_documents):
                filename = f"cdc_document_{i+1:03d}_{doc.file_hash[:8]}.json"
                filepath = output_path / filename
                
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
                               for k, v in doc.metadata.items()},
                    'cdc_topic': doc.cdc_topic,
                    'target_audience': doc.target_audience
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(doc_dict, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder le résumé
            summary = {
                'collection_date': datetime.now().isoformat(),
                'total_documents': len(self.collected_documents),
                'failed_urls': self.failed_urls,
                'categories': {},
                'specialties': {},
                'document_types': {},
                'target_audiences': {}
            }
            
            for doc in self.collected_documents:
                summary['categories'][doc.category] = summary['categories'].get(doc.category, 0) + 1
                if doc.specialty:
                    summary['specialties'][doc.specialty] = summary['specialties'].get(doc.specialty, 0) + 1
                summary['document_types'][doc.document_type] = summary['document_types'].get(doc.document_type, 0) + 1
                summary['target_audiences'][doc.target_audience] = summary['target_audiences'].get(doc.target_audience, 0) + 1
            
            summary_path = output_path / "cdc_collection_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Documents CDC sauvegardés dans {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde CDC: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de collecte CDC"""
        if not self.collected_documents:
            return {'total': 0}
        
        stats = {
            'total_documents': len(self.collected_documents),
            'failed_urls': len(self.failed_urls),
            'success_rate': len(self.collected_documents) / (len(self.collected_documents) + len(self.failed_urls)) * 100,
            'categories': {},
            'specialties': {},
            'document_types': {},
            'target_audiences': {},
            'avg_content_length': sum(len(doc.content) for doc in self.collected_documents) / len(self.collected_documents)
        }
        
        for doc in self.collected_documents:
            stats['categories'][doc.category] = stats['categories'].get(doc.category, 0) + 1
            if doc.specialty:
                stats['specialties'][doc.specialty] = stats['specialties'].get(doc.specialty, 0) + 1
            stats['document_types'][doc.document_type] = stats['document_types'].get(doc.document_type, 0) + 1
            stats['target_audiences'][doc.target_audience] = stats['target_audiences'].get(doc.target_audience, 0) + 1
        
        return stats

def main():
    """Fonction principale pour tester le collecteur CDC"""
    config = {
        'base_url': 'https://www.cdc.gov',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'request_delay': 2.0
    }
    
    collector = CDCCollector(config)
    
    logger.info("🚀 Démarrage de la collecte CDC...")
    
    # Collecter différents types de documents
    collector.collect_disease_information(max_documents=5)
    collector.collect_vaccine_information(max_documents=3)
    collector.collect_travel_health(max_documents=2)
    
    if collector.collected_documents:
        output_path = Path("../data/raw/cdc")
        collector.save_documents(output_path)
        
        stats = collector.get_collection_stats()
        logger.info(f"📈 Statistiques CDC: {stats}")
    else:
        logger.error("❌ Aucun document CDC collecté")

if __name__ == "__main__":
    main()