#!/usr/bin/env python3
"""
Orchestateur principal pour la collecte et préparation des données médicales
Coordonne toutes les étapes du pipeline de traitement
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Imports des modules du projet
from config.settings import (
    PROJECT_ROOT, DATA_SOURCES, LANGUAGES, MEDICAL_CATEGORIES,
    COMMON_DISEASES, TARGET_DOCUMENTS, MAX_RETRY_ATTEMPTS
)

from collectors.who_collector import WHOCollector
from collectors.cdc_collector import CDCCollector
from processors.data_processor import MedicalDataProcessor
from validators.medical_validator import MedicalValidator
from translators.medical_translator import MedicalTranslator
from organizers.knowledge_organizer import KnowledgeOrganizer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataCollectionOrchestrator:
    """Orchestrateur principal pour la collecte et préparation des données"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.orchestrator_version = "1.0.0"
        
        # Chemins de sortie
        self.output_base = Path(config.get('output_path', PROJECT_ROOT / 'data'))
        self.raw_data_path = self.output_base / 'raw'
        self.processed_data_path = self.output_base / 'processed'
        self.validated_data_path = self.output_base / 'validated'
        self.translated_data_path = self.output_base / 'translated'
        self.organized_data_path = self.output_base / 'organized'
        
        # Créer les dossiers
        self._create_directories()
        
        # Initialiser les composants
        self.collectors = self._initialize_collectors()
        self.processor = MedicalDataProcessor(config.get('processing', {}))
        self.validator = MedicalValidator(config.get('validation', {}))
        self.translator = MedicalTranslator(config.get('translation', {}))
        self.organizer = KnowledgeOrganizer(config.get('organization', {}))
        
        # Statistiques globales
        self.pipeline_stats = {
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'documents_collected': 0,
            'documents_processed': 0,
            'documents_validated': 0,
            'documents_translated': 0,
            'documents_organized': 0,
            'errors': [],
            'warnings': [],
            'success_rate': 0.0
        }
    
    def _create_directories(self):
        """Crée les dossiers nécessaires"""
        directories = [
            self.raw_data_path,
            self.processed_data_path,
            self.validated_data_path,
            self.translated_data_path,
            self.organized_data_path,
            PROJECT_ROOT / 'logs',
            PROJECT_ROOT / 'reports'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Dossiers créés dans {self.output_base}")
    
    def _initialize_collectors(self) -> Dict[str, Any]:
        """Initialise les collecteurs de données"""
        collectors = {}
        
        try:
            collectors['who'] = WHOCollector(self.config.get('who_config', {}))
            logger.info("✅ Collecteur WHO initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation WHO: {e}")
            self.pipeline_stats['errors'].append(f"WHO collector init: {e}")
        
        try:
            collectors['cdc'] = CDCCollector(self.config.get('cdc_config', {}))
            logger.info("✅ Collecteur CDC initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation CDC: {e}")
            self.pipeline_stats['errors'].append(f"CDC collector init: {e}")
        
        return collectors
    
    async def run_full_pipeline(self, target_documents: int = None) -> Dict[str, Any]:
        """Exécute le pipeline complet de collecte et préparation"""
        logger.info("🚀 Démarrage du pipeline de collecte et préparation des données médicales")
        logger.info(f"🎯 Objectif: {target_documents or TARGET_DOCUMENTS} documents")
        
        self.pipeline_stats['start_time'] = datetime.now()
        
        try:
            # Étape 1: Collecte des données
            logger.info("\n" + "="*60)
            logger.info("📥 ÉTAPE 1: COLLECTE DES DONNÉES")
            logger.info("="*60)
            
            raw_documents = await self._collect_data(target_documents or TARGET_DOCUMENTS)
            self.pipeline_stats['documents_collected'] = len(raw_documents)
            
            if not raw_documents:
                raise Exception("Aucun document collecté")
            
            # Étape 2: Traitement des données
            logger.info("\n" + "="*60)
            logger.info("⚙️ ÉTAPE 2: TRAITEMENT DES DONNÉES")
            logger.info("="*60)
            
            processed_documents = await self._process_data(raw_documents)
            self.pipeline_stats['documents_processed'] = len(processed_documents)
            
            # Étape 3: Validation médicale
            logger.info("\n" + "="*60)
            logger.info("🔍 ÉTAPE 3: VALIDATION MÉDICALE")
            logger.info("="*60)
            
            validation_results = await self._validate_data(processed_documents)
            valid_documents = [doc for doc, result in zip(processed_documents, validation_results) if result.is_valid]
            self.pipeline_stats['documents_validated'] = len(valid_documents)
            
            # Étape 4: Traduction
            logger.info("\n" + "="*60)
            logger.info("🌍 ÉTAPE 4: TRADUCTION")
            logger.info("="*60)
            
            translation_results = await self._translate_data(valid_documents)
            self.pipeline_stats['documents_translated'] = sum(len(results) for results in translation_results.values())
            
            # Étape 5: Organisation hiérarchique
            logger.info("\n" + "="*60)
            logger.info("🗂️ ÉTAPE 5: ORGANISATION HIÉRARCHIQUE")
            logger.info("="*60)
            
            knowledge_hierarchy = await self._organize_data(valid_documents)
            self.pipeline_stats['documents_organized'] = knowledge_hierarchy.total_documents
            
            # Étape 6: Génération des rapports
            logger.info("\n" + "="*60)
            logger.info("📊 ÉTAPE 6: GÉNÉRATION DES RAPPORTS")
            logger.info("="*60)
            
            final_report = await self._generate_reports({
                'raw_documents': raw_documents,
                'processed_documents': processed_documents,
                'validation_results': validation_results,
                'translation_results': translation_results,
                'knowledge_hierarchy': knowledge_hierarchy
            })
            
            # Finalisation
            self.pipeline_stats['end_time'] = datetime.now()
            self.pipeline_stats['total_duration'] = (
                self.pipeline_stats['end_time'] - self.pipeline_stats['start_time']
            ).total_seconds()
            
            self.pipeline_stats['success_rate'] = (
                self.pipeline_stats['documents_organized'] / 
                max(self.pipeline_stats['documents_collected'], 1) * 100
            )
            
            logger.info("\n" + "="*60)
            logger.info("✅ PIPELINE TERMINÉ AVEC SUCCÈS")
            logger.info("="*60)
            logger.info(f"📊 Documents collectés: {self.pipeline_stats['documents_collected']}")
            logger.info(f"⚙️ Documents traités: {self.pipeline_stats['documents_processed']}")
            logger.info(f"✅ Documents validés: {self.pipeline_stats['documents_validated']}")
            logger.info(f"🌍 Documents traduits: {self.pipeline_stats['documents_translated']}")
            logger.info(f"🗂️ Documents organisés: {self.pipeline_stats['documents_organized']}")
            logger.info(f"⏱️ Durée totale: {self.pipeline_stats['total_duration']:.1f}s")
            logger.info(f"📈 Taux de succès: {self.pipeline_stats['success_rate']:.1f}%")
            
            return {
                'success': True,
                'statistics': self.pipeline_stats,
                'final_report': final_report,
                'output_paths': {
                    'raw': str(self.raw_data_path),
                    'processed': str(self.processed_data_path),
                    'validated': str(self.validated_data_path),
                    'translated': str(self.translated_data_path),
                    'organized': str(self.organized_data_path)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le pipeline: {e}")
            self.pipeline_stats['errors'].append(f"Pipeline error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'statistics': self.pipeline_stats
            }
    
    async def _collect_data(self, target_documents: int) -> List[Dict[str, Any]]:
        """Collecte les données depuis les sources configurées"""
        logger.info(f"📥 Collecte de {target_documents} documents depuis {len(self.collectors)} sources...")
        
        all_documents = []
        documents_per_source = target_documents // len(self.collectors)
        
        # Collecte parallèle depuis toutes les sources
        collection_tasks = []
        
        for source_name, collector in self.collectors.items():
            if hasattr(collector, 'collect_documents'):
                task = self._collect_from_source(source_name, collector, documents_per_source)
                collection_tasks.append(task)
        
        # Attendre toutes les collectes
        collection_results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # Traiter les résultats
        for source_name, result in zip(self.collectors.keys(), collection_results):
            if isinstance(result, Exception):
                logger.error(f"❌ Erreur collecte {source_name}: {result}")
                self.pipeline_stats['errors'].append(f"Collection {source_name}: {result}")
            else:
                all_documents.extend(result)
                logger.info(f"✅ {source_name}: {len(result)} documents collectés")
        
        # Sauvegarder les données brutes
        await self._save_raw_data(all_documents)
        
        logger.info(f"📥 Collecte terminée: {len(all_documents)} documents au total")
        return all_documents
    
    async def _collect_from_source(self, source_name: str, collector: Any, target_count: int) -> List[Dict[str, Any]]:
        """Collecte depuis une source spécifique"""
        try:
            logger.info(f"🔄 Collecte depuis {source_name}...")
            
            if source_name == 'who':
                documents = await asyncio.to_thread(
                    collector.collect_priority_documents, 
                    target_count
                )
            elif source_name == 'cdc':
                documents = await asyncio.to_thread(
                    collector.collect_health_information,
                    target_count
                )
            else:
                documents = await asyncio.to_thread(
                    collector.collect_documents,
                    target_count
                )
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte {source_name}: {e}")
            return []
    
    async def _save_raw_data(self, documents: List[Dict[str, Any]]):
        """Sauvegarde les données brutes"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Sauvegarder par source
            sources = {}
            for doc in documents:
                source = doc.get('source', 'unknown')
                if source not in sources:
                    sources[source] = []
                sources[source].append(doc)
            
            for source, source_docs in sources.items():
                filename = f"raw_data_{source}_{timestamp}.json"
                filepath = self.raw_data_path / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(source_docs, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder le fichier consolidé
            consolidated_file = self.raw_data_path / f"all_raw_data_{timestamp}.json"
            with open(consolidated_file, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Données brutes sauvegardées: {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde données brutes: {e}")
    
    async def _process_data(self, raw_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traite les données collectées"""
        logger.info(f"⚙️ Traitement de {len(raw_documents)} documents...")
        
        try:
            # Traitement en parallèle par lots
            batch_size = 10
            processed_documents = []
            
            for i in range(0, len(raw_documents), batch_size):
                batch = raw_documents[i:i + batch_size]
                logger.info(f"🔄 Traitement du lot {i//batch_size + 1}/{(len(raw_documents)-1)//batch_size + 1}...")
                
                # Traiter le lot
                batch_results = await asyncio.to_thread(
                    self.processor.process_batch,
                    batch
                )
                
                processed_documents.extend(batch_results)
                
                # Pause entre les lots
                await asyncio.sleep(0.1)
            
            # Sauvegarder les données traitées
            await self._save_processed_data(processed_documents)
            
            logger.info(f"⚙️ Traitement terminé: {len(processed_documents)} documents traités")
            return [doc.__dict__ if hasattr(doc, '__dict__') else doc for doc in processed_documents]
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement: {e}")
            self.pipeline_stats['errors'].append(f"Processing error: {e}")
            return []
    
    async def _save_processed_data(self, processed_documents: List[Any]):
        """Sauvegarde les données traitées"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Convertir en dictionnaires si nécessaire
            docs_data = []
            for doc in processed_documents:
                if hasattr(doc, '__dict__'):
                    doc_dict = doc.__dict__.copy()
                    # Convertir les dates en ISO format
                    if 'processing_date' in doc_dict:
                        doc_dict['processing_date'] = doc_dict['processing_date'].isoformat()
                    docs_data.append(doc_dict)
                else:
                    docs_data.append(doc)
            
            filepath = self.processed_data_path / f"processed_data_{timestamp}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(docs_data, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les statistiques de traitement
            stats = self.processor.get_processing_statistics()
            stats_file = self.processed_data_path / f"processing_stats_{timestamp}.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Données traitées sauvegardées: {len(processed_documents)} documents")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde données traitées: {e}")
    
    async def _validate_data(self, processed_documents: List[Dict[str, Any]]) -> List[Any]:
        """Valide les données traitées"""
        logger.info(f"🔍 Validation de {len(processed_documents)} documents...")
        
        try:
            # Validation en parallèle par lots
            batch_size = 5
            validation_results = []
            
            for i in range(0, len(processed_documents), batch_size):
                batch = processed_documents[i:i + batch_size]
                logger.info(f"🔄 Validation du lot {i//batch_size + 1}/{(len(processed_documents)-1)//batch_size + 1}...")
                
                # Valider le lot
                batch_results = await asyncio.to_thread(
                    self.validator.validate_batch,
                    batch
                )
                
                validation_results.extend(batch_results)
                
                # Pause entre les lots
                await asyncio.sleep(0.1)
            
            # Sauvegarder les résultats de validation
            await self._save_validation_results(validation_results)
            
            valid_count = len([r for r in validation_results if r.is_valid])
            logger.info(f"🔍 Validation terminée: {valid_count}/{len(validation_results)} documents valides")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Erreur validation: {e}")
            self.pipeline_stats['errors'].append(f"Validation error: {e}")
            return []
    
    async def _save_validation_results(self, validation_results: List[Any]):
        """Sauvegarde les résultats de validation"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.validated_data_path / timestamp
            
            await asyncio.to_thread(
                self.validator.save_validation_results,
                validation_results,
                output_path
            )
            
            logger.info(f"💾 Résultats de validation sauvegardés")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde validation: {e}")
    
    async def _translate_data(self, valid_documents: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """Traduit les documents validés"""
        target_languages = self.config.get('target_languages', ['fr', 'en', 'ff', 'ewo'])
        logger.info(f"🌍 Traduction de {len(valid_documents)} documents vers {len(target_languages)} langues...")
        
        try:
            # Traduction en parallèle
            translation_results = await asyncio.to_thread(
                self.translator.translate_batch,
                valid_documents,
                target_languages
            )
            
            # Sauvegarder les traductions
            await self._save_translation_results(translation_results)
            
            # Créer des fiches simplifiées
            await self._create_simplified_sheets(valid_documents, target_languages)
            
            total_translations = sum(len(results) for results in translation_results.values())
            logger.info(f"🌍 Traduction terminée: {total_translations} documents traduits")
            
            return translation_results
            
        except Exception as e:
            logger.error(f"❌ Erreur traduction: {e}")
            self.pipeline_stats['errors'].append(f"Translation error: {e}")
            return {}
    
    async def _save_translation_results(self, translation_results: Dict[str, List[Any]]):
        """Sauvegarde les résultats de traduction"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.translated_data_path / timestamp
            
            await asyncio.to_thread(
                self.translator.save_translations,
                translation_results,
                output_path
            )
            
            logger.info(f"💾 Traductions sauvegardées")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde traductions: {e}")
    
    async def _create_simplified_sheets(self, documents: List[Dict[str, Any]], target_languages: List[str]):
        """Crée des fiches explicatives simplifiées"""
        logger.info(f"📋 Création de fiches simplifiées...")
        
        try:
            for language in target_languages:
                logger.info(f"📝 Fiches en {language}...")
                
                simplified_sheets = await asyncio.to_thread(
                    self.translator.create_simplified_sheets,
                    documents[:20],  # Limiter à 20 documents pour les fiches
                    language
                )
                
                # Sauvegarder les fiches
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sheets_path = self.translated_data_path / f"simplified_sheets_{language}_{timestamp}.json"
                
                with open(sheets_path, 'w', encoding='utf-8') as f:
                    json.dump(simplified_sheets, f, ensure_ascii=False, indent=2)
                
                logger.info(f"📋 {len(simplified_sheets)} fiches créées en {language}")
            
        except Exception as e:
            logger.error(f"❌ Erreur création fiches: {e}")
    
    async def _organize_data(self, valid_documents: List[Dict[str, Any]]) -> Any:
        """Organise les données en hiérarchie thématique"""
        logger.info(f"🗂️ Organisation de {len(valid_documents)} documents en hiérarchie...")
        
        try:
            # Organisation hiérarchique
            knowledge_hierarchy = await asyncio.to_thread(
                self.organizer.organize_documents,
                valid_documents
            )
            
            # Sauvegarder la hiérarchie
            await self._save_knowledge_hierarchy(knowledge_hierarchy)
            
            logger.info(f"🗂️ Organisation terminée: {knowledge_hierarchy.total_nodes} nœuds créés")
            
            return knowledge_hierarchy
            
        except Exception as e:
            logger.error(f"❌ Erreur organisation: {e}")
            self.pipeline_stats['errors'].append(f"Organization error: {e}")
            return None
    
    async def _save_knowledge_hierarchy(self, hierarchy: Any):
        """Sauvegarde la hiérarchie des connaissances"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.organized_data_path / timestamp
            
            # Sauvegarder en différents formats
            await asyncio.to_thread(
                self.organizer.export_hierarchy,
                hierarchy,
                output_path,
                'json'
            )
            
            await asyncio.to_thread(
                self.organizer.export_hierarchy,
                hierarchy,
                output_path,
                'tree'
            )
            
            await asyncio.to_thread(
                self.organizer.export_hierarchy,
                hierarchy,
                output_path,
                'csv'
            )
            
            logger.info(f"💾 Hiérarchie sauvegardée")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde hiérarchie: {e}")
    
    async def _generate_reports(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Génère les rapports finaux"""
        logger.info("📊 Génération des rapports finaux...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_path = PROJECT_ROOT / 'reports' / timestamp
            reports_path.mkdir(parents=True, exist_ok=True)
            
            # Rapport de synthèse
            summary_report = self._create_summary_report(pipeline_data)
            
            # Rapport détaillé
            detailed_report = self._create_detailed_report(pipeline_data)
            
            # Rapport de qualité
            quality_report = self._create_quality_report(pipeline_data)
            
            # Sauvegarder les rapports
            reports = {
                'summary': summary_report,
                'detailed': detailed_report,
                'quality': quality_report
            }
            
            for report_name, report_data in reports.items():
                report_file = reports_path / f"{report_name}_report_{timestamp}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # Créer un rapport HTML lisible
            await self._create_html_report(reports, reports_path, timestamp)
            
            logger.info(f"📊 Rapports générés dans {reports_path}")
            
            return {
                'reports_path': str(reports_path),
                'summary': summary_report,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur génération rapports: {e}")
            return {}
    
    def _create_summary_report(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée le rapport de synthèse"""
        return {
            'pipeline_info': {
                'version': self.orchestrator_version,
                'execution_date': self.pipeline_stats['start_time'].isoformat(),
                'duration_seconds': self.pipeline_stats['total_duration'],
                'success_rate': self.pipeline_stats['success_rate']
            },
            'collection_summary': {
                'total_documents_collected': self.pipeline_stats['documents_collected'],
                'sources_used': list(self.collectors.keys()),
                'collection_success': self.pipeline_stats['documents_collected'] > 0
            },
            'processing_summary': {
                'documents_processed': self.pipeline_stats['documents_processed'],
                'processing_success_rate': (
                    self.pipeline_stats['documents_processed'] / 
                    max(self.pipeline_stats['documents_collected'], 1) * 100
                )
            },
            'validation_summary': {
                'documents_validated': self.pipeline_stats['documents_validated'],
                'validation_success_rate': (
                    self.pipeline_stats['documents_validated'] / 
                    max(self.pipeline_stats['documents_processed'], 1) * 100
                )
            },
            'translation_summary': {
                'documents_translated': self.pipeline_stats['documents_translated'],
                'languages_supported': len(self.config.get('target_languages', []))
            },
            'organization_summary': {
                'documents_organized': self.pipeline_stats['documents_organized'],
                'hierarchy_created': pipeline_data.get('knowledge_hierarchy') is not None
            },
            'errors_and_warnings': {
                'total_errors': len(self.pipeline_stats['errors']),
                'total_warnings': len(self.pipeline_stats['warnings']),
                'critical_issues': [e for e in self.pipeline_stats['errors'] if 'critical' in e.lower()]
            }
        }
    
    def _create_detailed_report(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée le rapport détaillé"""
        return {
            'pipeline_statistics': self.pipeline_stats,
            'component_statistics': {
                'processor': self.processor.get_processing_statistics(),
                'validator': self.validator.get_validation_statistics(),
                'translator': self.translator.get_translation_statistics(),
                'organizer': self.organizer.get_organization_statistics()
            },
            'data_quality_metrics': self._calculate_quality_metrics(pipeline_data),
            'performance_metrics': self._calculate_performance_metrics(),
            'recommendations': self._generate_recommendations(pipeline_data)
        }
    
    def _create_quality_report(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée le rapport de qualité"""
        validation_results = pipeline_data.get('validation_results', [])
        
        quality_scores = [r.confidence_score for r in validation_results if hasattr(r, 'confidence_score')]
        medical_accuracy_scores = [r.medical_accuracy_score for r in validation_results if hasattr(r, 'medical_accuracy_score')]
        
        return {
            'overall_quality': {
                'average_confidence': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                'average_medical_accuracy': sum(medical_accuracy_scores) / len(medical_accuracy_scores) if medical_accuracy_scores else 0,
                'documents_above_threshold': len([s for s in quality_scores if s > 0.7]),
                'quality_distribution': self._calculate_quality_distribution(quality_scores)
            },
            'validation_details': {
                'total_validated': len(validation_results),
                'valid_documents': len([r for r in validation_results if hasattr(r, 'is_valid') and r.is_valid]),
                'common_issues': self._extract_common_issues(validation_results)
            },
            'content_analysis': {
                'average_document_length': self._calculate_average_length(pipeline_data.get('processed_documents', [])),
                'language_distribution': self._calculate_language_distribution(pipeline_data.get('processed_documents', [])),
                'category_distribution': self._calculate_category_distribution(pipeline_data.get('processed_documents', []))
            }
        }
    
    def _calculate_quality_metrics(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les métriques de qualité"""
        return {
            'data_completeness': self.pipeline_stats['documents_organized'] / max(self.pipeline_stats['documents_collected'], 1),
            'processing_efficiency': self.pipeline_stats['documents_processed'] / max(self.pipeline_stats['documents_collected'], 1),
            'validation_accuracy': self.pipeline_stats['documents_validated'] / max(self.pipeline_stats['documents_processed'], 1),
            'translation_coverage': self.pipeline_stats['documents_translated'] / max(self.pipeline_stats['documents_validated'], 1)
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de performance"""
        total_docs = max(self.pipeline_stats['documents_collected'], 1)
        total_time = max(self.pipeline_stats['total_duration'], 1)
        
        return {
            'documents_per_second': total_docs / total_time,
            'average_processing_time': total_time / total_docs,
            'memory_efficiency': 'N/A',  # Pourrait être implémenté
            'error_rate': len(self.pipeline_stats['errors']) / total_docs
        }
    
    def _generate_recommendations(self, pipeline_data: Dict[str, Any]) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Recommandations basées sur les statistiques
        if self.pipeline_stats['success_rate'] < 80:
            recommendations.append("Améliorer la robustesse du pipeline (taux de succès < 80%)")
        
        if len(self.pipeline_stats['errors']) > 5:
            recommendations.append("Investiguer et corriger les erreurs récurrentes")
        
        if self.pipeline_stats['documents_validated'] / max(self.pipeline_stats['documents_processed'], 1) < 0.7:
            recommendations.append("Améliorer la qualité des sources ou les critères de validation")
        
        return recommendations
    
    def _calculate_quality_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calcule la distribution des scores de qualité"""
        if not scores:
            return {}
        
        distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        for score in scores:
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['good'] += 1
            elif score >= 0.5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def _extract_common_issues(self, validation_results: List[Any]) -> List[str]:
        """Extrait les problèmes communs de validation"""
        issues = []
        for result in validation_results:
            if hasattr(result, 'flagged_issues'):
                issues.extend([issue.get('type', 'unknown') for issue in result.flagged_issues])
        
        from collections import Counter
        common_issues = Counter(issues).most_common(5)
        return [f"{issue}: {count}" for issue, count in common_issues]
    
    def _calculate_average_length(self, documents: List[Dict[str, Any]]) -> float:
        """Calcule la longueur moyenne des documents"""
        if not documents:
            return 0
        
        lengths = [len(doc.get('cleaned_content', '')) for doc in documents]
        return sum(lengths) / len(lengths)
    
    def _calculate_language_distribution(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calcule la distribution des langues"""
        from collections import Counter
        languages = [doc.get('language', 'unknown') for doc in documents]
        return dict(Counter(languages))
    
    def _calculate_category_distribution(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calcule la distribution des catégories"""
        from collections import Counter
        categories = [doc.get('category', 'unknown') for doc in documents]
        return dict(Counter(categories))
    
    async def _create_html_report(self, reports: Dict[str, Any], output_path: Path, timestamp: str):
        """Crée un rapport HTML lisible"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Collecte et Préparation des Données Médicales</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 5px; min-width: 150px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; }}
        .progress-bar {{ width: 100%; height: 20px; background-color: #ecf0f1; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background-color: #2980b9; transition: width 0.3s ease; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Rapport de Collecte et Préparation des Données Médicales</h1>
        <p><strong>Date d'exécution:</strong> {timestamp}</p>
        <p><strong>Version:</strong> {self.orchestrator_version}</p>
        
        <h2>📈 Métriques Principales</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value success">{self.pipeline_stats['documents_collected']}</div>
                <div class="metric-label">Documents Collectés</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.pipeline_stats['documents_processed']}</div>
                <div class="metric-label">Documents Traités</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.pipeline_stats['documents_validated']}</div>
                <div class="metric-label">Documents Validés</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.pipeline_stats['documents_translated']}</div>
                <div class="metric-label">Documents Traduits</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.pipeline_stats['success_rate']:.1f}%</div>
                <div class="metric-label">Taux de Succès</div>
            </div>
        </div>
        
        <h2>⏱️ Performance</h2>
        <p><strong>Durée totale:</strong> {self.pipeline_stats['total_duration']:.1f} secondes</p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {min(self.pipeline_stats['success_rate'], 100)}%"></div>
        </div>
        
        <h2>🔍 Détails par Étape</h2>
        <table>
            <tr><th>Étape</th><th>Documents</th><th>Taux de Succès</th><th>Statut</th></tr>
            <tr>
                <td>Collecte</td>
                <td>{self.pipeline_stats['documents_collected']}</td>
                <td>100%</td>
                <td class="success">✅ Terminé</td>
            </tr>
            <tr>
                <td>Traitement</td>
                <td>{self.pipeline_stats['documents_processed']}</td>
                <td>{(self.pipeline_stats['documents_processed'] / max(self.pipeline_stats['documents_collected'], 1) * 100):.1f}%</td>
                <td class="success">✅ Terminé</td>
            </tr>
            <tr>
                <td>Validation</td>
                <td>{self.pipeline_stats['documents_validated']}</td>
                <td>{(self.pipeline_stats['documents_validated'] / max(self.pipeline_stats['documents_processed'], 1) * 100):.1f}%</td>
                <td class="success">✅ Terminé</td>
            </tr>
            <tr>
                <td>Traduction</td>
                <td>{self.pipeline_stats['documents_translated']}</td>
                <td>-</td>
                <td class="success">✅ Terminé</td>
            </tr>
            <tr>
                <td>Organisation</td>
                <td>{self.pipeline_stats['documents_organized']}</td>
                <td>-</td>
                <td class="success">✅ Terminé</td>
            </tr>
        </table>
        
        <h2>⚠️ Erreurs et Avertissements</h2>
        <p><strong>Erreurs:</strong> {len(self.pipeline_stats['errors'])}</p>
        <p><strong>Avertissements:</strong> {len(self.pipeline_stats['warnings'])}</p>
        
        <h2>📁 Fichiers de Sortie</h2>
        <ul>
            <li><strong>Données brutes:</strong> {self.raw_data_path}</li>
            <li><strong>Données traitées:</strong> {self.processed_data_path}</li>
            <li><strong>Données validées:</strong> {self.validated_data_path}</li>
            <li><strong>Traductions:</strong> {self.translated_data_path}</li>
            <li><strong>Hiérarchie organisée:</strong> {self.organized_data_path}</li>
        </ul>
        
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; text-align: center;">
            <p>Rapport généré automatiquement par le système de collecte et préparation des données médicales</p>
            <p>Hôpital Général de Douala - Module 2: Collecte et Préparation des Données</p>
        </footer>
    </div>
</body>
</html>
            """
            
            html_file = output_path / f"rapport_complet_{timestamp}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"📄 Rapport HTML créé: {html_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur création rapport HTML: {e}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Orchestrateur de collecte et préparation des données médicales')
    parser.add_argument('--target-docs', type=int, default=TARGET_DOCUMENTS, help='Nombre de documents à collecter')
    parser.add_argument('--config', type=str, help='Fichier de configuration personnalisé')
    parser.add_argument('--output', type=str, default=str(PROJECT_ROOT / 'data'), help='Dossier de sortie')
    parser.add_argument('--languages', nargs='+', default=['fr', 'en', 'ff', 'ewo'], help='Langues cibles pour la traduction')
    
    args = parser.parse_args()
    
    # Configuration
    config = {
        'output_path': args.output,
        'target_languages': args.languages,
        'processing': {
            'min_content_length': 300,
            'max_content_length': 50000,
            'target_summary_length': 200
        },
        'validation': {
            'min_confidence_threshold': 0.7,
            'min_source_credibility': 0.6
        },
        'translation': {},
        'organization': {
            'max_hierarchy_depth': 4,
            'min_documents_per_node': 3,
            'max_documents_per_node': 20
        }
    }
    
    # Charger configuration personnalisée si fournie
    if args.config and Path(args.config).exists():
        with open(args.config, 'r', encoding='utf-8') as f:
            custom_config = json.load(f)
            config.update(custom_config)
    
    # Créer et exécuter l'orchestrateur
    orchestrator = DataCollectionOrchestrator(config)
    
    logger.info("🚀 Démarrage de l'orchestrateur de collecte et préparation des données médicales")
    logger.info(f"🎯 Objectif: {args.target_docs} documents")
    logger.info(f"🌍 Langues cibles: {', '.join(args.languages)}")
    logger.info(f"📁 Sortie: {args.output}")
    
    # Exécuter le pipeline
    result = asyncio.run(orchestrator.run_full_pipeline(args.target_docs))
    
    if result['success']:
        logger.info("\n" + "="*60)
        logger.info("🎉 PIPELINE EXÉCUTÉ AVEC SUCCÈS!")
        logger.info("="*60)
        logger.info(f"📊 Consultez le rapport complet dans: {result.get('final_report', {}).get('reports_path', 'N/A')}")
        logger.info(f"📁 Données disponibles dans: {args.output}")
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ ÉCHEC DU PIPELINE")
        logger.error("="*60)
        logger.error(f"Erreur: {result.get('error', 'Erreur inconnue')}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())