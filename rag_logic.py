import os
from typing import List
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

load_dotenv()

class HybridRAG:
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
            except Exception as e:
                print(f"Warning: Failed to connect to Qdrant Cloud ({e}). Falling back to local memory.")
                self.client = None
        
        if not self.client:
            print("Using local Qdrant (in-memory).")
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

    def load_documents(self, file_paths: List[str]) -> List[Document]:
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
                print(f"Warning: Failed to load {file_path}: {e}")
        return documents

    def ingest(self, file_paths: List[str]):
        docs = self.load_documents(file_paths)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        self.vector_store.add_documents(splits)
        return len(splits)

    def query(self, question: str) -> str:
        """
        Query the RAG system without using create_retrieval_chain.
        This is a fully manual implementation to avoid version conflicts.
        """
        try:
            # Step 1: Retrieve relevant documents
            docs = self.retriever.invoke(question)
            
            # Step 2: Format documents into context string
            if docs:
                context = "\n\n".join(doc.page_content for doc in docs)
            else:
                context = "No relevant documents found."
            
            # Step 3: Build prompt with {context} as a variable (not embedded)
            # This avoids issues with documents containing { or }
            system_prompt = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer "
                "the question. If you don't know the answer, say that you "
                "don't know. Use three sentences maximum and keep the "
                "answer concise."
                "\n\nContext:\n{context}"
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])
            
            # Step 4: Build simple chain: prompt -> llm -> parse
            chain = prompt | self.llm | StrOutputParser()
            
            # Step 5: Invoke chain with context and input as separate variables
            answer = chain.invoke({"input": question, "context": context})
            return answer
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise RuntimeError(f"RAG Query failed: {e}\nDetails:\n{error_details}")


# Placeholder for Graph retrieval logic
class GraphRAG:
    def __init__(self):
        pass
    
    def build_graph(self, documents):
        pass
    
    def query_graph(self, question):
        pass
