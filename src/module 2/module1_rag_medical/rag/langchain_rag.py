from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.vectorstores import Chroma
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
from config.settings import settings
from embeddings.chroma_manager import chroma_manager
from embeddings.embedding_manager import embedding_manager

logger = logging.getLogger(__name__)

class MedicalRAGSystem:
    """Système RAG spécialisé pour les connaissances médicales"""
    
    def __init__(self):
        self.text_splitter = None
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.qa_chain = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialise tous les composants RAG"""
        try:
            # Initialiser le text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            
            # Initialiser les embeddings LangChain
            self.embeddings = SentenceTransformerEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_kwargs={'device': settings.EMBEDDING_DEVICE}
            )
            
            # Initialiser le vectorstore
            self._setup_vectorstore()
            
            # Initialiser le retriever
            self._setup_retriever()
            
            logger.info("RAG system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            raise
    
    def _setup_vectorstore(self):
        """Configure le vectorstore Chroma"""
        try:
            self.vectorstore = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY
            )
            logger.info("Vectorstore configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup vectorstore: {e}")
            raise
    
    def _setup_retriever(self):
        """Configure le retriever avec compression contextuelle"""
        try:
            # Retriever de base
            base_retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.TOP_K_RETRIEVAL}
            )
            
            # Pour l'instant, on utilise le retriever de base
            # La compression contextuelle nécessiterait un LLM
            self.retriever = base_retriever
            
            logger.info("Retriever configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup retriever: {e}")
            raise
    
    def process_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Document]:
        """Traite et divise les documents en chunks"""
        try:
            processed_docs = []
            
            for i, doc_content in enumerate(documents):
                # Créer le document LangChain
                metadata = metadatas[i] if metadatas else {}
                document = Document(
                    page_content=doc_content,
                    metadata=metadata
                )
                
                # Diviser en chunks
                chunks = self.text_splitter.split_documents([document])
                
                # Ajouter des métadonnées aux chunks
                for j, chunk in enumerate(chunks):
                    chunk.metadata.update({
                        'chunk_index': j,
                        'total_chunks': len(chunks),
                        'source_doc_index': i
                    })
                
                processed_docs.extend(chunks)
            
            logger.info(f"Processed {len(documents)} documents into {len(processed_docs)} chunks")
            return processed_docs
            
        except Exception as e:
            logger.error(f"Failed to process documents: {e}")
            raise
    
    def add_documents_to_vectorstore(
        self,
        documents: List[Document]
    ) -> List[str]:
        """Ajoute des documents au vectorstore"""
        try:
            # Ajouter au vectorstore LangChain
            doc_ids = self.vectorstore.add_documents(documents)
            
            logger.info(f"Added {len(documents)} documents to vectorstore")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents to vectorstore: {e}")
            raise
    
    def retrieve_relevant_docs(
        self,
        query: str,
        k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Récupère les documents pertinents pour une requête"""
        try:
            if k is None:
                k = settings.TOP_K_RETRIEVAL
            
            # Configurer les paramètres de recherche
            search_kwargs = {"k": k}
            if filter_metadata:
                search_kwargs["filter"] = filter_metadata
            
            # Effectuer la recherche
            relevant_docs = self.retriever.get_relevant_documents(
                query,
                **search_kwargs
            )
            
            logger.info(f"Retrieved {len(relevant_docs)} relevant documents for query")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Failed to retrieve relevant documents: {e}")
            raise
    
    def create_medical_prompt_template(self) -> PromptTemplate:
        """Crée un template de prompt spécialisé pour le domaine médical"""
        template = """
Vous êtes un assistant médical expert de l'Hôpital Général de Douala. 
Utilisez les informations médicales suivantes pour répondre à la question de manière précise et professionnelle.

CONTEXTE MÉDICAL:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Basez votre réponse uniquement sur les informations fournies dans le contexte
- Si l'information n'est pas disponible, indiquez-le clairement
- Utilisez un langage médical approprié mais accessible
- Mentionnez les sources si disponibles
- En cas de doute, recommandez de consulter un professionnel de santé

RÉPONSE:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def search_medical_knowledge(
        self,
        query: str,
        specialty_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """Recherche dans la base de connaissances médicales"""
        try:
            # Préparer les filtres
            filters = {}
            if specialty_filter:
                filters['specialty'] = specialty_filter
            if document_type_filter:
                filters['document_type'] = document_type_filter
            
            # Récupérer les documents pertinents
            relevant_docs = self.retrieve_relevant_docs(
                query=query,
                k=top_k,
                filter_metadata=filters if filters else None
            )
            
            # Formater les résultats
            results = {
                'query': query,
                'total_results': len(relevant_docs),
                'documents': []
            }
            
            for doc in relevant_docs:
                doc_info = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'source': doc.metadata.get('source', 'Unknown'),
                    'specialty': doc.metadata.get('specialty', 'General'),
                    'document_type': doc.metadata.get('document_type', 'Unknown')
                }
                results['documents'].append(doc_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search medical knowledge: {e}")
            raise
    
    def get_vectorstore_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du vectorstore"""
        try:
            # Obtenir le nombre de documents
            collection = self.vectorstore._collection
            doc_count = collection.count()
            
            # Obtenir des échantillons de métadonnées
            sample_docs = collection.peek(limit=10)
            
            stats = {
                'total_documents': doc_count,
                'collection_name': settings.CHROMA_COLLECTION_NAME,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
                'chunk_size': settings.CHUNK_SIZE,
                'chunk_overlap': settings.CHUNK_OVERLAP,
                'sample_metadatas': sample_docs.get('metadatas', [])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get vectorstore stats: {e}")
            return {}
    
    def similarity_search_with_scores(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[Document, float]]:
        """Recherche de similarité avec scores"""
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )
            
            # Filtrer par seuil de similarité
            filtered_results = [
                (doc, score) for doc, score in results
                if score >= threshold
            ]
            
            logger.info(
                f"Similarity search: {len(filtered_results)}/{len(results)} "
                f"results above threshold {threshold}"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search with scores: {e}")
            raise
    
    def export_knowledge_base(self, export_path: str) -> bool:
        """Exporte la base de connaissances"""
        try:
            # Récupérer tous les documents
            collection = self.vectorstore._collection
            all_data = collection.get(include=["documents", "metadatas"])
            
            export_data = {
                'collection_name': settings.CHROMA_COLLECTION_NAME,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
                'total_documents': len(all_data['documents']),
                'documents': all_data['documents'],
                'metadatas': all_data['metadatas'],
                'ids': all_data['ids']
            }
            
            import json
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Knowledge base exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export knowledge base: {e}")
            return False

# Instance globale du système RAG
medical_rag = MedicalRAGSystem()