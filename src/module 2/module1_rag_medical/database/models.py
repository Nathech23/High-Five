from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()

class MedicalDocument(Base):
    """Table pour stocker les métadonnées des documents médicaux"""
    __tablename__ = "medical_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    document_type = Column(String(100), nullable=False)  # protocol, guideline, research, etc.
    specialty = Column(String(100), nullable=True, index=True)  # cardiologie, neurologie, etc.
    language = Column(String(10), default="fr", index=True)
    source_file = Column(String(500), nullable=True)
    file_hash = Column(String(64), unique=True, index=True)
    
    # Métadonnées temporelles
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_date = Column(DateTime(timezone=True), nullable=True)
    
    # Statut et validation
    is_validated = Column(Boolean, default=False)
    validation_status = Column(String(50), default="pending")  # pending, approved, rejected
    validated_by = Column(String(100), nullable=True)
    
    # Métadonnées médicales
    medical_level = Column(String(50), nullable=True)  # basic, intermediate, advanced
    target_audience = Column(String(100), nullable=True)  # doctors, nurses, patients
    keywords = Column(JSON, nullable=True)  # Liste de mots-clés
    
    # Relations
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    """Table pour stocker les chunks de documents"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("medical_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    overlap_size = Column(Integer, default=0)
    
    # Métadonnées du chunk
    start_position = Column(Integer, nullable=True)
    end_position = Column(Integer, nullable=True)
    section_title = Column(String(200), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    document = relationship("MedicalDocument", back_populates="chunks")
    embeddings = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")

class DocumentEmbedding(Base):
    """Table pour stocker les embeddings des documents complets"""
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("medical_documents.id"), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    vector_id = Column(String(100), nullable=False)  # ID dans Chroma
    embedding_dimension = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    document = relationship("MedicalDocument", back_populates="embeddings")

class ChunkEmbedding(Base):
    """Table pour stocker les embeddings des chunks"""
    __tablename__ = "chunk_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    vector_id = Column(String(100), nullable=False)  # ID dans Chroma
    embedding_dimension = Column(Integer, nullable=False)
    similarity_threshold = Column(Float, default=0.7)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    chunk = relationship("DocumentChunk", back_populates="embeddings")

class MedicalSpecialty(Base):
    """Table pour les spécialités médicales"""
    __tablename__ = "medical_specialties"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    code = Column(String(20), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QueryLog(Base):
    """Table pour logger les requêtes RAG"""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Résultats
    results_count = Column(Integer, default=0)
    top_similarity_score = Column(Float, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Métadonnées
    embedding_model_used = Column(String(100), nullable=True)
    retrieval_method = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())