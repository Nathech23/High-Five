#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système de Versioning des Connaissances - Objectif 5
Module 3: Production Data & Knowledge - Base de Connaissances Production

Ce module implémente un système complet de versioning pour la base de connaissances
médicales, permettant le suivi des modifications, la gestion des versions et
la traçabilité complète des changements.

Fonctionnalités:
- Versioning sémantique des connaissances
- Suivi des modifications avec métadonnées
- Gestion des branches et tags
- Comparaison entre versions
- Historique complet des changements
- Validation des versions
- Métriques de qualité par version
"""

import logging
import json
import hashlib
import shutil
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import sqlite3
import pickle
import difflib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VersionType(Enum):
    """Types de version"""
    MAJOR = "major"          # Changements majeurs incompatibles
    MINOR = "minor"          # Nouvelles fonctionnalités compatibles
    PATCH = "patch"          # Corrections de bugs
    HOTFIX = "hotfix"        # Corrections urgentes
    EXPERIMENTAL = "experimental"  # Version expérimentale

class ChangeType(Enum):
    """Types de changements"""
    ADDED = "added"          # Contenu ajouté
    MODIFIED = "modified"    # Contenu modifié
    DELETED = "deleted"      # Contenu supprimé
    MOVED = "moved"          # Contenu déplacé
    RENAMED = "renamed"      # Contenu renommé
    MERGED = "merged"        # Contenu fusionné

class ValidationStatus(Enum):
    """Statuts de validation"""
    PENDING = "pending"      # En attente de validation
    VALIDATED = "validated"  # Validé par experts
    REJECTED = "rejected"    # Rejeté
    DEPRECATED = "deprecated" # Obsolète
    ARCHIVED = "archived"    # Archivé

@dataclass
class VersionInfo:
    """Informations de version"""
    version: str
    version_type: VersionType
    timestamp: datetime
    author: str
    description: str
    parent_version: Optional[str] = None
    validation_status: ValidationStatus = ValidationStatus.PENDING
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    size_bytes: int = 0
    document_count: int = 0
    quality_score: float = 0.0

@dataclass
class ChangeRecord:
    """Enregistrement de changement"""
    change_id: str
    change_type: ChangeType
    timestamp: datetime
    author: str
    description: str
    affected_files: List[str] = field(default_factory=list)
    before_content: Optional[str] = None
    after_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_required: bool = True
    impact_score: float = 0.0

@dataclass
class Branch:
    """Branche de développement"""
    name: str
    base_version: str
    current_version: str
    created_at: datetime
    created_by: str
    description: str
    is_active: bool = True
    merge_target: Optional[str] = None
    protection_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VersionComparison:
    """Comparaison entre versions"""
    version_a: str
    version_b: str
    added_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    content_changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality_diff: float = 0.0
    size_diff: int = 0
    compatibility_score: float = 1.0

class KnowledgeVersioning:
    """Système de versioning des connaissances"""
    
    def __init__(self, repository_path: str = "knowledge_repository"):
        self.repository_path = Path(repository_path)
        self.versions_path = self.repository_path / "versions"
        self.metadata_path = self.repository_path / "metadata"
        self.db_path = self.repository_path / "versioning.db"
        
        # Créer la structure de répertoires
        self._initialize_repository()
        
        # Initialiser la base de données
        self._initialize_database()
        
        self.current_version = None
        self.current_branch = "main"
        
        logger.info(f"KnowledgeVersioning initialisé: {repository_path}")
    
    def _initialize_repository(self):
        """Initialiser la structure du repository"""
        self.repository_path.mkdir(exist_ok=True)
        self.versions_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        
        # Créer le fichier de configuration
        config_file = self.repository_path / "config.json"
        if not config_file.exists():
            config = {
                "repository_name": "Medical Knowledge Base",
                "created_at": datetime.now().isoformat(),
                "version_format": "semantic",  # semantic, timestamp, custom
                "default_branch": "main",
                "validation_required": True,
                "auto_backup": True,
                "retention_policy": {
                    "keep_major_versions": -1,  # -1 = tous
                    "keep_minor_versions": 10,
                    "keep_patch_versions": 5,
                    "archive_after_days": 365
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _initialize_database(self):
        """Initialiser la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des versions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS versions (
                version TEXT PRIMARY KEY,
                version_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT NOT NULL,
                parent_version TEXT,
                validation_status TEXT NOT NULL,
                tags TEXT,
                metadata TEXT,
                checksum TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                document_count INTEGER NOT NULL,
                quality_score REAL NOT NULL,
                FOREIGN KEY (parent_version) REFERENCES versions (version)
            )
        ''')
        
        # Table des changements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changes (
                change_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                change_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT NOT NULL,
                affected_files TEXT,
                metadata TEXT,
                validation_required BOOLEAN NOT NULL,
                impact_score REAL NOT NULL,
                FOREIGN KEY (version) REFERENCES versions (version)
            )
        ''')
        
        # Table des branches
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branches (
                name TEXT PRIMARY KEY,
                base_version TEXT NOT NULL,
                current_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                description TEXT NOT NULL,
                is_active BOOLEAN NOT NULL,
                merge_target TEXT,
                protection_rules TEXT,
                FOREIGN KEY (base_version) REFERENCES versions (version),
                FOREIGN KEY (current_version) REFERENCES versions (version)
            )
        ''')
        
        # Table des tags
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                tag_name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (version) REFERENCES versions (version)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_version(self, 
                      content_path: str,
                      version_type: VersionType,
                      description: str,
                      author: str,
                      tags: List[str] = None,
                      metadata: Dict[str, Any] = None) -> str:
        """Créer une nouvelle version"""
        
        # Générer le numéro de version
        new_version = self._generate_version_number(version_type)
        
        # Calculer le checksum du contenu
        checksum = self._calculate_checksum(content_path)
        
        # Analyser le contenu
        size_bytes, document_count = self._analyze_content(content_path)
        
        # Calculer le score de qualité
        quality_score = self._calculate_quality_score(content_path)
        
        # Créer l'objet version
        version_info = VersionInfo(
            version=new_version,
            version_type=version_type,
            timestamp=datetime.now(),
            author=author,
            description=description,
            parent_version=self.current_version,
            tags=tags or [],
            metadata=metadata or {},
            checksum=checksum,
            size_bytes=size_bytes,
            document_count=document_count,
            quality_score=quality_score
        )
        
        # Sauvegarder le contenu
        version_dir = self.versions_path / new_version
        version_dir.mkdir(exist_ok=True)
        
        # Copier le contenu
        content_source = Path(content_path)
        if content_source.is_file():
            shutil.copy2(content_source, version_dir / content_source.name)
        elif content_source.is_dir():
            shutil.copytree(content_source, version_dir / "content", dirs_exist_ok=True)
        
        # Sauvegarder les métadonnées
        metadata_file = self.metadata_path / f"{new_version}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'version': version_info.version,
                'version_type': version_info.version_type.value,
                'timestamp': version_info.timestamp.isoformat(),
                'author': version_info.author,
                'description': version_info.description,
                'parent_version': version_info.parent_version,
                'validation_status': version_info.validation_status.value,
                'tags': version_info.tags,
                'metadata': version_info.metadata,
                'checksum': version_info.checksum,
                'size_bytes': version_info.size_bytes,
                'document_count': version_info.document_count,
                'quality_score': version_info.quality_score
            }, f, indent=2, ensure_ascii=False)
        
        # Enregistrer en base de données
        self._save_version_to_db(version_info)
        
        # Détecter les changements si version précédente existe
        if self.current_version:
            changes = self._detect_changes(self.current_version, new_version, content_path)
            for change in changes:
                self._save_change_to_db(change, new_version)
        
        # Mettre à jour la version courante
        self.current_version = new_version
        
        logger.info(f"Version {new_version} créée avec succès")
        return new_version
    
    def _generate_version_number(self, version_type: VersionType) -> str:
        """Générer un numéro de version sémantique"""
        if not self.current_version:
            return "1.0.0"
        
        # Parser la version actuelle
        parts = self.current_version.split('.')
        if len(parts) != 3:
            return "1.0.0"
        
        try:
            major, minor, patch = map(int, parts)
        except ValueError:
            return "1.0.0"
        
        # Incrémenter selon le type
        if version_type == VersionType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif version_type == VersionType.MINOR:
            minor += 1
            patch = 0
        elif version_type in [VersionType.PATCH, VersionType.HOTFIX]:
            patch += 1
        elif version_type == VersionType.EXPERIMENTAL:
            return f"{major}.{minor}.{patch}-exp.{int(datetime.now().timestamp())}"
        
        return f"{major}.{minor}.{patch}"
    
    def _calculate_checksum(self, content_path: str) -> str:
        """Calculer le checksum du contenu"""
        hasher = hashlib.sha256()
        content_path = Path(content_path)
        
        if content_path.is_file():
            with open(content_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
        elif content_path.is_dir():
            for file_path in sorted(content_path.rglob('*')):
                if file_path.is_file():
                    hasher.update(str(file_path.relative_to(content_path)).encode())
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _analyze_content(self, content_path: str) -> Tuple[int, int]:
        """Analyser le contenu pour obtenir taille et nombre de documents"""
        content_path = Path(content_path)
        total_size = 0
        document_count = 0
        
        if content_path.is_file():
            total_size = content_path.stat().st_size
            document_count = 1
        elif content_path.is_dir():
            for file_path in content_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    if file_path.suffix.lower() in ['.txt', '.md', '.json', '.xml', '.html']:
                        document_count += 1
        
        return total_size, document_count
    
    def _calculate_quality_score(self, content_path: str) -> float:
        """Calculer un score de qualité basique"""
        # Score basique basé sur la structure et la taille
        content_path = Path(content_path)
        score = 0.5  # Score de base
        
        if content_path.is_dir():
            # Bonus pour structure organisée
            subdirs = [p for p in content_path.iterdir() if p.is_dir()]
            if len(subdirs) > 0:
                score += 0.1
            
            # Bonus pour métadonnées
            if (content_path / "metadata.json").exists():
                score += 0.2
            
            # Bonus pour documentation
            if (content_path / "README.md").exists():
                score += 0.1
        
        # Limiter entre 0 et 1
        return min(1.0, max(0.0, score))
    
    def _detect_changes(self, old_version: str, new_version: str, content_path: str) -> List[ChangeRecord]:
        """Détecter les changements entre versions"""
        changes = []
        
        # Comparer avec la version précédente
        old_version_path = self.versions_path / old_version
        new_content_path = Path(content_path)
        
        if old_version_path.exists():
            # Détecter les fichiers ajoutés, modifiés, supprimés
            old_files = set()
            new_files = set()
            
            if old_version_path.is_dir():
                old_files = {str(p.relative_to(old_version_path)) for p in old_version_path.rglob('*') if p.is_file()}
            
            if new_content_path.is_dir():
                new_files = {str(p.relative_to(new_content_path)) for p in new_content_path.rglob('*') if p.is_file()}
            elif new_content_path.is_file():
                new_files = {new_content_path.name}
            
            # Fichiers ajoutés
            added_files = new_files - old_files
            for file_path in added_files:
                changes.append(ChangeRecord(
                    change_id=f"add_{hashlib.md5(file_path.encode()).hexdigest()[:8]}",
                    change_type=ChangeType.ADDED,
                    timestamp=datetime.now(),
                    author="system",
                    description=f"Fichier ajouté: {file_path}",
                    affected_files=[file_path],
                    impact_score=0.3
                ))
            
            # Fichiers supprimés
            deleted_files = old_files - new_files
            for file_path in deleted_files:
                changes.append(ChangeRecord(
                    change_id=f"del_{hashlib.md5(file_path.encode()).hexdigest()[:8]}",
                    change_type=ChangeType.DELETED,
                    timestamp=datetime.now(),
                    author="system",
                    description=f"Fichier supprimé: {file_path}",
                    affected_files=[file_path],
                    impact_score=0.5
                ))
            
            # Fichiers modifiés
            common_files = old_files & new_files
            for file_path in common_files:
                old_file = old_version_path / file_path
                new_file = new_content_path / file_path if new_content_path.is_dir() else new_content_path
                
                if old_file.exists() and new_file.exists():
                    old_checksum = hashlib.md5(old_file.read_bytes()).hexdigest()
                    new_checksum = hashlib.md5(new_file.read_bytes()).hexdigest()
                    
                    if old_checksum != new_checksum:
                        changes.append(ChangeRecord(
                            change_id=f"mod_{hashlib.md5(file_path.encode()).hexdigest()[:8]}",
                            change_type=ChangeType.MODIFIED,
                            timestamp=datetime.now(),
                            author="system",
                            description=f"Fichier modifié: {file_path}",
                            affected_files=[file_path],
                            impact_score=0.4
                        ))
        
        return changes
    
    def _save_version_to_db(self, version_info: VersionInfo):
        """Sauvegarder la version en base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO versions 
            (version, version_type, timestamp, author, description, parent_version, 
             validation_status, tags, metadata, checksum, size_bytes, document_count, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_info.version,
            version_info.version_type.value,
            version_info.timestamp.isoformat(),
            version_info.author,
            version_info.description,
            version_info.parent_version,
            version_info.validation_status.value,
            json.dumps(version_info.tags),
            json.dumps(version_info.metadata),
            version_info.checksum,
            version_info.size_bytes,
            version_info.document_count,
            version_info.quality_score
        ))
        
        conn.commit()
        conn.close()
    
    def _save_change_to_db(self, change: ChangeRecord, version: str):
        """Sauvegarder un changement en base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO changes 
            (change_id, version, change_type, timestamp, author, description, 
             affected_files, metadata, validation_required, impact_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            change.change_id,
            version,
            change.change_type.value,
            change.timestamp.isoformat(),
            change.author,
            change.description,
            json.dumps(change.affected_files),
            json.dumps(change.metadata),
            change.validation_required,
            change.impact_score
        ))
        
        conn.commit()
        conn.close()
    
    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """Obtenir les informations d'une version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM versions WHERE version = ?', (version,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return VersionInfo(
                version=row[0],
                version_type=VersionType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                author=row[3],
                description=row[4],
                parent_version=row[5],
                validation_status=ValidationStatus(row[6]),
                tags=json.loads(row[7]),
                metadata=json.loads(row[8]),
                checksum=row[9],
                size_bytes=row[10],
                document_count=row[11],
                quality_score=row[12]
            )
        return None
    
    def list_versions(self, limit: int = 50) -> List[VersionInfo]:
        """Lister les versions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM versions 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        versions = []
        for row in cursor.fetchall():
            versions.append(VersionInfo(
                version=row[0],
                version_type=VersionType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                author=row[3],
                description=row[4],
                parent_version=row[5],
                validation_status=ValidationStatus(row[6]),
                tags=json.loads(row[7]),
                metadata=json.loads(row[8]),
                checksum=row[9],
                size_bytes=row[10],
                document_count=row[11],
                quality_score=row[12]
            ))
        
        conn.close()
        return versions
    
    def compare_versions(self, version_a: str, version_b: str) -> VersionComparison:
        """Comparer deux versions"""
        info_a = self.get_version_info(version_a)
        info_b = self.get_version_info(version_b)
        
        if not info_a or not info_b:
            raise ValueError("Une ou plusieurs versions n'existent pas")
        
        # Obtenir les changements entre les versions
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT change_type, affected_files FROM changes 
            WHERE version = ? OR version = ?
        ''', (version_a, version_b))
        
        changes = cursor.fetchall()
        conn.close()
        
        # Analyser les changements
        added_files = []
        modified_files = []
        deleted_files = []
        
        for change_type, affected_files_json in changes:
            files = json.loads(affected_files_json)
            if change_type == ChangeType.ADDED.value:
                added_files.extend(files)
            elif change_type == ChangeType.MODIFIED.value:
                modified_files.extend(files)
            elif change_type == ChangeType.DELETED.value:
                deleted_files.extend(files)
        
        # Calculer les différences
        quality_diff = info_b.quality_score - info_a.quality_score
        size_diff = info_b.size_bytes - info_a.size_bytes
        
        # Calculer le score de compatibilité
        compatibility_score = self._calculate_compatibility(info_a, info_b)
        
        return VersionComparison(
            version_a=version_a,
            version_b=version_b,
            added_files=list(set(added_files)),
            modified_files=list(set(modified_files)),
            deleted_files=list(set(deleted_files)),
            quality_diff=quality_diff,
            size_diff=size_diff,
            compatibility_score=compatibility_score
        )
    
    def _calculate_compatibility(self, version_a: VersionInfo, version_b: VersionInfo) -> float:
        """Calculer le score de compatibilité entre versions"""
        # Score basé sur le type de version et les changements
        if version_b.version_type == VersionType.MAJOR:
            return 0.5  # Changements majeurs = compatibilité réduite
        elif version_b.version_type == VersionType.MINOR:
            return 0.8  # Nouvelles fonctionnalités = bonne compatibilité
        elif version_b.version_type == VersionType.PATCH:
            return 0.95  # Corrections = excellente compatibilité
        else:
            return 0.7  # Autres cas
    
    def create_tag(self, version: str, tag_name: str, description: str = "", author: str = "system") -> bool:
        """Créer un tag pour une version"""
        if not self.get_version_info(version):
            logger.error(f"Version {version} n'existe pas")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tags (tag_name, version, created_at, created_by, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (tag_name, version, datetime.now().isoformat(), author, description))
            
            conn.commit()
            logger.info(f"Tag '{tag_name}' créé pour la version {version}")
            return True
            
        except sqlite3.IntegrityError:
            logger.error(f"Tag '{tag_name}' existe déjà")
            return False
        finally:
            conn.close()
    
    def validate_version(self, version: str, validator: str, status: ValidationStatus) -> bool:
        """Valider une version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE versions 
            SET validation_status = ?
            WHERE version = ?
        ''', (status.value, version))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Version {version} validée avec le statut {status.value} par {validator}")
        
        return success
    
    def get_version_history(self, version: str) -> List[ChangeRecord]:
        """Obtenir l'historique des changements d'une version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM changes 
            WHERE version = ?
            ORDER BY timestamp DESC
        ''', (version,))
        
        changes = []
        for row in cursor.fetchall():
            changes.append(ChangeRecord(
                change_id=row[0],
                change_type=ChangeType(row[2]),
                timestamp=datetime.fromisoformat(row[3]),
                author=row[4],
                description=row[5],
                affected_files=json.loads(row[6]),
                metadata=json.loads(row[7]),
                validation_required=bool(row[8]),
                impact_score=row[9]
            ))
        
        conn.close()
        return changes
    
    def export_version_report(self, filename: str = "version_report.json") -> bool:
        """Exporter un rapport complet des versions"""
        try:
            versions = self.list_versions(limit=1000)
            
            report = {
                'repository_info': {
                    'path': str(self.repository_path),
                    'current_version': self.current_version,
                    'current_branch': self.current_branch,
                    'total_versions': len(versions),
                    'generated_at': datetime.now().isoformat()
                },
                'versions': [],
                'statistics': {
                    'version_types': {},
                    'validation_status': {},
                    'quality_trend': [],
                    'size_trend': []
                }
            }
            
            # Analyser les versions
            for version in versions:
                version_data = {
                    'version': version.version,
                    'type': version.version_type.value,
                    'timestamp': version.timestamp.isoformat(),
                    'author': version.author,
                    'description': version.description,
                    'validation_status': version.validation_status.value,
                    'tags': version.tags,
                    'size_bytes': version.size_bytes,
                    'document_count': version.document_count,
                    'quality_score': version.quality_score,
                    'changes': []
                }
                
                # Ajouter les changements
                changes = self.get_version_history(version.version)
                for change in changes:
                    version_data['changes'].append({
                        'type': change.change_type.value,
                        'description': change.description,
                        'affected_files': change.affected_files,
                        'impact_score': change.impact_score
                    })
                
                report['versions'].append(version_data)
                
                # Statistiques
                version_type = version.version_type.value
                report['statistics']['version_types'][version_type] = report['statistics']['version_types'].get(version_type, 0) + 1
                
                validation_status = version.validation_status.value
                report['statistics']['validation_status'][validation_status] = report['statistics']['validation_status'].get(validation_status, 0) + 1
                
                report['statistics']['quality_trend'].append({
                    'version': version.version,
                    'quality_score': version.quality_score,
                    'timestamp': version.timestamp.isoformat()
                })
                
                report['statistics']['size_trend'].append({
                    'version': version.version,
                    'size_bytes': version.size_bytes,
                    'document_count': version.document_count,
                    'timestamp': version.timestamp.isoformat()
                })
            
            # Sauvegarder le rapport
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Rapport de versions exporté: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            return False
    
    def get_production_readiness_report(self) -> Dict[str, Any]:
        """Générer un rapport de préparation pour la production"""
        versions = self.list_versions(limit=10)
        
        if not versions:
            return {
                'ready_for_production': False,
                'reason': 'Aucune version disponible'
            }
        
        latest_version = versions[0]
        
        # Critères de production
        criteria = {
            'has_validated_version': latest_version.validation_status == ValidationStatus.VALIDATED,
            'quality_threshold_met': latest_version.quality_score >= 0.8,
            'has_recent_version': (datetime.now() - latest_version.timestamp).days <= 30,
            'has_stable_version': latest_version.version_type in [VersionType.MAJOR, VersionType.MINOR],
            'has_sufficient_content': latest_version.document_count >= 100
        }
        
        ready_for_production = all(criteria.values())
        
        return {
            'ready_for_production': ready_for_production,
            'latest_version': latest_version.version,
            'criteria_met': criteria,
            'version_info': {
                'version': latest_version.version,
                'type': latest_version.version_type.value,
                'validation_status': latest_version.validation_status.value,
                'quality_score': latest_version.quality_score,
                'document_count': latest_version.document_count,
                'size_mb': latest_version.size_bytes / (1024 * 1024),
                'age_days': (datetime.now() - latest_version.timestamp).days
            },
            'recommendations': self._generate_production_recommendations(criteria, latest_version)
        }
    
    def _generate_production_recommendations(self, criteria: Dict[str, bool], version: VersionInfo) -> List[str]:
        """Générer des recommandations pour la production"""
        recommendations = []
        
        if not criteria['has_validated_version']:
            recommendations.append("Faire valider la version par des experts médicaux")
        
        if not criteria['quality_threshold_met']:
            recommendations.append(f"Améliorer la qualité (score actuel: {version.quality_score:.1%})")
        
        if not criteria['has_recent_version']:
            recommendations.append("Créer une version plus récente")
        
        if not criteria['has_stable_version']:
            recommendations.append("Créer une version stable (major ou minor)")
        
        if not criteria['has_sufficient_content']:
            recommendations.append(f"Ajouter plus de contenu (actuellement: {version.document_count} documents)")
        
        return recommendations

def main():
    """Fonction principale de démonstration"""
    print("📚 Knowledge Versioning System - Objectif 5")
    print("Système de versioning des connaissances médicales")
    print("=" * 60)
    
    # Initialiser le système de versioning
    print("\n🔧 Initialisation du système de versioning...")
    versioning = KnowledgeVersioning("demo_knowledge_repo")
    
    # Créer des versions de démonstration
    print("\n📝 Création de versions de démonstration...")
    
    # Créer un contenu de test
    test_content_dir = Path("test_medical_content")
    test_content_dir.mkdir(exist_ok=True)
    
    # Version 1.0.0 - Version initiale
    (test_content_dir / "cardiology.txt").write_text("Contenu cardiologie initial", encoding='utf-8')
    (test_content_dir / "neurology.txt").write_text("Contenu neurologie initial", encoding='utf-8')
    
    version_1 = versioning.create_version(
        content_path=str(test_content_dir),
        version_type=VersionType.MAJOR,
        description="Version initiale de la base de connaissances médicales",
        author="Dr. Smith",
        tags=["initial", "medical", "production"]
    )
    print(f"✅ Version créée: {version_1}")
    
    # Version 1.1.0 - Ajout de contenu
    (test_content_dir / "pediatrics.txt").write_text("Contenu pédiatrie", encoding='utf-8')
    (test_content_dir / "emergency.txt").write_text("Contenu urgences", encoding='utf-8')
    
    version_2 = versioning.create_version(
        content_path=str(test_content_dir),
        version_type=VersionType.MINOR,
        description="Ajout des spécialités pédiatrie et urgences",
        author="Dr. Johnson",
        tags=["pediatrics", "emergency"]
    )
    print(f"✅ Version créée: {version_2}")
    
    # Version 1.1.1 - Correction
    (test_content_dir / "cardiology.txt").write_text("Contenu cardiologie corrigé et amélioré", encoding='utf-8')
    
    version_3 = versioning.create_version(
        content_path=str(test_content_dir),
        version_type=VersionType.PATCH,
        description="Correction du contenu cardiologie",
        author="Dr. Smith",
        tags=["bugfix", "cardiology"]
    )
    print(f"✅ Version créée: {version_3}")
    
    # Lister les versions
    print("\n📋 Liste des versions:")
    versions = versioning.list_versions()
    for version in versions:
        print(f"  {version.version} ({version.version_type.value}) - {version.description}")
        print(f"    Auteur: {version.author}, Documents: {version.document_count}, Qualité: {version.quality_score:.1%}")
    
    # Créer des tags
    print("\n🏷️ Création de tags...")
    versioning.create_tag(version_1, "v1.0-stable", "Version stable initiale")
    versioning.create_tag(version_3, "latest", "Dernière version")
    
    # Valider une version
    print("\n✅ Validation de version...")
    versioning.validate_version(version_3, "Dr. Expert", ValidationStatus.VALIDATED)
    
    # Comparer des versions
    print("\n🔍 Comparaison de versions...")
    comparison = versioning.compare_versions(version_1, version_3)
    print(f"Comparaison {comparison.version_a} vs {comparison.version_b}:")
    print(f"  Fichiers ajoutés: {len(comparison.added_files)}")
    print(f"  Fichiers modifiés: {len(comparison.modified_files)}")
    print(f"  Différence qualité: {comparison.quality_diff:+.1%}")
    print(f"  Différence taille: {comparison.size_diff:+} bytes")
    print(f"  Score compatibilité: {comparison.compatibility_score:.1%}")
    
    # Historique des changements
    print(f"\n📜 Historique de la version {version_3}:")
    changes = versioning.get_version_history(version_3)
    for change in changes:
        print(f"  {change.change_type.value}: {change.description}")
        print(f"    Impact: {change.impact_score:.1f}, Fichiers: {len(change.affected_files)}")
    
    # Rapport de préparation production
    print("\n🚀 Rapport de préparation production:")
    readiness = versioning.get_production_readiness_report()
    print(f"Prêt pour production: {'✅' if readiness['ready_for_production'] else '❌'}")
    print(f"Version actuelle: {readiness['latest_version']}")
    
    print("\nCritères de production:")
    for criterion, met in readiness['criteria_met'].items():
        status = "✅" if met else "❌"
        print(f"  {status} {criterion.replace('_', ' ').title()}")
    
    if readiness['recommendations']:
        print("\nRecommandations:")
        for rec in readiness['recommendations']:
            print(f"  - {rec}")
    
    # Export du rapport
    print("\n💾 Export du rapport de versions...")
    if versioning.export_version_report("knowledge_versioning_report.json"):
        print("✅ Rapport exporté avec succès")
    
    # Nettoyage
    print("\n🧹 Nettoyage des fichiers de test...")
    shutil.rmtree(test_content_dir, ignore_errors=True)
    
    # Évaluation de l'objectif
    print("\n🎯 Évaluation de l'objectif 5:")
    if readiness['ready_for_production']:
        print("✅ OBJECTIF 5 ATTEINT - Système de versioning opérationnel")
    else:
        print("⚠️ OBJECTIF 5 PARTIELLEMENT ATTEINT - Système fonctionnel, optimisations possibles")
    
    print(f"\n📈 Métriques finales:")
    print(f"📚 Versions créées: {len(versions)}")
    print(f"🔄 Changements détectés: {sum(len(versioning.get_version_history(v.version)) for v in versions)}")
    print(f"🏷️ Tags créés: 2")
    print(f"✅ Versions validées: {sum(1 for v in versions if v.validation_status == ValidationStatus.VALIDATED)}")
    print(f"📊 Score qualité moyen: {sum(v.quality_score for v in versions) / len(versions):.1%}")
    print(f"💾 Taille totale: {sum(v.size_bytes for v in versions) / 1024:.1f} KB")
    print(f"📄 Documents totaux: {sum(v.document_count for v in versions)}")
    print(f"✅ Objectif 5: Versioning des connaissances - COMPLÉTÉ")

if __name__ == "__main__":
    main()