# Blueprint - GROUPE 1 - RAG UI

Groupe 1

## 📋 Vue d'ensemble du projet

Système de **Retrieval-Augmented Generation (RAG) Hybride** qui combine deux approches complémentaires pour répondre intelligemment aux questions sur les produits et événements de GreenPower Solutions :

- **Recherche vectorielle** (Qdrant + LangChain) pour les questions descriptives simples
- **Graphe de connaissances** (Neo4j) pour les questions relationnelles complexes nécessitant du multi-hop reasoning

### 🎯 Objectif

Permettre de poser des questions en langage naturel sur :
- Les produits solaires autonomes GreenPower
- Les événements (salons, festivals alimentés)
- Les ventes et déploiements
- Les projets R&D
- Les relations entre ces entités

### 🏗️ Architecture Globale

```
┌──────────────────────────────────────────────────────────────────────┐
│                      INTERFACE UTILISATEUR                            │
│                         (app.py - Streamlit)                          │
│                                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │   RAG    │  │   RAG    │  │ Routeur  │  │  Dashboard   │        │
│  │  Simple  │  │ Hybride  │  │  Intel.  │  │  Métriques   │        │
│  │ (Qdrant) │  │  Q+Neo4j │  │  (Auto)  │  │(src/ui/dash) │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE DE ROUTAGE                         │
│                  (src/core/hybrid_rag.py)                    │
│                                                               │
│  classify_question() → détermine la stratégie optimale       │
│     ├── Keywords multi-hop → RAG Hybride                     │
│     └── Keywords simples → RAG Simple                        │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│  QDRANT          │                    │  NEO4J           │
│  (Vectoriel)     │                    │  (Graphe)        │
│                  │                    │                  │
│ • Embeddings     │                    │ • Nœuds:         │
│ • Similarité     │                    │   - Product      │
│   sémantique     │                    │   - Event        │
│ • Documents      │                    │   - TradeShow    │
│                  │                    │   - Sale         │
│                  │                    │   - RDProject    │
│                  │                    │   - BatteryType  │
│                  │                    │                  │
│                  │                    │ • Relations:     │
│                  │                    │   - DEPLOYED_AT  │
│                  │                    │   - SOLD_AT      │
│                  │                    │   - USES_BATTERY │
│                  │                    │   - etc.         │
└──────────────────┘                    └──────────────────┘
        │                                         │
        └────────────────────┬────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     MISTRAL AI LLM                           │
│              (via LangChain ChatMistralAI)                   │
│  • Génération de réponses contextualisées                    │
│  • Embeddings (MistralAIEmbeddings)                          │
│  • Chat (mistral-small-latest, mistral-large, pixtral)       |
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Modules et Fonctionnalités

### 1. **src/core/hybrid_rag.py** - Routeur Intelligent et Orchestrateur

**Rôle principal**: Classifier les questions et orchestrer la stratégie de réponse appropriée.

#### Classe `HybridRAG`

**Fonctionnalités principales**:

- **`classify_question(question)`**
  - Analyse la question pour déterminer la complexité
  - Détecte les mots-clés multi-hop (relations, agrégations, événements) et scores
  - Détecte les mots-clés simples (descriptions, spécifications)
  - Retourne: `"simple"` ou `"multi_hop"`

- **`query_simple(question, vector_store)`**
  - RAG classique avec Qdrant uniquement (via `LangChain QdrantVectorStore`)
  - Recherche par similarité sémantique (top 3 documents)
  - Génère une réponse avec le LLM Mistral
  - Cas d'usage: "Qu'est-ce que le produit GreenPower Max?"

- **`query_hybrid(question, vector_store)`**
  - RAG hybride combinant Qdrant + Neo4j
  - Récupère le contexte vectoriel (Qdrant)
  - Récupère le contexte relationnel (Neo4j via `Neo4jQuerier`)
  - Fusionne les deux contextes dans un prompt enrichi
  - Cas d'usage: "Quels événements ont utilisé des produits vendus à Pollutec Paris?"

- **`query(question, vector_store, force_strategy=None)`**
  - Point d'entrée principal avec routage automatique
  - Permet de forcer une stratégie si nécessaire
  - Retourne: `{answer, sources, strategy}`

- **`explain_routing(question)`**
  - Explique pourquoi une stratégie a été choisie
  - Utile pour la transparence et le debugging

**Exemples de questions traitées**:
- Simple: "Quel est le prix du GreenPower Max?"
- Multi-hop: "Quels projets R&D visent les produits utilisés aux festivals?"
- Multi-hop: "Quel est le CO2 total économisé par PG-M01?"

---

### 2. **src/services/neo4j_query.py** - Requêtes Multi-Hop sur le Graphe

**Rôle principal**: Exécuter des requêtes Cypher complexes pour extraire des informations relationnelles.

#### Classe `Neo4jQuerier`

**Requêtes multi-hop complexes**:

- **`query_events_with_products_sold_at_tradeshows(location=None)`**
  - Chemin: `Product → DEPLOYED_AT → Event` + `Product ← INCLUDES_PRODUCT ← Sale → SOLD_AT → TradeShow`
  - Question: "Quels événements ont utilisé des produits vendus à Pollutec Paris?"
  - Multi-hop: 2 sauts dans le graphe

- **`query_total_co2_saved_by_product(product_id)`**
  - Chemin: `Product → DEPLOYED_AT → Event` (avec agrégation CO2)
  - Question: "Quel est le CO2 total économisé par tous les déploiements de PG-M01?"
  - Agrégation: Somme des réductions CO2 sur tous les événements par produit

- **`query_tradeshows_sales_by_customer_type(customer_type)`**
  - Chemin: `TradeShow ← SOLD_AT ← Sale` (filtré par type client)
  - Question: "Quels salons ont généré le plus de revenus avec les collectivités?"
  - Agrégation: Somme des revenus par salon

- **`query_rd_projects_for_festival_products()`**
  - Chemin: `Event ← DEPLOYED_AT ← Product ← TARGETS_PRODUCT ← RDProject`
  - Question: "Quels projets R&D visent les produits utilisés aux festivals?"
  - Multi-hop: 3 sauts + filtrage par type d'événement

- **`query_events_powered_by_product_type(category)`** (Nouveau)
  - Chemin: `Product → DEPLOYED_AT → Event`
  - Question: "Quels événements ont été alimentés par du Solaire?"
  - Filtre sur la catégorie du produit

**Requêtes simples**:

- **`query_products_by_battery_type(battery_type)`**
  - Recherche produits par type de batterie (LiFePO4, Tesla)

- **`query_top_revenue_tradeshows(limit=5)`**
  - Top salons par revenu généré

- **`query_product_sales_across_tradeshows(product_id)`**
  - Historique des ventes d'un produit sur tous les salons

**Fonctions utilitaires**:

- **`get_graph_context_for_question(question)`**
  - Analyse la question et exécute automatiquement les requêtes pertinentes
  - Logique de détection étendue :
    1. Événements avec produits vendus aux salons
    2. CO2 économisé par produit
    3. Ventes aux collectivités
    4. Projets R&D pour festivals
    5. Produits par type de batterie
    6. Top Salons
    7. Historique de ventes d'un produit
    8. Événements alimentés par type de produit
  - Retourne une liste de résultats structurés

- **`format_graph_context(context)`**
  - Formate les résultats du graphe en texte lisible pour le LLM
  - Convertit les résultats Neo4j en contexte textuel

---

### 3. **src/services/neo4j_loader.py** - Chargement des Données dans le Graphe

**Rôle principal**: Parser les fichiers JSON et créer le graphe Neo4j complet avec toutes les relations.

#### Classe `Neo4jLoader`

**Fonctionnalités**:

- **`clear_database()`**: Nettoie toutes les données du graphe
- **`create_indexes()`**: Index sur product_id, event_id, trade_show_id, etc.
- **`load_products(products_file)`**: Crée noeuds `Product` et `BatteryType`
- **`load_events(events_file)`**: Crée noeuds `TradeShow`, `Event`, `Sale` et relations (`SOLD_AT`, `DEPLOYED_AT`, `INCLUDES_PRODUCT`)
- **`load_rd_projects(rd_file)`**: Crée noeuds `RDProject` et relations `TARGETS_PRODUCT`
- **`load_all()`**: Orchestre le chargement complet

**Modèle de données créé**:
- 6 Types de nœuds: Product, Event, TradeShow, Sale, RDProject, BatteryType
- Relations clés: DEPLOYED_AT, SOLD_AT, INCLUDES_PRODUCT, TARGETS_PRODUCT, USES_BATTERY, DISPLAYED_AT

---

### 4. **app.py** - Interface Utilisateur Streamlit

**Rôle principal**: Interface web interactive pour interagir avec le système RAG hybride.

#### Fonctionnalités de l'application

**Composants**:

- **`src.services.rag_init`**: Initialise les composants LangChain (`QdrantVectorStore`, `ChatMistralAI`) et `HybridRAG`.
- **`src.services.loaders`**: Gestion de l'upload et parsing (PDF, TXT, JSON, CSV).
- **`src.ui.styles`**: CSS personnalisé.

**Onglets principaux**:

1. **🧭 ChatBOT**
   - **Mode Routeur Intelligent**: Classification automatique (simple vs multi-hop). Badge visuel de la stratégie.
   - **Affichage des réponses**: Réponse générée + Sources (Onglets séparés: "📚 Documents (Qdrant)" et "🕸️ Relations (Neo4j)").
   - **Explication du routage**: Affiche pourquoi une stratégie a été choisie.

2. **📊 Dashboard Métriques**
   - Visualisation de l'état des bases de données.

**Sidebar**:
- **Upload de documents**: Drag & drop supporté.
- **Administration**: Reset Neo4j, Reset Qdrant.
- **Modèle de Raisonnement**: Sélecteur de LLM (mistral-small, mistral-large, pixtral).
- **Exemples**: accès rapide aux questions types.

---

### 5. **src/ui/dashboard.py** - Dashboard de Métriques et Performance

**Rôle principal**: Collecter et afficher les métriques de performance en temps réel de Qdrant et Neo4j.

#### Classe `DashboardMetrics` et Fonction `render_dashboard`

- **Métriques Qdrant**: Collection, documents, vecteurs. Test de performance de recherche.
- **Métriques Neo4j**: Compte des nœuds et relations. Test de performance des requêtes Cypher.
- **État du Système**: Indicateurs de santé (Vert/Rouge) pour Qdrant et Neo4j.

---

## 🔄 Flux de Données

### Flux Question → Réponse (RAG Simple)

```
1. Utilisateur pose une question: "Quel est le prix du GreenPower Max?"
   ↓
2. HybridRAG.classify_question() → "simple"
   ↓
3. HybridRAG.query_simple()
   ↓
4. Recherche vectorielle Qdrant (LangChain retriever, top 3)
   ↓
5. Contexte envoyé au LLM Mistral (via PromptTemplate)
   ↓
6. Génération de la réponse
   ↓
7. Retour: {answer, sources: {vector_docs}, strategy: "simple"}
```

### Flux Question → Réponse (RAG Hybride)

```
1. Utilisateur pose: "Quels événements ont utilisé des produits vendus à Paris?"
   ↓
2. HybridRAG.classify_question() → "multi_hop"
   ↓
3. HybridRAG.query_hybrid()
   ↓
4. Parallèlement:
   ├─> Qdrant: recherche vectorielle (top 3 docs)
   └─> Neo4j: get_graph_context_for_question()
       └─> Détecte: "événements" + "vendus" + "paris"
       └─> Exécute: query_events_with_products_sold_at_tradeshows("Paris")
   ↓
5. Fusion des deux contextes dans un prompt enrichi (System + Vector + Graph context)
   ↓
6. LLM Mistral génère réponse basée sur les deux sources
   ↓
7. Retour: {answer, sources: {vector_docs, graph_context}, strategy: "hybrid"}
```

---

## 💾 Modèle de Données Neo4j

### Nœuds

```
(Product)
├─ product_id, name, category, price, ...
(Event)
├─ name, type, location, attendees, co2_reduction, ...
(TradeShow)
├─ name, location, date, ...
(Sale)
├─ customer_type, total_revenue, units
(RDProject)
├─ name, objective, status, projected_savings
(BatteryType)
├─ type
```

### Relations

```
(Product)-[:DEPLOYED_AT {quantity}]->(Event)
(Product)-[:DISPLAYED_AT]->(TradeShow)
(Product)-[:USES_BATTERY]->(BatteryType)

(Sale)-[:SOLD_AT]->(TradeShow)
(Sale)-[:INCLUDES_PRODUCT {quantity}]->(Product)

(RDProject)-[:TARGETS_PRODUCT]->(Product)
```

---

## 🚀 Déploiement et Configuration

### Variables d'environnement requises (.env)

```bash
MISTRAL_API_KEY=your_key_here
QDRANT_ENDPOINT=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key_here
NEO4J_URI=neo4j+ssc://your-instance.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### Commandes principales

```bash
# Lancer l'application
streamlit run app.py
```

---

## 🔍 Avantages de l'Architecture Hybride

- **RAG Simple**: Rapide, simple, idéal pour le factuel.
- **RAG Hybride**: Multi-hop, agrégations, relations, dépasse les limites du vectoriel pur.
- **Routeur Intelligent**: Optimisation automatique des coûts et de la latence.

---

## 🛠️ Technologies Utilisées

| Technologie | Rôle |
|------------|------|
| **Streamlit** | Interface web interactive |
| **Qdrant** | Base vectorielle (embeddings) |
| **Neo4j** | Graphe de connaissances |
| **Mistral AI** | LLM + Embeddings (via LangChain) |
| **LangChain** | Framework RAG (ChatMistralAI, QdrantVectorStore) |
| **Python 3.9+** | Langage principal |

---

## 👥 Crédits

**Développé par le groupe 1 :**
- Enzo
- Kyllian
- Romain
- Will
- Yovèn

