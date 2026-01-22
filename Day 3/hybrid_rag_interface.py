import gradio as gr
from pathlib import Path
from typing import List, Dict, Any
import json
import os
from datetime import datetime
from neo4j import GraphDatabase

from config import (
    COLLECTION_NAME, QDRANT_URL, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, PRIVATE_PATTERN, TEMPORAL_KEYWORDS,
    GRADIO_SERVER_NAME, GRADIO_SERVER_PORT, GRADIO_SHARE
)
from qdrant_connect import QdrantConnector
from rag_features import SimpleRAG
from document_utils import load_document, split_into_chunks


class Neo4jFeeder:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        self.driver.close()
    
    def process_json_file(self, file_path: str) -> Dict[str, Any]:
        """Traite un fichier JSON et l'insère dans Neo4j"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stats = {
                'nodes_created': 0,
                'relationships_created': 0,
                'errors': []
            }
            
            # Détection automatique du type de données
            if isinstance(data, list):
                for item in data:
                    result = self._process_entity(item)
                    stats['nodes_created'] += result.get('nodes', 0)
                    stats['relationships_created'] += result.get('rels', 0)
            elif isinstance(data, dict):
                result = self._process_entity(data)
                stats['nodes_created'] += result.get('nodes', 0)
                stats['relationships_created'] += result.get('rels', 0)
            
            return {
                'success': True,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_entity(self, entity: Dict[str, Any]) -> Dict[str, int]:
        """Traite une entité et crée les nœuds/relations correspondants"""
        stats = {'nodes': 0, 'rels': 0}
        
        with self.driver.session() as session:
            # Détection du type d'entité
            entity_type = entity.get('type', 'Entity')
            entity_id = entity.get('id', entity.get('name', ''))
            
            # Création du nœud principal
            properties = {k: v for k, v in entity.items() 
                         if not isinstance(v, (dict, list))}
            
            query = f"""
            MERGE (n:{entity_type} {{id: $id}})
            SET n += $properties
            RETURN n
            """
            
            session.run(query, id=entity_id, properties=properties)
            stats['nodes'] += 1
            
            # Traitement des relations
            for key, value in entity.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            rel_stats = self._create_relationship(
                                session, entity_type, entity_id, key, item
                            )
                            stats['rels'] += rel_stats
                elif isinstance(value, dict):
                    rel_stats = self._create_relationship(
                        session, entity_type, entity_id, key, value
                    )
                    stats['rels'] += rel_stats
        
        return stats
    
    def _create_relationship(self, session, from_type: str, from_id: str, 
                            rel_name: str, to_entity: Dict) -> int:
        """Crée une relation entre deux entités"""
        to_type = to_entity.get('type', rel_name.title())
        to_id = to_entity.get('id', to_entity.get('name', ''))
        
        to_properties = {k: v for k, v in to_entity.items() 
                        if not isinstance(v, (dict, list))}
        
        query = f"""
        MATCH (from:{from_type} {{id: $from_id}})
        MERGE (to:{to_type} {{id: $to_id}})
        SET to += $to_properties
        MERGE (from)-[r:{rel_name.upper()}]->(to)
        RETURN r
        """
        
        session.run(query, from_id=from_id, to_id=to_id, 
                   to_properties=to_properties)
        return 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la base Neo4j"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (n)
            RETURN count(n) as total_nodes,
                   count(distinct labels(n)) as node_types
            """)
            record = result.single()
            
            rel_result = session.run("""
            MATCH ()-[r]->()
            RETURN count(r) as total_relationships
            """)
            rel_record = rel_result.single()
            
            return {
                'total_nodes': record['total_nodes'],
                'node_types': record['node_types'],
                'total_relationships': rel_record['total_relationships']
            }


# Initialize components
qdrant = QdrantConnector()
rag = SimpleRAG()

# Initialize Neo4j (from environment variables)
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://xxxxx.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

neo4j_feeder = None
upload_history = []

try:
    if NEO4J_PASSWORD:
        neo4j_feeder = Neo4jFeeder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        print("✅ Neo4j connecté")
    else:
        print("⚠️ Neo4j non configuré (vérifier .env)")
except Exception as e:
    print(f"⚠️ Erreur connexion Neo4j: {e}")

# Create collection at startup
print("\n" + "="*70)
print("🔧 Initialisation GreenPower RAG System...")
print("="*70)
result = qdrant.create_collection()
print(result)


def upload_and_index(file) -> str:
    """Upload et indexation d'un fichier"""
    if file is None:
        return "⚠️ Aucun fichier sélectionné"
    
    try:
        # Load document
        file_path = file.name
        filename = Path(file_path).name
        
        print(f"\n📄 Traitement: {filename}")
        text = load_document(file_path)
        
        # Split into chunks
        documents = split_into_chunks(text, qdrant.text_splitter)
        
        # Index in Qdrant
        result = qdrant.index_documents(documents, filename)
        
        # Collection info
        info = qdrant.get_collection_info()
        total_docs = info.get('points_count', 0) if info.get('exists') else 0
        
        return f"""
## ✅ Fichier Indexé

**Fichier:** {filename}  
**Chunks créés:** {len(documents)}  
**Total documents en base:** {total_docs}

{result}

Vous pouvez maintenant poser des questions sur ce document !
"""
    
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def search_and_answer(question: str, top_k: int = 3) -> str:
    """Recherche et génération de réponse"""
    if not question or not question.strip():
        return "⚠️ Veuillez poser une question"
    
    try:
        return rag.search_and_answer(question, top_k)
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def reset_collection() -> str:
    """Reset la collection Qdrant"""
    result = qdrant.reset_collection()
    info = qdrant.get_collection_info()
    total_docs = info.get('points_count', 0) if info.get('exists') else 0
    
    return f"""
## 🔄 Collection Reset

{result}

**Documents restants:** {total_docs}

La base de données a été vidée. Vous pouvez uploader de nouveaux documents.
"""


# ============================================================================
# NEO4J FUNCTIONS
# ============================================================================

def upload_json_to_neo4j(files: List[Any]) -> str:
    """Traite les fichiers JSON uploadés vers Neo4j"""
    global upload_history
    
    if neo4j_feeder is None:
        return "❌ Neo4j non configuré. Vérifiez vos variables d'environnement (.env)"
    
    if not files:
        return "❌ Aucun fichier sélectionné"
    
    results = []
    for file in files:
        file_path = file.name
        result = neo4j_feeder.process_json_file(file_path)
        
        if result['success']:
            stats = result['stats']
            message = f"✅ **{os.path.basename(file_path)}**\n"
            message += f"   - Nœuds créés: {stats['nodes_created']}\n"
            message += f"   - Relations créées: {stats['relationships_created']}\n"
            message += f"   - Timestamp: {result['timestamp']}\n"
            
            upload_history.append({
                'file': os.path.basename(file_path),
                'timestamp': result['timestamp'],
                'stats': stats
            })
        else:
            message = f"❌ **{os.path.basename(file_path)}**\n"
            message += f"   - Erreur: {result['error']}\n"
        
        results.append(message)
    
    return "\n".join(results)


def get_neo4j_stats() -> str:
    """Affiche les statistiques de la base Neo4j"""
    if neo4j_feeder is None:
        return "❌ Neo4j non configuré"
    
    try:
        stats = neo4j_feeder.get_stats()
        return f"""
### 📊 Statistiques Neo4j

- **Nœuds totaux**: {stats['total_nodes']:,}
- **Types de nœuds**: {stats['node_types']}
- **Relations totales**: {stats['total_relationships']:,}

*Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
        """
    except Exception as e:
        return f"❌ Erreur lors de la récupération des stats: {str(e)}"


def get_upload_history() -> str:
    """Affiche l'historique des uploads Neo4j"""
    if not upload_history:
        return "📝 Aucun upload enregistré"
    
    history_text = "### 📜 Historique des uploads Neo4j\n\n"
    for idx, upload in enumerate(reversed(upload_history[-10:]), 1):
        history_text += f"{idx}. **{upload['file']}** ({upload['timestamp']})\n"
        history_text += f"   - Nœuds: {upload['stats']['nodes_created']}, "
        history_text += f"Relations: {upload['stats']['relationships_created']}\n\n"
    
    return history_text


# ============================================================================
# GRADIO INTERFACE
# ============================================================================

with gr.Blocks(
    title="GreenPower RAG System",
    theme=gr.themes.Soft()
) as demo:
    
    gr.Markdown(
        """
        # 🌞 GreenPower RAG System - Phase 02
        
        ## Vector RAG avec Qdrant + Mistral LLM + Neo4j GraphRAG
        
        ### Fonctionnalités:
        - 📤 Upload documents (PDF, DOCX, TXT, JSON, CSV)
        - 🔍 Recherche vectorielle intelligente
        - 🤖 Réponses générées par Mistral
        - 🔒 Filtrage automatique des données privées
        - 📅 Versioning hybride (stable vs temporel)
        - 🕸️ **Neo4j Graph Database** pour multi-hop queries
        """
    )
    
    with gr.Tab("📤 Upload Documents"):
        gr.Markdown(
            """
            ### Instructions:
            1. Sélectionnez un fichier à uploader
            2. Le système va automatiquement:
               - Extraire le texte
               - Découper en chunks
               - Détecter type de données (stable vs temporel)
               - Créer les embeddings
               - Indexer dans Qdrant
            
            **Formats supportés:** PDF, DOCX, TXT, JSON, CSV
            """
        )
        
        with gr.Row():
            file_input = gr.File(
                label="📁 Sélectionnez un fichier",
                file_types=[".pdf", ".docx", ".doc", ".txt", ".json", ".csv"]
            )
        
        upload_btn = gr.Button("📤 Upload et Indexer", variant="primary")
        upload_output = gr.Markdown(label="Résultat")
        
        upload_btn.click(
            upload_and_index,
            inputs=file_input,
            outputs=upload_output
        )
        
        gr.Markdown("---")
        reset_btn = gr.Button("🗑️ Reset Collection", variant="stop")
        reset_output = gr.Markdown()
        
        reset_btn.click(
            reset_collection,
            outputs=reset_output
        )
    
    with gr.Tab("🔍 Recherche & Questions"):
        gr.Markdown(
            """
            ### Posez vos questions sur les documents uploadés
            
            Le système va:
            1. 🔍 Chercher les chunks les plus pertinents
            2. 🔒 Filtrer les données privées (`private_*`)
            3. 🤖 Générer une réponse avec Mistral
            4. 📚 Citer les sources et versions
            
            ⚠️ Si tous les chunks contiennent `private_*` → **"Désolé, donnée confidentielle"**
            """
        )
        
        question_input = gr.Textbox(
            label="❓ Votre question",
            placeholder="Ex: Quels sont les prix actuels? Quelle est notre politique RH?",
            lines=3
        )
        
        top_k_slider = gr.Slider(
            minimum=1,
            maximum=10,
            value=3,
            step=1,
            label="🎯 Nombre de chunks à récupérer",
            info="Plus de chunks = plus de contexte (mais plus lent)"
        )
        
        ask_btn = gr.Button("🤔 Obtenir la Réponse", variant="primary")
        
        answer_output = gr.Markdown(
            label="💡 Réponse",
            value="*La réponse apparaîtra ici...*"
        )
        
        ask_btn.click(
            search_and_answer,
            inputs=[question_input, top_k_slider],
            outputs=answer_output
        )
        
        gr.Examples(
            examples=[
                ["Quels sont les prix actuels?", 3],
                ["Quelle est notre politique de congés?", 3],
                ["Montrez-moi l'évolution des stocks", 5],
                ["Quels sont les objectifs 2025?", 3],
            ],
            inputs=[question_input, top_k_slider],
        )
    
    with gr.Tab("🕸️ Neo4j Feeding"):
        gr.Markdown(
            """
            ### Alimenter la base de connaissances Neo4j
            
            Glissez-déposez vos fichiers JSON pour enrichir le graphe de connaissances.
            
            **Format attendu**: JSON avec structure d'entités (type, id, propriétés, relations)
            
            **Exemple de structure:**
```json
            {
              "type": "Product",
              "id": "solar-panel-500w",
              "name": "SolarMax 500W",
              "category": "Solar Panels",
              "price": 599.99,
              "specifications": [
                {
                  "type": "Specification",
                  "id": "power-output",
                  "name": "Power Output",
                  "value": "500W"
                }
              ]
            }
```
            """
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                neo4j_file_upload = gr.File(
                    label="📁 Fichiers JSON pour Neo4j",
                    file_count="multiple",
                    file_types=[".json"]
                )
                neo4j_upload_btn = gr.Button("⬆️ Uploader vers Neo4j", variant="primary")
                neo4j_upload_result = gr.Markdown(label="Résultat")
            
            with gr.Column(scale=1):
                neo4j_stats_btn = gr.Button("📊 Rafraîchir Stats")
                neo4j_stats_output = gr.Markdown()
        
        gr.Markdown("---")
        neo4j_history_output = gr.Markdown()
        
        # Connexions
        neo4j_upload_btn.click(
            fn=upload_json_to_neo4j,
            inputs=neo4j_file_upload,
            outputs=neo4j_upload_result
        ).then(
            fn=get_neo4j_stats,
            outputs=neo4j_stats_output
        ).then(
            fn=get_upload_history,
            outputs=neo4j_history_output
        )
        
        neo4j_stats_btn.click(
            fn=get_neo4j_stats,
            outputs=neo4j_stats_output
        )
    
    with gr.Tab("ℹ️ Info"):
        gr.Markdown(
            f"""
            ### 🔧 Configuration Technique
            
            **Vector DB:**
            - Platform: Qdrant ({QDRANT_URL})
            - Embeddings: {EMBEDDING_MODEL}
            - Collection: {COLLECTION_NAME}
            - Chunk size: {CHUNK_SIZE} caractères
            - Overlap: {CHUNK_OVERLAP} caractères
            
            **Graph DB:**
            - Platform: Neo4j Aurora
            - Status: {'✅ Connecté' if neo4j_feeder else '❌ Non configuré'}
            
            **LLM:**
            - Model: Mistral Small
            
            **Privacy:**
            - 🔒 Pattern privé: `{PRIVATE_PATTERN.pattern}`
            - 📅 Mots-clés temporels: {len(TEMPORAL_KEYWORDS)} patterns
            
            ### 📅 Système de Versioning Hybride
            
            **Problème résolu:**
            - Certaines données changent souvent (prix, stocks) → besoin d'historique
            - D'autres sont stables (politiques, procédures) → pas besoin d'historique
            - Re-upload d'un fichier : faut-il écraser ou garder les 2 versions ?
            
            **Solution:**
            
            1️⃣ **Détection automatique du type de données**
```python
            # Analyse filename + contenu
            is_temporal = any(keyword in text for keyword in [
                'prix', 'salaire', 'stock', 'budget', 'kpi', 'vente'...
            ])
```
            
            2️⃣ **ID intelligent basé sur le type**
```python
            # Données STABLES (écrasement)
            ID = "politique_rh.pdf_5"  # Toujours le même ID
            → Re-upload écrase l'ancien chunk
            
            # Données TEMPORELLES (historique)
            ID = "prix_2025.csv_2025-01-20_143022_5"  # ID unique avec timestamp
            → Re-upload crée un nouveau chunk, garde l'ancien
```
            
            ### 🔒 Système de Confidentialité
            
            **Filtrage par contenu:**
            - Regex: `/private_\\w+/` (case insensitive)
            - Appliqué APRÈS la recherche vectorielle
            - Chunks avec `private_xxx` → automatiquement rejetés
            - Message transparent si données filtrées
            
            **Patterns détectés:**
            - `private_client_001` ✅
            - `Private_Salary_Data` ✅
            - `PRIVATE_PROJECT_X` ✅
            
            ### 🕸️ Neo4j GraphRAG
            
            **Avantages du graphe:**
            - Multi-hop queries (traversée de relations)
            - Contexte sémantique enrichi
            - Relations ontologiques explicites
            - Meilleur pour questions complexes multi-domaines
            
            ### 🚀 Phase 03 Preview
            
            La prochaine phase ajoutera:
            - **Routing intelligent** Qdrant/Neo4j
            - **HybridRetriever** pour choisir automatiquement
            - **Enrichissement contextuel** avec relations graphe
            
            ### 📝 Notes
            
            - 📊 Les chunks temporels incluent version/timestamp dans réponse
            - 🎯 Recherche priorise naturellement versions récentes
            - 🗑️ "Reset Collection" vide complètement Qdrant
            - 💾 Mode `:memory:` ne persiste pas entre redémarrages
            - 🔄 Production: utiliser Qdrant cloud avec persistence
            """
        )

# ============================================================================
# LAUNCH
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 Lancement de l'interface Gradio...")
    print("="*70)
    
    demo.launch(
        server_name=GRADIO_SERVER_NAME,
        server_port=GRADIO_SERVER_PORT,
        share=GRADIO_SHARE,
        show_error=True
    )