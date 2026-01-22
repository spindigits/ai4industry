"""
RAG Features: HybridRetriever avec routing intelligent Qdrant/Neo4j

Phase 02: Pure Qdrant (vector RAG)
Phase 03: Hybrid Qdrant + Neo4j (GraphRAG)
"""
import re
from typing import List, Dict, Tuple
from langchain_mistralai import ChatMistralAI

from config import MISTRAL_API_KEY, MISTRAL_MODEL, MISTRAL_TEMPERATURE
from qdrant_connect import QdrantConnector
from neo4j_connect import Neo4jConnector


class HybridRetriever:
    """
    Retriever hybride avec routing intelligent
    
    Phase 02 (actuel): 100% Qdrant
    Phase 03 (à venir): Routing Qdrant/Neo4j basé sur type de query
    """
    
    def __init__(self, use_neo4j: bool = False):
        """
        Initialize HybridRetriever
        
        Args:
            use_neo4j: Activer Neo4j (Phase 03)
        """
        self.qdrant = QdrantConnector()
        self.neo4j = Neo4jConnector() if use_neo4j else None
        self.llm = ChatMistralAI(
            model=MISTRAL_MODEL,
            mistral_api_key=MISTRAL_API_KEY,
            temperature=MISTRAL_TEMPERATURE
        )
        
        # Patterns pour détecter multi-hop queries (Phase 03)
        self.multi_hop_patterns = [
            r'\b(related|connected|linked|associated)\b',
            r'\b(and|also|additionally)\b.*\?',
            r'\b(who|what).*\b(know|involved|work)\b',
            r'\b(customer|product|team).*\b(history|previous|past)\b',
            r'\b(path|connection|relationship)\b',
            r'\bévolution\b',
            r'\bcompare|compar',
        ]
        
        # Patterns pour queries simples (Phase 02 - Qdrant suffit)
        self.simple_patterns = [
            r'^what is\b',
            r'^define\b',
            r'^explain\b.*\b(product|service)\b',
            r'\b(price|prix|cost|tarif)\b',
            r'\b(spec|specification|caractéristique)\b',
        ]
    
    def route_query(self, query: str) -> str:
        """
        Détermine le backend à utiliser
        
        Returns:
            'qdrant' | 'neo4j' | 'hybrid'
        """
        # Phase 02: Toujours Qdrant
        if not self.neo4j:
            return 'qdrant'
        
        # Phase 03: Routing intelligent
        query_lower = query.lower()
        
        # Check multi-hop patterns
        is_multi_hop = any(
            re.search(pattern, query_lower, re.IGNORECASE) 
            for pattern in self.multi_hop_patterns
        )
        
        if is_multi_hop:
            return 'neo4j'
        
        # Check simple patterns
        is_simple = any(
            re.search(pattern, query_lower, re.IGNORECASE)
            for pattern in self.simple_patterns
        )
        
        if is_simple:
            return 'qdrant'
        
        # Default: hybrid (Qdrant first, Neo4j si contexte insuffisant)
        return 'hybrid'
    
    def retrieve(self, query: str, top_k: int = 3) -> Tuple[List[Dict], str]:
        """
        Retrieve avec routing intelligent
        
        Returns:
            (chunks, route_used)
        """
        route = self.route_query(query)
        
        if route == 'qdrant':
            chunks = self.qdrant.search(query, top_k)
            return chunks, 'qdrant'
        
        elif route == 'neo4j' and self.neo4j:
            # Phase 03: Pure Neo4j search
            chunks = self.neo4j.search_graph(query)
            return chunks, 'neo4j'
        
        elif route == 'hybrid' and self.neo4j:
            # Phase 03: Qdrant first, then Neo4j enrichment
            qdrant_chunks = self.qdrant.search(query, top_k)
            enriched_chunks = self.neo4j.enrich_context(qdrant_chunks)
            return enriched_chunks, 'hybrid'
        
        else:
            # Fallback: Qdrant
            chunks = self.qdrant.search(query, top_k)
            return chunks, 'qdrant (fallback)'
    
    def generate_answer(self, query: str, chunks: List[Dict], route_used: str) -> str:
        """
        Génère une réponse basée sur les chunks récupérés
        
        Args:
            query: Question de l'utilisateur
            chunks: Chunks récupérés
            route_used: Route utilisée pour debug/traçabilité
            
        Returns:
            Réponse formatée en Markdown
        """
        # Filter private chunks
        filtered_chunks, filtered_count = self.qdrant.filter_private_chunks(chunks)
        
        # Si tous filtrés → message confidentiel
        if not filtered_chunks and chunks:
            return """
## 🔒 Données Confidentielles

Désolé, les informations pertinentes pour votre question contiennent des données marquées comme **privées** (`private_*`).

Pour des raisons de sécurité, je ne peux pas partager ces informations.

**Suggestion:** Contactez votre responsable pour obtenir l'accès nécessaire.
"""
        
        # Si aucun résultat
        if not filtered_chunks:
            return f"""
## ❌ Aucun Résultat

Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question dans la base de données GreenPower.

**Route utilisée:** {route_used}

**Suggestions:**
1. Reformulez votre question
2. Vérifiez que les documents ont bien été uploadés
3. Essayez des termes plus généraux
"""
        
        # Construire le contexte
        context_parts = []
        for i, chunk in enumerate(filtered_chunks, 1):
            text = chunk['text']
            metadata = chunk['metadata']
            score = chunk.get('score', 0)
            
            source = metadata.get('source', 'unknown')
            timestamp = metadata.get('timestamp', '')
            is_temporal = metadata.get('is_temporal', False)
            
            version_info = f" (Version: {timestamp})" if is_temporal and timestamp else ""
            
            context_parts.append(
                f"[Source {i}: {source}{version_info} - Score: {score:.3f}]\n{text}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        # Prompt pour Mistral
        system_prompt = """Tu es un assistant expert pour GreenPower Solutions, une entreprise de générateurs solaires.

INSTRUCTIONS IMPORTANTES:
1. Réponds UNIQUEMENT basé sur le CONTEXTE fourni ci-dessous
2. Si le contexte ne contient pas l'info → dis-le clairement
3. Ne fabrique JAMAIS d'informations
4. Cite tes sources (Source 1, Source 2, etc.)
5. Si données temporelles → mentionne la version/date
6. Format Markdown avec sections claires

CONTEXTE:
{context}

QUESTION: {query}

RÉPONSE (en Markdown):"""
        
        prompt = system_prompt.format(context=context, query=query)
        
        try:
            response = self.llm.invoke(prompt)
            answer = response.content
            
            # Ajouter métadonnées de debug
            debug_info = f"\n\n---\n*Route: {route_used} | Chunks: {len(filtered_chunks)}/{len(chunks)}"
            if filtered_count > 0:
                debug_info += f" | Filtrés (private): {filtered_count}"
            debug_info += "*"
            
            return answer + debug_info
            
        except Exception as e:
            return f"""
## ❌ Erreur Génération Réponse

Une erreur s'est produite lors de la génération de la réponse:

```
{str(e)}
```

**Contexte récupéré:** {len(filtered_chunks)} chunks
**Route utilisée:** {route_used}
"""


class SimpleRAG:
    """
    RAG simple sans routing (Phase 02 actuel)
    Conservé pour compatibilité avec code existant
    """
    
    def __init__(self):
        self.retriever = HybridRetriever(use_neo4j=False)
    
    def search_and_answer(self, query: str, top_k: int = 3) -> str:
        """
        Recherche et génère une réponse (Phase 02)
        """
        chunks, route = self.retriever.retrieve(query, top_k)
        return self.retriever.generate_answer(query, chunks, route)
