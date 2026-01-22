import re
from typing import List, Tuple, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import GROQ_API_KEY, GROQ_MODEL
from neo4j_connect import GraphRAG
from qdrant_connect import QdrantConnector
from document_utils import load_document, split_into_chunks

class HybridRetriever:
    """Core RAG logic with routing and knowledge graph."""
    
    def __init__(self, use_neo4j: bool = True):
        """
        Initialize the hybrid retriever.
        
        Args:
            use_neo4j: Enable Neo4J knowledge graph (default: True)
        """
        self.use_neo4j = use_neo4j
        
        if not GROQ_API_KEY or "your_groq_api_key" in GROQ_API_KEY:
            raise ValueError("Please set a valid GROQ_API_KEY in your .env file")
            
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY, 
            model_name=GROQ_MODEL,
            temperature=0
        )
        
        # Initialize connectors
        self.qdrant = QdrantConnector()
        self.retriever = self.qdrant.get_retriever()
        
        # Always try to initialize GraphRAG when use_neo4j is True
        self.graph_rag = None
        if self.use_neo4j:
            self.graph_rag = GraphRAG(llm=self.llm)
            if self.graph_rag.is_available():
                print("✅ Neo4J GraphRAG enabled - entities will be extracted automatically")
            else:
                print("⚠️ Neo4J not connected - graph features disabled")

        # Routing patterns
        self.patterns = {
            'qdrant': [
                r'what is', r'define', r'price', r'prix', r'cost', r'tarif', 
                r'spec', r'feature', r'combien', r'c\'est quoi'
            ],
            'neo4j': [
                r'related', r'history', r'evolution', r'connection', r'link',
                r'historique', r'lien', r'impact'
            ]
        }
        
        # Contextualization prompt for conversational memory
        self.contextualize_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query reformulation assistant. Your job is to rewrite the user's question 
so that it is self-contained and can be understood without the conversation history.

Rules:
- Resolve all pronouns (it, this, that, its, their, sa, son, ce, cette, etc.)
- Include relevant context from the history
- Keep the reformulated question concise but complete
- If the question is already self-contained, return it as-is
- Output ONLY the reformulated question, nothing else
- Preserve the original language (French/English)

Examples:
History: "User: What is the price of SolarMax 500?"
Current: "And what about its warranty?"
Reformulated: "What is the warranty of SolarMax 500?"

History: "User: Tell me about GreenPower panels"
Current: "How much do they cost?"
Reformulated: "How much do GreenPower panels cost?"
"""),
            ("human", """Conversation history:
{history}

Current question: {question}

Reformulated question:""")
        ])

    def contextualize_query(self, query: str, chat_history: List[dict] = None) -> str:
        """
        Reformulate a query to be self-contained using conversation history.
        
        Args:
            query: The current user question
            chat_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            
        Returns:
            Reformulated query that is self-contained
        """
        # If no history or empty, return as-is
        if not chat_history or len(chat_history) == 0:
            return query
        
        # Check if query likely needs contextualization
        # (contains pronouns or is very short)
        needs_context_hints = [
            r'\b(it|its|this|that|these|those|they|them|their)\b',
            r'\b(il|elle|ils|elles|ce|cette|ces|son|sa|ses|le|la|les)\b',
            r'\b(and|et|also|aussi|same|même)\b',
        ]
        
        needs_context = any(re.search(pattern, query.lower()) for pattern in needs_context_hints)
        
        # Also check if query is very short (likely needs context)
        if len(query.split()) <= 4:
            needs_context = True
        
        if not needs_context:
            return query
        
        try:
            # Format history for the prompt (last 6 messages max)
            recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
            history_text = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:200]}" 
                for msg in recent_history
            ])
            
            # Call LLM to reformulate
            chain = self.contextualize_prompt | self.llm | StrOutputParser()
            reformulated = chain.invoke({
                "history": history_text,
                "question": query
            })
            
            reformulated = reformulated.strip()
            
            # Basic validation - if result is empty or too long, use original
            if not reformulated or len(reformulated) > len(query) * 3:
                return query
                
            print(f"🔄 Query contextualized: '{query}' → '{reformulated}'")
            return reformulated
            
        except Exception as e:
            print(f"⚠️ Contextualization failed: {e}")
            return query

    def route_query(self, query: str) -> str:
        """Determine which retrieval method to use."""
        query_lower = query.lower()
        
        for method, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return method
                    
        return 'hybrid'

    def retrieve(self, query: str) -> Tuple[List[Any], str, dict]:
        """Retrieve context based on routing."""
        import time
        route = self.route_query(query)
        chunks = []
        timings = {"qdrant": 0.0, "neo4j": 0.0}
        
        if route in ['qdrant', 'hybrid']:
            # Vector search
            start = time.time()
            chunks.extend(self.retriever.invoke(query))
            timings["qdrant"] = time.time() - start
            
        if route in ['neo4j', 'hybrid'] and self.use_neo4j and self.graph_rag and self.graph_rag.is_available():
            # Graph search (returning as text/string for now, wrapped in list for consistency)
            start = time.time()
            graph_context = self.graph_rag.query_graph(query)
            if graph_context:
                # We wrap it in a mock object or string to treat as a chunk
                from langchain_core.documents import Document
                chunks.append(Document(page_content=f"Generic Graph Context: {graph_context}", metadata={"source": "neo4j"}))
            timings["neo4j"] = time.time() - start

        return chunks, route, timings

    def generate_answer(self, query: str, context_chunks: List[Any], route: str) -> str:
        """Generate answer from context."""
        context_text = "\n\n".join([doc.page_content for doc in context_chunks])
        
        if not context_text:
            context_text = "No relevant information found."

        system_prompt = (
            f"You are an intelligent assistant using {route} retrieval strategy. "
            "Use the provided context to answer the user's question.\n\n"
            "Context:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"input": query, "context": context_text})

    def ingest(self, file_paths: List[str]) -> dict:
        """Ingest documents into enabled stores."""
        print(f"📥 Starting ingestion for {len(file_paths)} file(s): {file_paths}")
        
        docs = []
        for path in file_paths:
            loaded = load_document(path)
            print(f"  → Loaded {len(loaded)} document(s) from {path}")
            docs.extend(loaded)
        
        print(f"📚 Total documents loaded: {len(docs)}")
        
        if not docs:
            print("⚠️ No documents were loaded! Check file format or content.")
            return {
                "vector_chunks": 0,
                "graph_entities": 0,
                "graph_relations": 0,
                "error": "No documents could be loaded from the provided files"
            }
            
        chunks = split_into_chunks(docs)
        print(f"🔪 Split into {len(chunks)} chunks")
        
        vector_count = self.qdrant.index_documents(chunks)
        print(f"✅ Indexed {vector_count} chunks into Qdrant")
        
        result = {
            "vector_chunks": vector_count,
            "graph_entities": 0,
            "graph_relations": 0
        }
        
        if self.use_neo4j and self.graph_rag and self.graph_rag.is_available():
            print("Building Knowledge Graph...")
            stats = self.graph_rag.build_graph(docs)
            result.update({
                "graph_entities": stats["entities"],
                "graph_relations": stats["relations"]
            })
            
        return result

    def ingest_web(
        self, 
        urls: List[str], 
        follow_links: bool = False, 
        max_pages: int = 10
    ) -> dict:
        """
        Scrape web pages and ingest them into the RAG system.
        
        Args:
            urls: List of URLs to scrape
            follow_links: Whether to follow internal links on pages
            max_pages: Maximum number of pages to scrape
            
        Returns:
            Dictionary with ingestion statistics
        """
        from web_scraper import scrape_urls_for_rag
        from document_utils import split_into_chunks
        
        print(f"🌐 Starting web scraping for {len(urls)} URL(s)...")
        print(f"   Follow links: {follow_links}, Max pages: {max_pages}")
        
        try:
            # Scrape and convert to documents
            documents, images = scrape_urls_for_rag(
                urls=urls,
                follow_links=follow_links,
                max_pages=max_pages,
                include_images=True
            )
            
            if not documents:
                print("⚠️ No content was scraped from the provided URLs")
                return {
                    "pages_scraped": 0,
                    "vector_chunks": 0,
                    "graph_entities": 0,
                    "graph_relations": 0,
                    "images_found": 0,
                    "error": "No content could be extracted from the URLs"
                }
            
            print(f"📚 Scraped {len(documents)} documents")
            
            # Split into chunks for better retrieval
            chunks = split_into_chunks(documents)
            print(f"🔪 Split into {len(chunks)} chunks")
            
            # Index in Qdrant
            vector_count = self.qdrant.index_documents(chunks)
            print(f"✅ Indexed {vector_count} chunks into Qdrant")
            
            result = {
                "pages_scraped": len(set(doc.metadata.get('source', '') for doc in documents if doc.metadata.get('type') == 'web_page')),
                "vector_chunks": vector_count,
                "graph_entities": 0,
                "graph_relations": 0,
                "images_found": len(images),
            }
            
            # Build knowledge graph if enabled
            if self.use_neo4j and self.graph_rag and self.graph_rag.is_available():
                print("🕸️ Building Knowledge Graph from web content...")
                # Only use the main page documents for graph building (not image descriptions)
                main_docs = [doc for doc in documents if doc.metadata.get('type') == 'web_page']
                stats = self.graph_rag.build_graph(main_docs)
                result.update({
                    "graph_entities": stats["entities"],
                    "graph_relations": stats["relations"]
                })
                print(f"✅ Created {stats['entities']} entities and {stats['relations']} relations")
            
            return result
            
        except Exception as e:
            print(f"❌ Web scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "pages_scraped": 0,
                "vector_chunks": 0,
                "graph_entities": 0,
                "graph_relations": 0,
                "images_found": 0,
                "error": str(e)
            }
