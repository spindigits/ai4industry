import os
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBEDDING_MODEL

class QdrantConnector:
    """Manages interactions with Qdrant vector database."""
    
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.client = self._connect()
        self.vector_store = self._init_vector_store()
        
    def _connect(self) -> QdrantClient:
        """Connect to Qdrant Cloud or fallback to local memory."""
        is_configured = (
            QDRANT_URL 
            and QDRANT_API_KEY 
            and "your_qdrant_url" not in QDRANT_URL
        )
        
        if is_configured:
            try:
                # Extract host from URL (remove https:// prefix)
                host = QDRANT_URL.replace("https://", "").replace("http://", "").rstrip("/")
                
                # Use host/port/https approach for better compatibility
                # The 'url' parameter has issues with some network configurations
                client = QdrantClient(
                    host=host,
                    port=443,
                    api_key=QDRANT_API_KEY,
                    https=True,
                    prefer_grpc=False,  # Force REST mode
                    timeout=60
                )
                # Test connection by getting collection info
                info = client.get_collection(COLLECTION_NAME)
                print(f"✅ Connected to Qdrant Cloud (collection: {COLLECTION_NAME}, {info.points_count} points)")
                return client
            except Exception as e:
                print(f"⚠️ Failed to connect to Qdrant Cloud ({e}). Falling back to local memory.")
        
        print("📦 Using local Qdrant (in-memory).")
        return QdrantClient(location=":memory:")
    
    def _init_vector_store(self) -> QdrantVectorStore:
        """Initialize the vector store."""
        if not self.client.collection_exists(COLLECTION_NAME):
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            
        return QdrantVectorStore(
            client=self.client,
            collection_name=COLLECTION_NAME,
            embedding=self.embeddings,
        )

    def index_documents(self, documents):
        """Index documents into Qdrant."""
        if not documents:
            return 0
        self.vector_store.add_documents(documents)
        return len(documents)
    
    def get_retriever(self):
        """Get the retriever object."""
        return self.vector_store.as_retriever()
