import reflex as rx
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import existing backend logic
from rag_features import HybridRetriever
from qdrant_connect import QdrantConnector
from auth import authenticate

class State(rx.State):
    """The app state."""
    
    # --- Authentication State ---
    user: Optional[Dict[str, Any]] = None
    username_input: str = ""
    password_input: str = ""
    auth_error: str = ""
    
    # --- Chat State ---
    chat_history: List[Dict[str, str]] = []
    question: str = ""
    is_processing: bool = False
    
    # --- Ingestion State ---
    upload_result: Dict[str, Any] = {}
    is_uploading: bool = False
    
    # --- Scraping State ---
    scrape_urls: str = ""
    scrape_follow_links: bool = False
    scrape_max_pages: int = 5
    scrape_result: Dict[str, Any] = {}
    is_scraping: bool = False
    
    # --- Metrics State ---
    # (We could load metrics from CSV here if needed for dashboard)
    
    # --- Internal Objects (not serialized) ---
    _rag: Optional[HybridRetriever] = None

    # --- Explicit Setters (for Reflex 0.9 compatibility) ---
    def set_username_input(self, value: str): self.username_input = value
    def set_password_input(self, value: str): self.password_input = value
    def set_question(self, value: str): self.question = value
    def set_scrape_urls(self, value: str): self.scrape_urls = value
    def set_scrape_follow_links(self, value: bool): self.scrape_follow_links = value
    def set_scrape_max_pages(self, value: str): self.scrape_max_pages = int(value) if value.isdigit() else 5

    def on_load(self):
        """Called when the app loads."""
        pass

    @rx.var
    def is_authenticated(self) -> bool:
        return self.user is not None

    def get_rag(self):
        """Get or initialize the RAG engine."""
        if self._rag is None:
            try:
                self._rag = HybridRetriever()
            except Exception as e:
                print(f"Error initializing RAG: {e}")
        return self._rag

    # --- Authentication Handlers ---
    
    def login(self):
        """Handle login submission."""
        user_info = authenticate(self.username_input, self.password_input)
        if user_info:
            self.user = user_info
            self.auth_error = ""
            self.password_input = "" # Clear password
        else:
            self.auth_error = "Invalid username or password"
            
    def logout(self):
        """Handle logout."""
        self.user = None
        self.chat_history = []

    # --- Chat Handlers ---

    def _generate_answer_step(self, question, history):
        """Helper to run RAG logic (runs in thread pool by default in Reflex events)."""
        rag = self.get_rag()
        if not rag:
            return "System Error: RAG engine could not be initialized."

        # Contextualize
        # Reflex history is dict, formatting for our backend
        formatted_history = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in history
        ]
        
        contextualized_query = rag.contextualize_query(question, formatted_history)
        chunks, route, timings = rag.retrieve(contextualized_query)
        response = rag.generate_answer(contextualized_query, chunks, route)
        
        # Add latency info/debug to response (optional, or store in separate var)
        debug_info = f"\n\n*(Route: {route} | Latency: {(timings.get('qdrant',0)+timings.get('neo4j',0)):.2f}s)*"
        return response + debug_info

    async def handle_submit(self):
        """Handle chat submission."""
        if not self.question:
            return

        user_msg = self.question
        self.is_processing = True
        
        # Add user message immediately
        self.chat_history.append({"role": "user", "content": user_msg})
        self.question = "" # Clear input
        yield # Trigger UI update
        
        # Get response
        # Note: In a real async blocking scenario, we might want to run_in_executor
        response = self._generate_answer_step(user_msg, self.chat_history[:-1])
        
        self.chat_history.append({"role": "assistant", "content": response})
        self.is_processing = False

    # --- Ingestion Handlers ---
    
    async def handle_upload(self, files: List[rx.UploadFile]):
        """Handle file upload and ingestion."""
        self.is_uploading = True
        yield
        
        rag = self.get_rag()
        if not rag:
            self.upload_result = {"error": "RAG engine not ready"}
            self.is_uploading = False
            return

        # Save uploaded files temporally
        saved_paths = []
        upload_dir = "temp_uploads_reflex"
        os.makedirs(upload_dir, exist_ok=True)
        
        try:
            for file in files:
                upload_data = await file.read()
                file_path = os.path.join(upload_dir, file.filename)
                with open(file_path, "wb") as f:
                    f.write(upload_data)
                saved_paths.append(file_path)
            
            # Run ingestion
            if saved_paths:
                result = rag.ingest(saved_paths)
                self.upload_result = result
            else:
                self.upload_result = {"error": "No files received"}
                
        except Exception as e:
            self.upload_result = {"error": str(e)}
        finally:
            self.is_uploading = False
            # Cleanup could happen here or later
            
    # --- Scraping Handlers ---
    
    def handle_scrape(self):
        """Handle web scraping."""
        self.is_scraping = True
        yield
        
        if not self.scrape_urls:
            self.scrape_result = {"error": "No URLs provided"}
            self.is_scraping = False
            return
            
        rag = self.get_rag()
        if not rag:
            self.scrape_result = {"error": "RAG engine not ready"}
            self.is_scraping = False
            return

        urls = [u.strip() for u in self.scrape_urls.split('\n') if u.strip()]
        
        try:
            result = rag.ingest_web(
                urls=urls,
                follow_links=self.scrape_follow_links,
                max_pages=int(self.scrape_max_pages)
            )
            self.scrape_result = result
        except Exception as e:
            self.scrape_result = {"error": str(e)}
        
        self.is_scraping = False
