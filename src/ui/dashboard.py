"""
Dashboard de métriques pour le système RAG Hybride
Affiche les statistiques de performance de Qdrant et Neo4j
"""

import time
import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime


class DashboardMetrics:
    """Collecte et affiche les métriques de performance du système"""

    def __init__(self, qdrant_client, neo4j_querier, vector_store):
        self.qdrant_client = qdrant_client
        self.neo4j_querier = neo4j_querier
        self.vector_store = vector_store

    def get_qdrant_metrics(self) -> Dict:
        """Récupère les métriques de Qdrant"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_name = "documents_rag"

            # Vérifier si la collection existe
            collection_exists = any(c.name == collection_name for c in collections.collections)

            if not collection_exists:
                return {
                    "total_collections": len(collections.collections),
                    "documents_count": 0,
                    "vectors_count": 0,
                    "collection_exists": False
                }

            # Récupérer les infos de la collection
            collection_info = self.qdrant_client.get_collection(collection_name)

            # Gérer le cas où vectors est un dict ou un objet direct
            vector_size = 0
            if hasattr(collection_info.config.params, 'vectors'):
                vectors = collection_info.config.params.vectors
                if isinstance(vectors, dict):
                    # Cas multi-vecteurs: prendre la taille du premier vecteur
                    vector_size = next(iter(vectors.values())).size if vectors else 0
                elif hasattr(vectors, 'size'):
                    # Cas vecteur unique
                    vector_size = vectors.size

            return {
                "total_collections": len(collections.collections),
                "documents_count": collection_info.points_count,
                "vectors_count": collection_info.points_count,
                "collection_exists": True,
                "vector_size": vector_size
            }
        except Exception as e:
            st.error(f"Erreur lors de la récupération des métriques Qdrant: {e}")
            return {"error": str(e)}

    def get_neo4j_metrics(self) -> Dict:
        """Récupère les métriques de Neo4j"""
        try:
            with self.neo4j_querier.driver.session() as session:
                # Compter les nœuds par type
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """)
                nodes_by_type = {record["label"]: record["count"] for record in result}

                # Compter les relations par type
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as rel_type, count(r) as count
                    ORDER BY count DESC
                """)
                relations_by_type = {record["rel_type"]: record["count"] for record in result}

                # Total
                total_nodes = sum(nodes_by_type.values())
                total_relations = sum(relations_by_type.values())

                return {
                    "total_nodes": total_nodes,
                    "total_relations": total_relations,
                    "nodes_by_type": nodes_by_type,
                    "relations_by_type": relations_by_type
                }
        except Exception as e:
            st.error(f"Erreur lors de la récupération des métriques Neo4j: {e}")
            return {"error": str(e)}

    def measure_qdrant_search_time(self, question: str, k: int = 3) -> Tuple[float, int]:
        """Mesure le temps de recherche Qdrant"""
        try:
            retriever = self.vector_store.as_retriever(search_kwargs={"k": k})

            start_time = time.time()
            results = retriever.invoke(question)
            end_time = time.time()

            return (end_time - start_time) * 1000, len(results)  # en ms
        except Exception as e:
            st.error(f"Erreur lors de la mesure Qdrant: {e}")
            return 0, 0

    def measure_neo4j_query_time(self, query_func, *args) -> Tuple[float, int]:
        """Mesure le temps d'exécution d'une requête Neo4j"""
        try:
            start_time = time.time()
            results = query_func(*args)
            end_time = time.time()

            return (end_time - start_time) * 1000, len(results)  # en ms
        except Exception as e:
            st.error(f"Erreur lors de la mesure Neo4j: {e}")
            return 0, 0


def render_dashboard(qdrant_client, neo4j_querier, vector_store):
    """Affiche le dashboard complet des métriques"""

    # Initialiser le dashboard
    dashboard = DashboardMetrics(qdrant_client, neo4j_querier, vector_store)

    # --- Nouveau Layout ---
    st.markdown("## 📊 Dashboard de Performance")

    # 2. Tabs principaux pour séparer les vues
    tab_overview, tab_qdrant, tab_neo4j = st.tabs(["👁️ Vue d'ensemble", "🔵 Détails Qdrant", "🟢 Détails Neo4j"])

    qdrant_metrics = dashboard.get_qdrant_metrics()
    neo4j_metrics = dashboard.get_neo4j_metrics()

    # --- TAB OVERVIEW ---
    with tab_overview:
        col_users1, col_users2 = st.columns(2)
        
        # Carte Qdrant
        with col_users1:
            st.subheader("Base Vectorielle")
            if "error" not in qdrant_metrics:
                st.info(f"✅ Opérationnel - {qdrant_metrics.get('documents_count', 0)} documents")
            else:
                st.error("❌ Erreur de connexion")
        
        # Carte Neo4j
        with col_users2:
            st.subheader("Base Graphique")
            if "error" not in neo4j_metrics:
                st.info(f"✅ Opérationnel - {neo4j_metrics.get('total_nodes', 0)} nœuds / {neo4j_metrics.get('total_relations', 0)} relations")
            else:
                st.error("❌ Erreur de connexion")

        # Carte Performance LLM
        st.subheader("Performance LLM")
        last_time = st.session_state.get("last_llm_time", None)
        if last_time is not None:
             st.metric("Dernier temps de réponse", f"{last_time / 1000:.2f} s")
        else:
             st.info("Aucune requête effectuée pour l'instant")

        st.markdown("### 🚀 Tests Rapides")
        col_test1, col_test2 = st.columns(2)
        with col_test1:
             if st.button("▶️ Test Latence Qdrant", use_container_width=True):
                 time_ms, count = dashboard.measure_qdrant_search_time("Test", k=1)
                 st.metric("Latence", f"{time_ms:.2f} ms", f"{count} results")

        with col_test2:
             if st.button("▶️ Test Latence Neo4j", use_container_width=True):
                  time_ms, count = dashboard.measure_neo4j_query_time(neo4j_querier.query_top_revenue_tradeshows, 1)
                  st.metric("Latence", f"{time_ms:.2f} ms", f"{count} results")

    # --- TAB QDRANT ---
    with tab_qdrant:
        st.markdown("### 📊 Statistiques Vectorielles")
        if "error" not in qdrant_metrics:
            c1, c2, c3 = st.columns(3)
            c1.metric("Collections", qdrant_metrics.get("total_collections"))
            c2.metric("Vecteurs", qdrant_metrics.get("vectors_count"))
            c3.metric("Dimension", qdrant_metrics.get("vector_size"))
            
            st.progress(min(100, qdrant_metrics.get("documents_count", 0)), text="Indexation relative")

            # Benchmark Qdrant
            with st.expander("🔬 Benchmark Avancé Qdrant", expanded=False):
                test_questions = ["Qu'est-ce que GreenPower?", "Prix des produits", "Événements festivals"]
                if st.button("▶️ Lancer Test Complet Qdrant", use_container_width=True):
                    with st.spinner("Performance test..."):
                        perf_data = []
                        for q in test_questions:
                            t, c = dashboard.measure_qdrant_search_time(q)
                            perf_data.append({"Question": q, "Temps (ms)": round(t, 2), "Résultats": c})
                        st.dataframe(pd.DataFrame(perf_data), use_container_width=True)

    # --- TAB NEO4J ---
    with tab_neo4j:
        st.markdown("### 🕸️ Structure du Graphe")
        if "error" not in neo4j_metrics:
            c1, c2 = st.columns(2)
            
            with c1:
                st.caption("Distribution des Nœuds")
                nodes_data = neo4j_metrics.get("nodes_by_type", {})
                if nodes_data:
                    st.bar_chart(nodes_data)
            
            with c2:
                st.caption("Distribution des Relations")
                rel_data = neo4j_metrics.get("relations_by_type", {})
                if rel_data:
                    st.bar_chart(rel_data)

            # Benchmark Neo4j
            with st.expander("🔬 Benchmark Avancé Neo4j", expanded=False):
                if st.button("▶️ Lancer Test Complet Neo4j", use_container_width=True):
                    with st.spinner("Performance test..."):
                        perf_data = []
                        # 1. Simple
                        t, c = dashboard.measure_neo4j_query_time(neo4j_querier.query_top_revenue_tradeshows, 5)
                        perf_data.append({"Type": "Simple (Top Salons)", "Temps (ms)": t, "Count": c})
                        # 2. Multi-hop
                        t, c = dashboard.measure_neo4j_query_time(neo4j_querier.query_events_with_products_sold_at_tradeshows)
                        perf_data.append({"Type": "Multi-hop (Products -> Events)", "Temps (ms)": t, "Count": c})
                        # 3. Aggregation
                        t, c = dashboard.measure_neo4j_query_time(neo4j_querier.query_tradeshows_sales_by_customer_type, "collectivites")
                        perf_data.append({"Type": "Aggregation (Sales)", "Temps (ms)": t, "Count": c})
                        
                        df_perf = pd.DataFrame(perf_data)
                        st.dataframe(df_perf, use_container_width=True)
                        st.bar_chart(df_perf.set_index("Type")["Temps (ms)"])
