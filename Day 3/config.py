"""
Configuration centralisée pour GreenPower RAG System
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL', ':memory:')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', None)

# Collection name
COLLECTION_NAME = "greenpower_docs"

# Chunking configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# LLM configuration
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_TEMPERATURE = 0.7

# 🔒 PATTERN POUR DÉTECTER LES DONNÉES PRIVÉES
PRIVATE_PATTERN = re.compile(r'private_\w+', re.IGNORECASE)

# 📅 PATTERNS POUR DÉTECTER LES DONNÉES TEMPORELLES
TEMPORAL_KEYWORDS = [
    'prix', 'price', 'tarif', 'tarification',
    'salaire', 'salary', 'paie', 'remuneration',
    'stock', 'inventory', 'inventaire',
    'budget', 'kpi', 'metric', 'metriques',
    'vente', 'sales', 'ca', 'chiffre',
    'cours', 'cotation', 'taux', 'rate'
]

# Interface configuration
GRADIO_SERVER_NAME = "127.0.0.1"
GRADIO_SERVER_PORT = 7865
GRADIO_SHARE = False
