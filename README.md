# GROUPE 1 - RAG UI 🤖

> **Système RAG Hybride Intelligent pour GreenPower Solutions**

Ce projet implémente une interface de **Retrieval-Augmented Generation (RAG)** avancée combinant deux puissantes approches pour répondre aux questions sur les produits solaires autonomes et leurs déploiements :
1. **Recherche Vectorielle (Qdrant)** : Pour les questions factuelles et descriptives.
2. **Graphe de Connaissances (Neo4j)** : Pour les questions complexes nécessitant du raisonnement multi-hop et des agrégations relationnelles.

---

## ✨ Fonctionnalités Clés

- **🧠 Routeur Intelligent** : Analyse votre question et choisit automatiquement la meilleure stratégie (RAG Simple vs RAG Hybride).
- **🕸️ Raisonnement Multi-Hop** : Capable de naviguer dans le graphe pour relier des produits, des événements, des ventes et des projets R&D.
- **📊 Dashboard Temps Réel** : Visualisez les métriques de vos bases de données (Qdrant & Neo4j) et analysez les performances des requêtes.
- **📁 Ingestion Flexible** : Supporte le chargement de fichiers `.txt`, `.json`, `.csv` et `.pdf` (avec extraction intelligente).
- **🖥️ Interface Moderne** : Une UI Streamlit soignée, intuitive et responsive.

---

## 🏗️ Architecture

Le système s'appuie sur une architecture robuste :
- **Frontend** : Streamlit
- **LLM & Embeddings** : Mistral AI (via LangChain)
- **Vector Store** : Qdrant
- **Graph Database** : Neo4j
- **Orchestration** : LangChain & Logique personnalisée (HybridRAG)

---

## 🚀 Installation

### Prérequis
- Python 3.9+
- Une instance **Neo4j** active (Locale ou AuraDB)
- Un cluster **Qdrant** (ou mode local)
- Une clé API **Mistral AI**

### Étapes

1. **Cloner le dépòt**
   ```bash
   git clone <votre-repo-url>
   cd ragmultihop-main
   ```

2. **Créer un environnement virtuel**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration (.env)**
   Créez un fichier `.env` à la racine du projet et remplissez-le avec vos identifiants :
   ```env
   MISTRAL_API_KEY=votre_cle_mistral
   
   QDRANT_ENDPOINT=https://votre-cluster.qdrant.io
   QDRANT_API_KEY=votre_cle_qdrant
   
   NEO4J_URI=neo4j+ssc://votre-instance.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=votre_mot_de_passe
   ```

---

## 🎮 Utilisation

### Lancer l'application
```bash
streamlit run app.py
```

### Guide de l'interface

#### 1. Sidebar (Menu Latéral)
- **Importer des documents** : Glissez-déposez vos fichiers de données ici pour les indexer dans Qdrant.
- **Admin** : Boutons pour réinitialiser ou nettoyer les bases Neo4j et Qdrant.
- **Modèle** : Choisissez le modèle de langage (ex: `mistral-small`, `mistral-large`).

#### 2. Onglet "🧭 ChatBOT"
C'est le cœur du système. Posez votre question dans la barre de chat.
- **Mode Auto** : Le système vous dira s'il utilise le mode "Simple" ou "Multi-hop".
- **Réponse** : La réponse générée s'affiche clairement.
- **Sources** : Explorez les onglets "Documents" (Qdrant) et "Relations" (Neo4j) pour voir d'où vient l'information.

#### 3. Onglet "📊 Dashboard Métriques"
Surveillez la santé de votre système :
- Nombre de documents vectorisés.
- Nombre de nœuds et relations dans le graphe.
- Tests de performance (latence des requêtes).

---

## 💾 Données & Modèle
Le système gère les entités suivantes dans Neo4j :
- `Product` (Produits)
- `Event` (Événements / Festivals)
- `TradeShow` (Salons professionnels)
- `Sale` (Ventes)
- `RDProject` (Projets R&D)
- `BatteryType` (Types de batteries)

---

## 👥 Crédits

**Développé avec ❤️ par l'équipe :**
- Enzo
- Kyllian
- Romain
- Will
- Yovèn
