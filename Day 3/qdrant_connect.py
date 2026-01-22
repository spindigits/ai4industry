"""
Qdrant Vector Database Connection and Operations
"""
import uuid
from typing import List, Dict, Tuple
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL,
    PRIVATE_PATTERN, TEMPORAL_KEYWORDS
)


class QdrantConnector:
    """Gestionnaire de connexion et opérations Qdrant"""
    
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.collection_name = COLLECTION_NAME
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
        
    def create_collection(self) -> str:
        """Crée la collection Qdrant si elle n'existe pas"""
        try:
            collections = self.client.get_collections().collections
            if any(c.name == self.collection_name for c in collections):
                return f"ℹ️ Collection '{self.collection_name}' existe déjà"
            
            # Get embedding dimension
            test_embedding = self.embeddings.embed_query("test")
            vector_size = len(test_embedding)
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            return f"✅ Collection '{self.collection_name}' créée avec succès"
            
        except Exception as e:
            return f"❌ Erreur création collection: {str(e)}"
    
    def reset_collection(self) -> str:
        """Supprime et recrée la collection"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            return self.create_collection()
        except Exception as e:
            return f"❌ Erreur reset collection: {str(e)}"
    
    def is_temporal_content(self, filename: str, text: str) -> bool:
        """Détecte si le contenu est temporel (prix, stock, etc.)"""
        combined_text = f"{filename} {text}".lower()
        return any(keyword in combined_text for keyword in TEMPORAL_KEYWORDS)
    
    def index_documents(self, documents: List[Dict], filename: str) -> str:
        """
        Index des documents dans Qdrant avec ID intelligents
        
        Args:
            documents: Liste de dicts avec 'text' et 'metadata'
            filename: Nom du fichier source
            
        Returns:
            Message de statut
        """
        try:
            if not documents:
                return "⚠️ Aucun document à indexer"
            
            # Détecter si données temporelles
            full_text = " ".join([doc.get('text', '') for doc in documents])
            is_temporal = self.is_temporal_content(filename, full_text)
            
            # Timestamp pour données temporelles
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S") if is_temporal else None
            
            points = []
            for idx, doc in enumerate(documents):
                text = doc.get('text', '')
                metadata = doc.get('metadata', {})
                
                # Générer embedding
                embedding = self.embeddings.embed_query(text)
                
                # Générer un UUID unique pour chaque point
                point_id = str(uuid.uuid4())
                
                # Enrichir métadonnées
                enhanced_metadata = {
                    **metadata,
                    'source': filename,
                    'chunk_index': idx,
                    'is_temporal': is_temporal,
                    'timestamp': timestamp,
                    'indexed_at': datetime.now().isoformat()
                }
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            'text': text,
                            **enhanced_metadata
                        }
                    )
                )
            
            # Upsert dans Qdrant (écrase si ID existe pour données stables)
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            data_type = "📅 TEMPORELLES (historique)" if is_temporal else "📌 STABLES (écrasement)"
            return f"✅ {len(points)} chunks indexés - Type: {data_type}"
            
        except Exception as e:
            return f"❌ Erreur indexation: {str(e)}"
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Recherche vectorielle dans Qdrant
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre de résultats
            
        Returns:
            Liste de chunks avec métadonnées et scores
        """
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            chunks = []
            for hit in results:
                chunks.append({
                    'text': hit.payload.get('text', ''),
                    'metadata': {
                        'source': hit.payload.get('source', 'unknown'),
                        'chunk_index': hit.payload.get('chunk_index', 0),
                        'is_temporal': hit.payload.get('is_temporal', False),
                        'timestamp': hit.payload.get('timestamp'),
                        'indexed_at': hit.payload.get('indexed_at'),
                    },
                    'score': hit.score
                })
            
            return chunks
            
        except Exception as e:
            print(f"❌ Erreur recherche: {str(e)}")
            return []
    
    def filter_private_chunks(self, chunks: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Filtre les chunks contenant des données privées
        
        Returns:
            (chunks_filtrés, nombre_filtrés)
        """
        filtered = []
        filtered_count = 0
        
        for chunk in chunks:
            text = chunk.get('text', '')
            if PRIVATE_PATTERN.search(text):
                filtered_count += 1
            else:
                filtered.append(chunk)
        
        return filtered, filtered_count
    
    def get_collection_info(self) -> Dict:
        """Retourne des infos sur la collection"""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                'exists': True,
                'points_count': info.points_count,
                'vectors_count': info.vectors_count
            }
        except Exception:
            return {'exists': False}
