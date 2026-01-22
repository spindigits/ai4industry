"""
Test Script - Validation du découpage modulaire
"""
import sys

def test_imports():
    """Test que tous les modules s'importent correctement"""
    print("🧪 Test 1: Imports des modules...")
    
    try:
        import config
        print("  ✅ config.py")
        
        from qdrant_connect import QdrantConnector
        print("  ✅ qdrant_connect.py")
        
        from neo4j_connect import Neo4jConnector
        print("  ✅ neo4j_connect.py")
        
        from rag_features import HybridRetriever, SimpleRAG
        print("  ✅ rag_features.py")
        
        from document_utils import load_document, split_into_chunks
        print("  ✅ document_utils.py")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur import: {e}")
        return False


def test_routing():
    """Test le routing logic du HybridRetriever"""
    print("\n🧪 Test 2: Routing Logic...")
    
    try:
        from rag_features import HybridRetriever
        
        retriever = HybridRetriever(use_neo4j=False)
        
        # Test simple queries → Qdrant
        simple_queries = [
            "What is the price?",
            "Quels sont les prix?",
            "Define solar panel",
            "Explain the product specs"
        ]
        
        for query in simple_queries:
            route = retriever.route_query(query)
            assert route == 'qdrant', f"Query '{query}' should route to qdrant, got {route}"
            print(f"  ✅ '{query[:30]}...' → {route}")
        
        # Test multi-hop queries → Neo4j (si activé)
        retriever_neo4j = HybridRetriever(use_neo4j=True)
        
        multi_hop_queries = [
            "Show customer history and related products",
            "What is the evolution of prices?",
            "Quelle est l'évolution des stocks?",
            "Who is connected to this project?"
        ]
        
        for query in multi_hop_queries:
            route = retriever_neo4j.route_query(query)
            print(f"  ✅ '{query[:30]}...' → {route}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur routing: {e}")
        return False


def test_qdrant_connector():
    """Test basique du QdrantConnector"""
    print("\n🧪 Test 3: QdrantConnector (in-memory)...")
    
    try:
        from qdrant_connect import QdrantConnector
        
        # Init avec :memory:
        qdrant = QdrantConnector()
        print("  ✅ Connector initialisé")
        
        # Test temporal detection
        assert qdrant.is_temporal_content("prix_2025.csv", "Liste des prix") == True
        print("  ✅ Détection temporelle (prix)")
        
        assert qdrant.is_temporal_content("politique_rh.pdf", "Règles internes") == False
        print("  ✅ Détection stable (politique)")
        
        # Test collection creation
        result = qdrant.create_collection()
        print(f"  ✅ Collection: {result}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur Qdrant: {e}")
        return False


def test_document_utils():
    """Test des utilitaires documents"""
    print("\n🧪 Test 4: Document Utils...")
    
    try:
        from document_utils import split_into_chunks
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=10,
        )
        
        test_text = "Hello world. " * 50
        docs = split_into_chunks(test_text, text_splitter)
        
        assert len(docs) > 0
        assert all('text' in doc for doc in docs)
        
        print(f"  ✅ Chunking OK - {len(docs)} chunks créés")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur document utils: {e}")
        return False


def run_all_tests():
    """Execute tous les tests"""
    print("="*70)
    print("🚀 TESTS VALIDATION - GreenPower RAG Modulaire")
    print("="*70)
    
    tests = [
        test_imports,
        test_routing,
        test_qdrant_connector,
        test_document_utils,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "="*70)
    print("📊 RÉSULTATS")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passés: {passed}/{total}")
    
    if passed == total:
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        return 0
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
