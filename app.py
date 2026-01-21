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
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # Status Panel
    st.subheader("🔌 Connection Status")
    if rag:
        status = rag.get_status()
        
        col1, col2 = st.columns(2)
        with col1:
            if status.get("vector_store") == "connected":
                st.success("Vector DB ✅")
            else:
                st.error("Vector DB ❌")
        with col2:
            if status.get("graph_store") == "connected":
                st.success("Neo4j ✅")
            else:
                st.warning("Neo4j ⚠️")
        
        # Graph statistics
        if status.get("graph_stats"):
            stats = status["graph_stats"]
            st.caption(f"📊 Graph: {stats.get('nodes', 0)} nodes, {stats.get('relationships', 0)} relations")
    
    st.markdown("---")
    
    st.subheader("📄 Data Ingestion")
    uploaded_files = st.file_uploader(
        "Upload Documents", 
        accept_multiple_files=True,
        type=['txt', 'pdf', 'csv', 'json']
    )
    
    # Graph building toggle
    build_graph = st.checkbox("Build Knowledge Graph", value=True, 
                               help="Extract entities and relationships to Neo4j")
    
    if uploaded_files and st.button("🚀 Ingest Documents"):
        if rag:
            with st.spinner("Processing documents..."):
                temp_paths = []
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_paths.append(tmp.name)
                
                try:
                    result = rag.ingest(temp_paths, build_graph=build_graph)
                    st.success(f"✅ Processed {result['vector_chunks']} chunks!")
                    if build_graph and result['graph_entities'] > 0:
                        st.info(f"🔗 Created {result['graph_entities']} entities, {result['graph_relations']} relations")
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
    
    # Query settings
    st.subheader("🔍 Query Settings")
    use_graph = st.checkbox("Use Knowledge Graph", value=True,
                            help="Include graph context in responses")
    st.session_state['use_graph'] = use_graph
    
    st.markdown("---")
    st.info("📁 Supported formats: PDF, TXT, CSV, JSON")


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
                    use_graph = st.session_state.get('use_graph', True)
                    response = rag.query(prompt, use_graph=use_graph)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error calling RAG: {e}")
        else:
            st.error("Engine not available.")
