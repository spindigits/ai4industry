import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

# API Keys and Credentials
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_CLIENT_ID = os.getenv("NEO4J_CLIENT_ID", "")
NEO4J_CLIENT_SECRET = os.getenv("NEO4J_CLIENT_SECRET", "")

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# RAG Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "hybrid_rag_collection"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Llama Cloud Configuration
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
