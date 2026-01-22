"""
Authentication Module for Streamlit App.
Manages user authentication with local JSON storage.
"""

import os
import json
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime

# Path to users database
USERS_FILE = "users.json"

# Default admin account
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "created_at": "2026-01-22T00:00:00",
        "display_name": "Administrator"
    }
}


def _load_users() -> Dict[str, Any]:
    """Load users from JSON file."""
    if not os.path.exists(USERS_FILE):
        # Create file with default users
        _save_users(DEFAULT_USERS)
        return DEFAULT_USERS.copy()
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_USERS.copy()


def _save_users(users: Dict[str, Any]) -> None:
    """Save users to JSON file."""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user.
    
    Args:
        username: The username
        password: The plain text password
        
    Returns:
        User info dict if authenticated, None otherwise
    """
    users = _load_users()
    
    if username not in users:
        return None
    
    user = users[username]
    password_hash = _hash_password(password)
    
    if user["password_hash"] == password_hash:
        return {
            "username": username,
            "role": user.get("role", "user"),
            "display_name": user.get("display_name", username)
        }
    
    return None


def create_user(
    username: str, 
    password: str, 
    role: str = "user",
    display_name: str = None
) -> bool:
    """
    Create a new user.
    
    Args:
        username: The username (must be unique)
        password: The plain text password
        role: User role (admin/user)
        display_name: Display name for the user
        
    Returns:
        True if created successfully, False if user exists
    """
    users = _load_users()
    
    if username in users:
        return False
    
    users[username] = {
        "password_hash": _hash_password(password),
        "role": role,
        "created_at": datetime.now().isoformat(),
        "display_name": display_name or username
    }
    
    _save_users(users)
    return True


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """
    Change user password.
    
    Args:
        username: The username
        old_password: Current password
        new_password: New password
        
    Returns:
        True if changed successfully
    """
    users = _load_users()
    
    if username not in users:
        return False
    
    if users[username]["password_hash"] != _hash_password(old_password):
        return False
    
    users[username]["password_hash"] = _hash_password(new_password)
    _save_users(users)
    return True


def delete_user(username: str) -> bool:
    """Delete a user (cannot delete admin)."""
    if username == "admin":
        return False
        
    users = _load_users()
    
    if username not in users:
        return False
    
    del users[username]
    _save_users(users)
    return True


def list_users() -> Dict[str, Dict]:
    """List all users (without password hashes)."""
    users = _load_users()
    return {
        username: {
            "role": info.get("role", "user"),
            "display_name": info.get("display_name", username),
            "created_at": info.get("created_at", "unknown")
        }
        for username, info in users.items()
    }


def is_admin(username: str) -> bool:
    """Check if user is admin."""
    users = _load_users()
    return users.get(username, {}).get("role") == "admin"


# Streamlit Session State Helpers
def init_session_state(st):
    """Initialize authentication state in Streamlit session."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def login(st, username: str, password: str) -> bool:
    """
    Attempt to log in a user.
    
    Args:
        st: Streamlit module
        username: Username
        password: Password
        
    Returns:
        True if login successful
    """
    user = authenticate(username, password)
    if user:
        st.session_state.authenticated = True
        st.session_state.user = user
        return True
    return False


def logout(st):
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.user = None


def require_auth(st) -> bool:
    """
    Check if user is authenticated. Shows login form if not.
    
    Args:
        st: Streamlit module
        
    Returns:
        True if authenticated, False otherwise
    """
    init_session_state(st)
    
    if st.session_state.authenticated:
        return True
    
    # Show login form
    show_login_page(st)
    return False


def show_login_page(st):
    """Display the login page."""
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <h1>⚡ GreenPower RAG</h1>
            <p style="color: #888;">Please login to continue</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                remember = st.checkbox("Remember me")
            
            submitted = st.form_submit_button("🔐 Login", use_container_width=True)
            
            if submitted:
                if username and password:
                    if login(st, username, password):
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        
