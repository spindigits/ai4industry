# Migration Guide: Jupyter → Modules Python

## 📊 Comparaison Architecture

### AVANT (08_Small_RAG_v08.ipynb)
```
Jupyter Notebook (1 fichier)
├── Cell 1: pip install
├── Cell 2: imports
├── Cell 3: config variables
├── Cell 4: init clients
├── Cell 5: create collection
├── Cell 6-8: document processing
├── Cell 9: search & answer
└── Cell 10: Gradio interface (600+ lignes)
```

**Problèmes:**
- ❌ Tout dans un seul fichier
- ❌ Difficile à réutiliser
- ❌ Impossible d'importer dans autres projets
- ❌ Pas de séparation des responsabilités
- ❌ Tests difficiles

### APRÈS (Architecture Modulaire)
```
greenpower-rag/
├── config.py              (50 lignes)  → Configuration
├── qdrant_connect.py      (200 lignes) → Vector DB
├── neo4j_connect.py       (80 lignes)  → Graph DB (Phase 03)
├── rag_features.py        (250 lignes) → RAG Logic + Routing
├── document_utils.py      (120 lignes) → Document Loading
├── interface.py           (250 lignes) → Gradio UI
├── test_modules.py        (150 lignes) → Tests
└── README.md              (300 lignes) → Documentation
```

**Avantages:**
- ✅ Modulaire et réutilisable
- ✅ Importable dans N8N, agents, etc.
- ✅ Testable unitairement
- ✅ Séparation claire des responsabilités
- ✅ Prêt pour Phase 03 (GraphRAG)

## 🔄 Mapping Notebook → Modules

| Notebook Cell | Module | Fonction/Classe |
|---------------|--------|-----------------|
| Cell 1 (pip install) | `requirements.txt` | Dépendances |
| Cell 2 (imports) | Chaque module | Imports locaux |
| Cell 3 (config) | `config.py` | Variables globales |
| Cell 4 (init clients) | `qdrant_connect.py` | `QdrantConnector.__init__()` |
| Cell 5 (create collection) | `qdrant_connect.py` | `QdrantConnector.create_collection()` |
| Cell 6 (is_temporal) | `qdrant_connect.py` | `QdrantConnector.is_temporal_content()` |
| Cell 7 (load_document) | `document_utils.py` | `load_pdf()`, `load_docx()`, etc. |
| Cell 8 (index_docs) | `qdrant_connect.py` | `QdrantConnector.index_documents()` |
| Cell 9 (search & answer) | `rag_features.py` | `SimpleRAG.search_and_answer()` |
| Cell 10 (Gradio UI) | `interface.py` | Interface complète |

## 🎯 Nouveautés Architecture

### 1. Classe HybridRetriever (rag_features.py)

**Nouveau concept** pour Phase 03:

```python
from rag_features import HybridRetriever

# Phase 02: Pure Qdrant
retriever = HybridRetriever(use_neo4j=False)

# Phase 03: Hybrid Qdrant + Neo4j
retriever = HybridRetriever(use_neo4j=True)

# Routing automatique
chunks, route = retriever.retrieve("Show customer history")
# route = 'qdrant' | 'neo4j' | 'hybrid'
```

**Routing patterns:**

| Query Type | Pattern | Route |
|------------|---------|-------|
| Simple fact | "What is X?", "Define Y" | qdrant |
| Price/spec | "prix", "tarif", "spec" | qdrant |
| Multi-hop | "related", "history", "evolution" | neo4j |
| Complex | Pas de match clair | hybrid |

### 2. Neo4j Connector (neo4j_connect.py)

**Placeholder Phase 03:**

```python
class Neo4jConnector:
    def search_graph(self, query, entities):
        """Recherche multi-hop dans Neo4j"""
        # À implémenter Phase 03
        
    def enrich_context(self, qdrant_results):
        """Enrichit résultats Qdrant avec graphe"""
        # À implémenter Phase 03
```

**Prêt pour:**
- Connexion Neo4j
- Requêtes Cypher
- Enrichissement contextuel
- Multi-hop traversal

### 3. Document Utils (document_utils.py)

**Centralise chargement docs:**

```python
from document_utils import load_document, split_into_chunks

# Auto-détecte format
text = load_document("document.pdf")  # ou .docx, .txt, .json, .csv

# Split en chunks
docs = split_into_chunks(text, text_splitter)
```

**Formats supportés:**
- PDF, DOCX, TXT
- JSON (converti en texte)
- CSV (converti en lignes lisibles)

### 4. Config Centralisée (config.py)

**Avant:** Variables éparpillées dans le notebook

**Après:** Tout dans `config.py`

```python
from config import (
    MISTRAL_API_KEY,
    QDRANT_URL,
    COLLECTION_NAME,
    CHUNK_SIZE,
    TEMPORAL_KEYWORDS,
    # ... etc
)
```

**Avantage:** Change config une fois, impacte tous les modules

## 🔧 Comment Utiliser

### Option 1: Interface Gradio (comme avant)

```bash
python interface.py
```

Identique au notebook, mais avec code modulaire.

### Option 2: Script Python

```python
from qdrant_connect import QdrantConnector
from rag_features import SimpleRAG
from document_utils import load_document, split_into_chunks

# Init
qdrant = QdrantConnector()
rag = SimpleRAG()

# Setup
qdrant.create_collection()

# Load doc
text = load_document("greenpower_products.pdf")
docs = split_into_chunks(text, qdrant.text_splitter)

# Index
result = qdrant.index_documents(docs, "greenpower_products.pdf")
print(result)

# Query
answer = rag.search_and_answer("Quels sont les prix?", top_k=3)
print(answer)
```

### Option 3: Intégration N8N

**Workflow possible:**

```
[Webhook Trigger]
    ↓
[Python Code Node]
    from qdrant_connect import QdrantConnector
    from document_utils import load_document, split_into_chunks
    
    text = load_document(input_file)
    docs = split_into_chunks(text, splitter)
    
    qdrant = QdrantConnector()
    result = qdrant.index_documents(docs, filename)
    
    return result
    ↓
[Send Email/Slack]
```

### Option 4: Agent Integration (Futur)

```python
# Agent peut importer et utiliser
from rag_features import HybridRetriever

class RAGAgent:
    def __init__(self):
        self.retriever = HybridRetriever(use_neo4j=True)
    
    def answer_question(self, query):
        chunks, route = self.retriever.retrieve(query)
        return self.retriever.generate_answer(query, chunks, route)
```

## 🧪 Tests

### Lancer tests unitaires:

```bash
python test_modules.py
```

**Output attendu:**
```
🧪 Test 1: Imports des modules...
  ✅ config.py
  ✅ qdrant_connect.py
  ✅ neo4j_connect.py
  ✅ rag_features.py
  ✅ document_utils.py

🧪 Test 2: Routing Logic...
  ✅ 'What is the price?...' → qdrant
  ✅ 'Show customer history...' → neo4j

🧪 Test 3: QdrantConnector...
  ✅ Détection temporelle (prix)
  ✅ Collection créée

📊 RÉSULTATS
Tests passés: 4/4
✅ TOUS LES TESTS SONT PASSÉS!
```

## 📚 Pour les Étudiants

### Phase 02 - Exercices Pratiques

**1. Comprendre le découpage**
- [ ] Ouvrir `config.py` → voir toutes les variables
- [ ] Ouvrir `qdrant_connect.py` → classe QdrantConnector
- [ ] Ouvrir `rag_features.py` → classe HybridRetriever
- [ ] Comparer avec notebook original

**2. Tester le routing**
```python
from rag_features import HybridRetriever

r = HybridRetriever()

# Tester différentes queries
queries = [
    "What is the price?",           # → qdrant
    "Customer history and orders",  # → neo4j (si activé)
    "Evolution of stocks",          # → neo4j
]

for q in queries:
    print(f"{q} → {r.route_query(q)}")
```

**3. Modifier le routing**
```python
# Dans rag_features.py, ligne ~45
self.multi_hop_patterns = [
    # Ajouter vos propres patterns
    r'\bhistorique\b',
    r'\bcomparer\b',
]
```

**4. Créer votre propre loader**
```python
# Dans document_utils.py
def load_xml(file_path: str) -> str:
    """Charge un fichier XML"""
    # Votre code ici
    pass

# Ajouter dans loaders dict
loaders = {
    '.xml': load_xml,  # Nouveau
    '.pdf': load_pdf,
    # ...
}
```

### Phase 03 - Preview

**À venir:**
- Implémenter `Neo4jConnector.search_graph()`
- Activer routing dans `HybridRetriever`
- Créer ontologies GreenPower dans Neo4j
- Comparer performances Qdrant vs Neo4j

## 🎓 Concepts Clés

### Séparation des Responsabilités

| Module | Responsabilité | Dépendances |
|--------|----------------|-------------|
| `config.py` | Configuration | Aucune |
| `document_utils.py` | Chargement docs | `pypdf`, `docx` |
| `qdrant_connect.py` | Vector DB | `config`, `qdrant-client` |
| `neo4j_connect.py` | Graph DB | `config` (Phase 03: `neo4j`) |
| `rag_features.py` | RAG Logic | `config`, `qdrant_connect`, `neo4j_connect` |
| `interface.py` | UI | Tous les modules ci-dessus |

### Inversion de Dépendances

**Avant (Notebook):**
```
Tout dépend de tout → spaghetti code
```

**Après (Modules):**
```
interface.py
    ↓
rag_features.py
    ↓ ↓
qdrant_connect.py  neo4j_connect.py
    ↓ ↓
config.py
```

### Testabilité

**Avant:** Impossible de tester sans lancer tout le notebook

**Après:** Chaque module testable indépendamment

```python
# test_qdrant.py
def test_temporal_detection():
    q = QdrantConnector()
    assert q.is_temporal_content("prix.csv", "prix") == True
    assert q.is_temporal_content("policy.pdf", "rules") == False
```

## 🚀 Migration Rapide

**Pour migrer votre propre notebook:**

1. **Identifier les blocs fonctionnels**
   - Configuration
   - Connexions DB
   - Processing logic
   - UI

2. **Créer modules correspondants**
   - `config.py` → variables
   - `{service}_connect.py` → connexions
   - `{feature}.py` → logique métier
   - `interface.py` → UI

3. **Extraire et réorganiser**
   - Copier code par bloc
   - Créer classes/fonctions
   - Importer entre modules
   - Tester progressivement

4. **Tester**
   - Créer `test_{module}.py`
   - Valider chaque module
   - Intégration finale

## 📖 Ressources

**Code original:**
- `08_Small_RAG_v08-fixed_ids.ipynb` (notebook monolithique)

**Code modulaire:**
- Tous les fichiers `.py` dans ce dossier

**Docs:**
- `README.md` - Documentation générale
- Ce fichier - Guide migration

## ❓ FAQ

**Q: Pourquoi découper?**
A: Réutilisabilité, testabilité, maintenabilité, scalabilité.

**Q: Phase 02 vs Phase 03?**
A: Phase 02 = Pure Qdrant. Phase 03 = + Neo4j GraphRAG.

**Q: HybridRetriever nécessaire en Phase 02?**
A: Non mais préparé pour Phase 03. Utilisez `SimpleRAG` si plus simple.

**Q: Peut-on garder le notebook?**
A: Oui pour prototypage. Modules pour production/intégration.

**Q: Performance impact?**
A: Aucun. Même code, juste réorganisé.

---

**Prochaine étape:** Phase 03 - Implémenter GraphRAG avec Neo4j!
