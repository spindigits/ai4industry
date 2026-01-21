from typing import Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import GROQ_API_KEY, GROQ_MODEL
from neo4j_connect import GraphRAG
from qdrant_connect import QdrantConnector
from document_utils import load_document, split_into_chunks

class HybridRetriever:
    """Core RAG logic combining functionality from Qdrant and Neo4j."""
    
    def __init__(self):
        if not GROQ_API_KEY or "your_groq_api_key" in GROQ_API_KEY:
            raise ValueError("Please set a valid GROQ_API_KEY in your .env file")
            
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY, 
            model_name=GROQ_MODEL,
            temperature=0
        )
        
        # Initialize connectors
        self.qdrant = QdrantConnector()
        self.graph_rag = GraphRAG(llm=self.llm)
        self.retriever = self.qdrant.get_retriever()

    def ingest(self, file_paths: List[str], build_graph: bool = True) -> Dict[str, Any]:
        """Ingest documents into both vector store and knowledge graph."""
        docs = []
        for path in file_paths:
            docs.extend(load_document(path))
            
        chunks = split_into_chunks(docs)
        vector_count = self.qdrant.index_documents(chunks)
        
        result = {
            "vector_chunks": vector_count,
            "graph_entities": 0,
            "graph_relations": 0
        }
        
        if build_graph and self.graph_rag.is_available():
            print("Building Knowledge Graph... This may take a moment.")
            graph_stats = self.graph_rag.build_graph(docs)
            result["graph_entities"] = graph_stats["entities"]
            result["graph_relations"] = graph_stats["relations"]
            
        return result

    def query(self, question: str, use_graph: bool = True) -> str:
        """Query using hybrid retrieval."""
        try:
            # Vector retrieval
            docs = self.retriever.invoke(question)
            vector_context = "\n\n".join(doc.page_content for doc in docs) if docs else "No relevant documents found in vector store."
            
            # Graph retrieval
            graph_context = ""
            if use_graph and self.graph_rag.is_available():
                graph_context = self.graph_rag.query_graph(question)
            
            # Combine
            combined_context = f"## Vector Search Results:\n{vector_context}"
            if graph_context:
                combined_context += f"\n\n## {graph_context}"
            
            # Generate answer
            system_prompt = (
                "You are an intelligent assistant. Use the provided context to answer the user's question. "
                "If the information is insufficient, acknowledge it. Be concise.\n\n"
                "Context:\n{context}"
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"input": question, "context": combined_context})
            
        except Exception as e:
            return f"Error processing query: {e}"
