from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import CHUNK_SIZE, CHUNK_OVERLAP

def load_document(file_path: str) -> List[Document]:
    """Load a document based on its file extension."""
    ext = file_path.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            # Check for LlamaParse configuration
            from config import LLAMA_CLOUD_API_KEY
            if LLAMA_CLOUD_API_KEY:
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    from llama_parse import LlamaParse
                    
                    print("🦙 Using LlamaParse for PDF ingestion...")
                    parser = LlamaParse(
                        api_key=LLAMA_CLOUD_API_KEY,
                        result_type="markdown",
                        verbose=True,
                        language="en", # Optional: can me made configurable
                    )
                    llama_docs = parser.load_data(file_path)
                    
                    # Convert LlamaIndex docs to LangChain docs
                    langchain_docs = []
                    for doc in llama_docs:
                        langchain_docs.append(Document(
                            page_content=doc.text,
                            metadata=doc.metadata or {}
                        ))
                    return langchain_docs
                except Exception as e:
                    print(f"⚠️ LlamaParse failed, falling back to PyPDF: {e}")
                    loader = PyPDFLoader(file_path)
            else:
                loader = PyPDFLoader(file_path)

        elif ext == 'txt':
            loader = TextLoader(file_path, encoding='utf-8')
        elif ext == 'csv':
            loader = CSVLoader(file_path)
        elif ext == 'json':
            loader = JSONLoader(file_path, jq_schema='.', text_content=False)
        else:
            print(f"⚠️ Unsupported format: {ext}")
            return []
        
        return loader.load()
    except Exception as e:
        print(f"⚠️ Failed to load {file_path}: {e}")
        return []

def split_into_chunks(documents: List[Document]) -> List[Document]:
    """Split documents into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP
    )
    return text_splitter.split_documents(documents)
