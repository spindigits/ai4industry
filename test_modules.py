import unittest
import os
from config import COLLECTION_NAME

class TestModules(unittest.TestCase):
    
    def test_imports(self):
        """Test that all modules can be imported."""
        try:
            import config
            import document_utils
            import neo4j_connect
            import qdrant_connect
            import rag_features
            print("✅ Modules imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import modules: {e}")

    def test_config(self):
        """Test configuration loading."""
        import config
        self.assertIsNotNone(config.COLLECTION_NAME)
        print(f"✅ Config loaded. Collection: {config.COLLECTION_NAME}")

if __name__ == '__main__':
    unittest.main()
