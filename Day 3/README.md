# GreenPower RAG System - Phase 02

## 🎯 Architecture Modulaire

Découpage du notebook Jupyter en modules Python pour:
- ✅ Meilleure maintenabilité
- ✅ Réutilisabilité du code
- ✅ Préparation Phase 03 (GraphRAG)
- ✅ Intégration future avec agents

## 📁 Structure du Projet

```
greenpower-rag/
├── config.py              # Configuration centralisée
├── qdrant_connect.py      # Connexion & opérations Qdrant
├── neo4j_connect.py       # Connexion Neo4j (Phase 03)
├── rag_features.py        # HybridRetriever avec routing
├── document_utils.py      # Utilitaires chargement docs
├── interface.py           # Interface Gradio
├── requirements.txt       # Dépendances Python
├── .env.template          # Template configuration
└── README.md             # Cette doc
```

## 🚀 Installation

```bash
# 1. Créer environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Configurer .env
cp .env.template .env
# Éditer .env avec vos clés API
```

## ⚙️ Configuration (.env)

```bash
# Obligatoire
MISTRAL_API_KEY=your_key_here

# Qdrant - Choisir une option:
QDRANT_URL=:memory:                                    # Local (test)
# QDRANT_URL=https://xxx.cloud.qdrant.io              # Cloud (prod)
# QDRANT_API_KEY=your_key_here                        # Si cloud
```

## 🎮 Utilisation

### Lancer l'interface Gradio

```bash
python interface.py
```

Ouvre l'interface sur: http://127.0.0.1:7855

### Utilisation programmatique

```python
from qdrant_connect import QdrantConnector
from rag_features import SimpleRAG
from document_utils import load_document, split_into_chunks

# Initialiser
qdrant = QdrantConnector()
rag = SimpleRAG()

# Créer collection
qdrant.create_collection()

# Charger et indexer document
text = load_document("documents/politique_rh.pdf")
docs = split_into_chunks(text, qdrant.text_splitter)
qdrant.index_documents(docs, "politique_rh.pdf")

# Poser question
answer = rag.search_and_answer("Quelle est la politique de congés?", top_k=3)
print(answer)
```

## 📦 Modules Détaillés

### config.py
Configuration centralisée:
- API keys (Mistral, Qdrant)
- Paramètres chunking
- Patterns (private, temporal)
- Config interface Gradio

### qdrant_connect.py
Classe `QdrantConnector`:
- `create_collection()` - Crée collection Qdrant
- `index_documents()` - Index avec ID intelligents
- `search()` - Recherche vectorielle
- `filter_private_chunks()` - Filtre données privées
- `is_temporal_content()` - Détecte données temporelles

### neo4j_connect.py (Phase 03)
Classe `Neo4jConnector`:
- `search_graph()` - Recherche dans graphe
- `enrich_context()` - Enrichit résultats Qdrant
- `execute_cypher()` - Exécute requêtes Cypher

**Status:** Placeholder pour Phase 03

### rag_features.py
**Classe `HybridRetriever`:**
- `route_query()` - Routing Qdrant/Neo4j
- `retrieve()` - Récupère chunks selon route
- `generate_answer()` - Génère réponse Mistral

**Classe `SimpleRAG`:**
- `search_and_answer()` - RAG simple Phase 02

### document_utils.py
Utilitaires chargement:
- `load_pdf()`, `load_docx()`, `load_txt()`
- `load_json()`, `load_csv()`
- `load_document()` - Auto-détecte format
- `split_into_chunks()` - Découpe en chunks

### interface.py
Interface Gradio avec 3 tabs:
1. **Upload Documents** - Upload + indexation
2. **Recherche & Questions** - RAG interface
3. **Info** - Documentation système

## 🔄 Versioning Hybride

### Données STABLES (écrasement)
```python
ID = "politique_rh.pdf_5"  # Même ID toujours
→ Re-upload écrase l'ancien
```

**Exemples:** Politiques, procédures, descriptions produits

### Données TEMPORELLES (historique)
```python
ID = "prix_2025.csv_2025-01-20_143022_5"  # ID unique
→ Re-upload garde historique
```

**Exemples:** Prix, salaires, stocks, KPIs

**Détection auto** via keywords: `prix`, `salaire`, `stock`, `budget`, etc.

## 🔒 Filtrage Private

Chunks contenant `private_*` (case-insensitive):
- Filtrés APRÈS recherche vectorielle
- Message clair si toutes données privées
- Patterns: `private_client_001`, `Private_Salary_Data`, etc.

## 🚀 Phase 03 Preview

**HybridRetriever** est prêt pour GraphRAG:

```python
# Phase 03: Activer Neo4j
retriever = HybridRetriever(use_neo4j=True)

# Routing automatique
chunks, route = retriever.retrieve(query)
# route = 'qdrant' | 'neo4j' | 'hybrid'
```

**Routing Logic:**
- **Simple query** → Qdrant (rapide)
- **Multi-hop query** → Neo4j (contexte graphe)
- **Hybrid** → Qdrant first + Neo4j enrichment

**Patterns multi-hop:**
- `related`, `connected`, `linked`
- `customer history`, `product evolution`
- Comparaisons, évolutions temporelles

## 🧪 Tests

```python
# Test Qdrant
from qdrant_connect import QdrantConnector
q = QdrantConnector()
assert q.create_collection() == "✅ Collection 'greenpower_docs' créée avec succès"

# Test routing
from rag_features import HybridRetriever
r = HybridRetriever()
assert r.route_query("What is the price?") == "qdrant"
assert r.route_query("Show customer history and related products") == "neo4j"
```

## 📝 Notes Phase 02

- ✅ 100% Qdrant (vector RAG)
- ✅ Neo4j préparé mais inactif
- ✅ Routing logic implémentée
- ✅ Prêt pour Phase 03

## 🎓 Pour les Étudiants

**Progression pédagogique:**

1. **Phase 01:** Connection Mistral LLM ✅
2. **Phase 02:** Vector RAG (Qdrant) ← VOUS ÊTES ICI
3. **Phase 03:** GraphRAG (Neo4j) ← À VENIR

**Exercices Phase 02:**
- [ ] Tester différents `top_k` (1-10)
- [ ] Uploader documents stables vs temporels
- [ ] Observer IDs générés dans Qdrant dashboard
- [ ] Tester filtrage `private_*`
- [ ] Analyser routing patterns (prépare Phase 03)

## 🔗 Intégration MensaFlow

**Workflow N8N possible:**

```
Trigger (Webhook)
    ↓
Load Document (Python Node: document_utils)
    ↓
Index Qdrant (Python Node: qdrant_connect)
    ↓
RAG Query (Python Node: rag_features)
    ↓
Send Response (Email/Slack/API)
```

## 📚 Ressources

- [Qdrant Docs](https://qdrant.tech/documentation/)
- [Mistral AI Docs](https://docs.mistral.ai/)
- [LangChain Docs](https://python.langchain.com/)
- [Gradio Docs](https://www.gradio.app/docs/)

## 🤝 Support

Questions? Contactez votre formateur ou ouvrez une issue.

---

**Version:** Phase 02 - Vector RAG  
**Date:** Janvier 2025  
**Auteur:** AI4industry Training Program
