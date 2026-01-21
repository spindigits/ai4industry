import os
import re
import json
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, bearer_auth
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, 
    NEO4J_CLIENT_ID, NEO4J_CLIENT_SECRET
)

class Neo4jConnection:
    """Manages Neo4j database connection and operations."""
    
    def __init__(self):
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            # Try OAuth2 / Bearer token auth first
            if NEO4J_CLIENT_ID and NEO4J_CLIENT_SECRET:
                auth = bearer_auth(NEO4J_CLIENT_SECRET)
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
            else:
                # Standard basic authentication
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            
            # Test connection
            self.driver.verify_connectivity()
            print(f"✅ Connected to Neo4j at {NEO4J_URI}")
        except Exception as e:
            print(f"⚠️ Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
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

class GraphRAG:
    """Graph-based RAG using Neo4j for knowledge graph storage and retrieval."""
    
    def __init__(self, llm=None):
        self.neo4j = Neo4jConnection()
        self.llm = llm
        
        if not self.neo4j.is_connected():
            print("⚠️ Neo4j not connected. GraphRAG will be disabled.")
    
    def is_available(self) -> bool:
        return self.neo4j.is_connected()
    
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
            
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
            
            return json.loads(cleaned)
        except Exception as e:
            print(f"Entity extraction error: {e}")
            return {"entities": [], "relations": []}
    
    def build_graph(self, documents: List[Document]) -> Dict[str, int]:
        """Build knowledge graph from documents."""
        if not self.is_available():
            return {"entities": 0, "relations": 0}
        
        total_entities = 0
        total_relations = 0
        entity_id_map = {}
        
        for doc in documents:
            extracted = self.extract_entities_and_relations(doc.page_content)
            
            # Create entity nodes
            for entity in extracted.get("entities", []):
                entity_name = entity.get("name", "").strip()
                if not entity_name: continue
                    
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
        
        keywords = self._extract_keywords(question)
        graph_context = []
        seen_nodes = set()
        
        for keyword in keywords:
            nodes = self.neo4j.search_nodes(keyword, limit=5)
            for node_data in nodes:
                node_id = node_data.get("node_id")
                if node_id in seen_nodes: continue
                seen_nodes.add(node_id)
                
                node_props = node_data.get("n", {})
                labels = node_data.get("labels", [])
                
                node_info = f"[{'/'.join(labels)}] {node_props.get('name', 'Unknown')}"
                if node_props.get("description"):
                    node_info += f": {node_props.get('description')}"
                graph_context.append(node_info)
                
                relationships = self.neo4j.get_node_relationships(node_id, depth=1)
                for rel_data in relationships[:5]:
                    for rel in rel_data.get("relationships", []):
                        rel_info = f"  -> {rel.get('type', 'RELATED')}"
                        if rel.get("props", {}).get("description"):
                            rel_info += f": {rel['props']['description']}"
                        graph_context.append(rel_info)
        
        if graph_context:
            return "Knowledge Graph Context:\n" + "\n".join(graph_context[:20])
        return ""
    
    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'who', 'what', 'where', 'when', 'why', 'how', 'which', 'that', 'this', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'with', 'from', 'by'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        unique_keywords = []
        for kw in keywords:
            if kw not in unique_keywords: unique_keywords.append(kw)
        return unique_keywords[:10]
