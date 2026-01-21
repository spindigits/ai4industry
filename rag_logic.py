import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Neo4j imports
from neo4j import GraphDatabase

load_dotenv()


class Neo4jConnection:
    """Manages Neo4j database connection and operations."""
    
    def __init__(self, uri: str, user: str = None, password: str = None, 
                 client_id: str = None, client_secret: str = None):
        self.uri = uri
        self.user = user
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            # Try OAuth2 / Bearer token auth first (for Neo4j Aura with API credentials)
            if self.client_id and self.client_secret:
                from neo4j import bearer_auth
                # For Neo4j Aura, client credentials can be used as bearer auth
                # The client_secret is typically used as the bearer token
                auth = bearer_auth(self.client_secret)
                self.driver = GraphDatabase.driver(self.uri, auth=auth)
            else:
                # Standard basic authentication
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            # Test connection
            self.driver.verify_connectivity()
            print(f"✅ Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"⚠️ Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self.driver is not None
    
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """Execute a Cypher query and return results."""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            print(f"Query error: {e}")
            return []
    
    def create_node(self, label: str, properties: Dict) -> Optional[int]:
        """Create a node with given label and properties."""
        query = f"CREATE (n:{label} $props) RETURN id(n) as node_id"
        result = self.execute_query(query, {"props": properties})
        return result[0]["node_id"] if result else None
    
    def create_relationship(self, from_id: int, to_id: int, rel_type: str, properties: Dict = None):
        """Create a relationship between two nodes."""
        query = """
        MATCH (a), (b)
        WHERE id(a) = $from_id AND id(b) = $to_id
        CREATE (a)-[r:%s $props]->(b)
        RETURN type(r) as rel_type
        """ % rel_type
        return self.execute_query(query, {"from_id": from_id, "to_id": to_id, "props": properties or {}})
    
    def search_nodes(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Search nodes by keyword in their properties."""
        query = """
        MATCH (n)
        WHERE any(key IN keys(n) WHERE toString(n[key]) CONTAINS $keyword)
        RETURN n, labels(n) as labels, id(n) as node_id
        LIMIT $limit
        """
        return self.execute_query(query, {"keyword": keyword, "limit": limit})
    
    def get_node_relationships(self, node_id: int, depth: int = 2) -> List[Dict]:
        """Get all relationships for a node up to specified depth."""
        query = """
        MATCH path = (n)-[*1..%d]-(m)
        WHERE id(n) = $node_id
        RETURN 
            [rel in relationships(path) | {type: type(rel), props: properties(rel)}] as relationships,
            [node in nodes(path) | {id: id(node), labels: labels(node), props: properties(node)}] as nodes
        LIMIT 50
        """ % depth
        return self.execute_query(query, {"node_id": node_id})
    
    def clear_graph(self):
        """Clear all nodes and relationships (use with caution!)."""
        self.execute_query("MATCH (n) DETACH DELETE n")


class GraphRAG:
    """Graph-based RAG using Neo4j for knowledge graph storage and retrieval."""
    
    def __init__(self, llm=None):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        self.neo4j_client_id = os.getenv("NEO4J_CLIENT_ID", "")
        self.neo4j_client_secret = os.getenv("NEO4J_CLIENT_SECRET", "")
        
        self.neo4j = None
        self.llm = llm
        self._connect_neo4j()
    
    def _connect_neo4j(self):
        """Initialize Neo4j connection."""
        # Check if OAuth2 credentials are provided
        has_oauth = (self.neo4j_client_id and self.neo4j_client_secret and 
                     "your_client" not in self.neo4j_client_id)
        # Check if basic auth credentials are provided
        has_basic_auth = (self.neo4j_password and 
                          "your_neo4j_password" not in self.neo4j_password)
        
        if has_oauth or has_basic_auth:
            try:
                self.neo4j = Neo4jConnection(
                    uri=self.neo4j_uri,
                    user=self.neo4j_user if has_basic_auth else None,
                    password=self.neo4j_password if has_basic_auth else None,
                    client_id=self.neo4j_client_id if has_oauth else None,
                    client_secret=self.neo4j_client_secret if has_oauth else None
                )
                if not self.neo4j.is_connected():
                    self.neo4j = None
            except Exception as e:
                print(f"⚠️ Neo4j initialization failed: {e}")
                self.neo4j = None
        else:
            print("⚠️ Neo4j credentials not configured. GraphRAG will be disabled.")
    
    def is_available(self) -> bool:
        """Check if GraphRAG is available."""
        return self.neo4j is not None and self.neo4j.is_connected()
    
    def extract_entities_and_relations(self, text: str) -> Dict[str, Any]:
        """Use LLM to extract entities and relationships from text."""
        if not self.llm:
            return {"entities": [], "relations": []}
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting entities and relationships from text.
Extract entities (people, organizations, concepts, locations, etc.) and relationships between them.

Return your response as a valid JSON object with this structure:
{
    "entities": [
        {"name": "entity name", "type": "PERSON|ORGANIZATION|CONCEPT|LOCATION|PRODUCT|EVENT", "description": "brief description"}
    ],
    "relations": [
        {"from": "entity1 name", "to": "entity2 name", "type": "RELATIONSHIP_TYPE", "description": "brief description"}
    ]
}

Rules:
- Entity names should be normalized (proper capitalization, full names)
- Relationship types should be uppercase with underscores (e.g., WORKS_FOR, LOCATED_IN, RELATED_TO)
- Only extract clear, factual information
- Return ONLY the JSON, no additional text"""),
            ("human", "Extract entities and relationships from this text:\n\n{text}")
        ])
        
        try:
            chain = extraction_prompt | self.llm | StrOutputParser()
            response = chain.invoke({"text": text[:4000]})  # Limit text length
            
            # Parse JSON response
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return {"entities": [], "relations": []}
        except Exception as e:
            print(f"Entity extraction error: {e}")
            return {"entities": [], "relations": []}
    
    def build_graph(self, documents: List[Document]) -> Dict[str, int]:
        """Build knowledge graph from documents."""
        if not self.is_available():
            return {"entities": 0, "relations": 0}
        
        total_entities = 0
        total_relations = 0
        entity_id_map = {}  # Maps entity names to Neo4j node IDs
        
        for doc in documents:
            # Extract entities and relations
            extracted = self.extract_entities_and_relations(doc.page_content)
            
            # Create entity nodes
            for entity in extracted.get("entities", []):
                entity_name = entity.get("name", "").strip()
                if not entity_name:
                    continue
                    
                # Check if entity already exists
                if entity_name.lower() not in entity_id_map:
                    node_id = self.neo4j.create_node(
                        label=entity.get("type", "ENTITY"),
                        properties={
                            "name": entity_name,
                            "description": entity.get("description", ""),
                            "source": doc.metadata.get("source", "unknown")
                        }
                    )
                    if node_id is not None:
                        entity_id_map[entity_name.lower()] = node_id
                        total_entities += 1
            
            # Create relationships
            for relation in extracted.get("relations", []):
                from_name = relation.get("from", "").strip().lower()
                to_name = relation.get("to", "").strip().lower()
                rel_type = relation.get("type", "RELATED_TO").upper().replace(" ", "_")
                
                if from_name in entity_id_map and to_name in entity_id_map:
                    self.neo4j.create_relationship(
                        from_id=entity_id_map[from_name],
                        to_id=entity_id_map[to_name],
                        rel_type=rel_type,
                        properties={"description": relation.get("description", "")}
                    )
                    total_relations += 1
        
        return {"entities": total_entities, "relations": total_relations}
    
    def query_graph(self, question: str) -> str:
        """Query the knowledge graph based on the question."""
        if not self.is_available():
            return ""
        
        # Extract key terms from question for graph search
        keywords = self._extract_keywords(question)
        
        graph_context = []
        seen_nodes = set()
        
        for keyword in keywords:
            # Search for matching nodes
            nodes = self.neo4j.search_nodes(keyword, limit=5)
            
            for node_data in nodes:
                node_id = node_data.get("node_id")
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                
                # Get node properties
                node_props = node_data.get("n", {})
                labels = node_data.get("labels", [])
                
                node_info = f"[{'/'.join(labels)}] {node_props.get('name', 'Unknown')}"
                if node_props.get("description"):
                    node_info += f": {node_props.get('description')}"
                graph_context.append(node_info)
                
                # Get relationships
                relationships = self.neo4j.get_node_relationships(node_id, depth=1)
                for rel_data in relationships[:5]:  # Limit relationships
                    for rel in rel_data.get("relationships", []):
                        rel_info = f"  -> {rel.get('type', 'RELATED')}"
                        if rel.get("props", {}).get("description"):
                            rel_info += f": {rel['props']['description']}"
                        graph_context.append(rel_info)
        
        if graph_context:
            return "Knowledge Graph Context:\n" + "\n".join(graph_context[:20])  # Limit context size
        return ""
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for graph search."""
        # Simple keyword extraction - remove common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'who', 
                      'where', 'when', 'why', 'how', 'which', 'that', 'this', 'these',
                      'those', 'it', 'its', 'in', 'on', 'at', 'to', 'for', 'of', 'and',
                      'or', 'but', 'with', 'from', 'by', 'about', 'as', 'into', 'like',
                      'through', 'after', 'over', 'between', 'out', 'against', 'during',
                      'without', 'before', 'under', 'around', 'among', 'do', 'does', 'did',
                      'can', 'could', 'would', 'should', 'may', 'might', 'must', 'shall'}
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Return unique keywords, maintaining order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to top 10 keywords
    
    def get_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the knowledge graph."""
        if not self.is_available():
            return {"nodes": 0, "relationships": 0}
        
        node_count = self.neo4j.execute_query("MATCH (n) RETURN count(n) as count")
        rel_count = self.neo4j.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        
        return {
            "nodes": node_count[0]["count"] if node_count else 0,
            "relationships": rel_count[0]["count"] if rel_count else 0
        }


class HybridRAG:
    """Hybrid RAG combining Vector Search (Qdrant) and Graph Search (Neo4j)."""
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not self.groq_api_key or "your_groq_api_key" in self.groq_api_key:
            raise ValueError("Please set a valid GROQ_API_KEY in your .env file")
            
        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key, 
            model_name=self.groq_model,
            temperature=0
        )
        
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize Qdrant Client
        is_qdrant_configured = (
            self.qdrant_url 
            and self.qdrant_api_key 
            and "your_qdrant_url" not in self.qdrant_url
        )
        
        self.client = None
        if is_qdrant_configured:
            try:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
                self.client.get_collections()
                print("✅ Connected to Qdrant Cloud")
            except Exception as e:
                print(f"⚠️ Failed to connect to Qdrant Cloud ({e}). Falling back to local memory.")
                self.client = None
        
        if not self.client:
            print("📦 Using local Qdrant (in-memory).")
            self.client = QdrantClient(location=":memory:")
            
        self.collection_name = "hybrid_rag_collection"
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )
        
        # Store retriever for later use
        self.retriever = self.vector_store.as_retriever()
        
        # Initialize GraphRAG with shared LLM
        self.graph_rag = GraphRAG(llm=self.llm)

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from various file formats."""
        documents = []
        for file_path in file_paths:
            ext = file_path.split('.')[-1].lower()
            try:
                if ext == 'pdf':
                    loader = PyPDFLoader(file_path)
                elif ext == 'txt':
                    loader = TextLoader(file_path)
                elif ext == 'csv':
                    loader = CSVLoader(file_path)
                elif ext == 'json':
                    loader = JSONLoader(file_path, jq_schema='.', text_content=False)
                else:
                    continue
                documents.extend(loader.load())
            except Exception as e:
                print(f"⚠️ Failed to load {file_path}: {e}")
        return documents

    def ingest(self, file_paths: List[str], build_graph: bool = True) -> Dict[str, Any]:
        """Ingest documents into both vector store and knowledge graph."""
        docs = self.load_documents(file_paths)
        
        # Vector store ingestion
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        self.vector_store.add_documents(splits)
        
        result = {
            "vector_chunks": len(splits),
            "graph_entities": 0,
            "graph_relations": 0
        }
        
        # Knowledge graph construction (if enabled and available)
        if build_graph and self.graph_rag.is_available():
            graph_stats = self.graph_rag.build_graph(docs)
            result["graph_entities"] = graph_stats["entities"]
            result["graph_relations"] = graph_stats["relations"]
        
        return result

    def query(self, question: str, use_graph: bool = True) -> str:
        """
        Query the Hybrid RAG system combining vector and graph retrieval.
        """
        try:
            # Step 1: Vector retrieval
            docs = self.retriever.invoke(question)
            
            if docs:
                vector_context = "\n\n".join(doc.page_content for doc in docs)
            else:
                vector_context = "No relevant documents found in vector store."
            
            # Step 2: Graph retrieval (if enabled)
            graph_context = ""
            if use_graph and self.graph_rag.is_available():
                graph_context = self.graph_rag.query_graph(question)
            
            # Step 3: Combine contexts
            if graph_context:
                combined_context = f"## Vector Search Results:\n{vector_context}\n\n## {graph_context}"
            else:
                combined_context = vector_context
            
            # Step 4: Build prompt
            system_prompt = (
                "You are an intelligent assistant for question-answering tasks. "
                "You have access to two types of information:\n"
                "1. Vector Search Results: Relevant text passages from documents\n"
                "2. Knowledge Graph Context: Entities and relationships extracted from documents\n\n"
                "Use both sources to provide comprehensive, accurate answers. "
                "If the information is insufficient, acknowledge what you don't know. "
                "Be concise but thorough."
                "\n\nContext:\n{context}"
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])
            
            # Step 5: Generate response
            chain = prompt | self.llm | StrOutputParser()
            answer = chain.invoke({"input": question, "context": combined_context})
            
            return answer
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise RuntimeError(f"RAG Query failed: {e}\nDetails:\n{error_details}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of all RAG components."""
        status = {
            "vector_store": "connected",
            "graph_store": "connected" if self.graph_rag.is_available() else "disconnected",
            "llm": "connected"
        }
        
        if self.graph_rag.is_available():
            status["graph_stats"] = self.graph_rag.get_graph_stats()
        
        return status

