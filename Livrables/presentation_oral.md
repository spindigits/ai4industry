# Fil Conducteur - Soutenance Technique MensaFlow (5 min)

## 🎯 Objectif
Présentation technique d'une solution RAG Hybride (Graph + Vector) répondant aux contraintes de souveraineté et de précision de MensaFlow.

---

## 1. Introduction (Slide 1)
* **Qui :** Présentation du Groupe 1.
* **Quoi :** Solution de **RAG Hybride**.
* **Pour qui :** Réponse à la problématique client **MensaFlow** (Use Case : GreenPower Solutions).

## 2. Contexte & Problématique (Slide 2 - Sommaire)
* **Le Client (MensaFlow) :**
    * [cite_start]Société de services IA (MensaBot, MensaMail) fondée par A. Garrigos & W. Thompson[cite: 6].
    * [cite_start]Infrastructure souveraine (Serveurs 00 et 01)[cite: 7].
* **La Problématique :**
    * Besoin de traiter des données métiers complexes.
    * Limites du RAG classique (hallucinations, manque de précision sur les calculs/relations).
    * [cite_start]Exigence de souveraineté des données (espaces privés)[cite: 8].

## 3. La Solution : RAG Hybride Multi-hop (Slide 3)
* **Concept clé : Le Routeur Intelligent.**
    * Analyse de la question utilisateur basée sur des **mots-clés**.
    * Fonction de décision (algorithme interne) :
        * **Question Simple :** Redirection vers **Qdrant** (Base Vectorielle).
        * **Question Complexe :** Redirection vers **Neo4j** (Base Graphe) pour le *Multi-hop* (corrélation d'infos).
* **Performance :**
    * Solution déployable sur infrastructure client.
    * [cite_start]Rapidité : Temps de réponse **< 3 secondes**[cite: 56].
    * Adaptabilité : Choix automatique du LLM (Mistral AI) selon la complexité.

## 4. Architecture Technique (Slide 4 - Schéma)
* **Flux de Requête (Inférence) :**
    1.  Utilisateur → Interface Streamlit.
    2.  **Routeur** : Classification (Simple vs Complexe).
    3.  **Engine** : Interrogation Qdrant ou Neo4j (ou les deux).
    4.  **LLM** : Génération de la réponse via Mistral AI.
    5.  Retour à l'utilisateur.
* **Flux d'Ingestion (Data Pipeline) :**
    1.  Upload de documents via Streamlit.
    2.  Parsing & Chunking.
    3.  Embedding (Mistral) → Stockage dans les bases (Vectorielle & Graphique).

## 5. Fonctionnalités & Interface (Slide 5)
* **Support Multi-formats :**
    * Documents classiques : TXT, JSON, CSV, PDF.
    * [cite_start]**Multimodalité (Images) :** Traitement via **VLLM (Pixtral)** pour comprendre les schémas/images[cite: 60].
* **Barre Latérale (Sidebar) :**
    * Upload de fichiers.
    * Administration : Reset des bases de données.
    * **Personnalisation :** Choix du modèle (LLM) manuel possible si besoin de plus de précision.

## 6. Dashboard & Métriques (Slide 6)
* **Monitoring en temps réel :**
    * État de la base **Qdrant** (Nombre de documents vectorisés).
    * État de la base **Neo4j** (Distribution des Nœuds et Relations).
* **Performance :**
    * Tests de latence (Ping BDD/LLM).
    * Visualisation de la structure du graphe chargé.

## 7. Exemple Concret & Démo (Slide 7)
* **Le scénario (GreenPower) :**
    * [cite_start]Question complexe type : *"Quels sont les salons avec des ventes aux collectivités ?"*[cite: 61].
* **La mécanique visible :**
    * Le système identifie le besoin de *Multi-hop*.
    * Il traverse le graphe : Nœud `Salon` ↔ Relation `Vente` ↔ Attribut `Collectivité`.
    * Affichage des **sources consultées** : Preuve du cheminement logique (Nodes traversés) vs simple recherche documentaire.

---

## 💡 Conseils pour l'oral
* **Ne pas lire :** Utilise ces points comme des "déclencheurs" de mémoire.
* **Focus technique :** Insiste sur le **Routeur**, **Neo4j** (Graph) et **Pixtral** (VLLM), ce sont tes points forts techniques.
* **Fluidité :** Fais le lien entre la Slide 3 (Théorie du routeur) et la Slide 7 (Preuve par l'exemple).