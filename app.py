import streamlit as st
import os
import tempfile
from rag_logic import HybridRAG

# Page config
st.set_page_config(
    page_title="Hybrid RAG Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stButton>button {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        border: none;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
    }
    .user-message {
        background-color: #2b313e;
    }
    .bot-message {
        background-color: #1c2128;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# Initialize RAG engine
@st.cache_resource
def get_engine():
    try:
        return HybridRAG()
    except Exception as e:
        st.error(f"Failed to initialize RAG Engine: {e}")
        return None

rag = get_engine()

# Sidebar
with st.sidebar:
    st.title("Settings")
    st.markdown("---")
    
    st.subheader("Data Ingestion")
    uploaded_files = st.file_uploader(
        "Upload Documents", 
        accept_multiple_files=True,
        type=['txt', 'pdf', 'csv', 'json']
    )
    
    if uploaded_files and st.button("Ingest Documents"):
        if rag:
            with st.spinner("Processing documents..."):
                temp_paths = []
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_paths.append(tmp.name)
                
                try:
                    num_chunks = rag.ingest(temp_paths)
                    st.success(f"Successfully processed {num_chunks} chunks!")
                except Exception as e:
                    st.error(f"Error during ingestion: {e}")
                finally:
                    # Cleanup
                    for p in temp_paths:
                        try:
                            os.remove(p)
                        except:
                            pass
        else:
            st.error("RAG engine not initialized. Check your credentials.")

    st.markdown("---")
    st.info("Supported formats: PDF, TXT, CSV, JSON")

# Main Chat Interface
st.title("Knowledge Graph & Vector RAG")
st.markdown("Ask questions about your uploaded documents.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if rag:
            with st.spinner("Thinking..."):
                try:
                    response = rag.query(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error calling RAG: {e}")
        else:
            st.error("Engine not available.")
