import streamlit as st
from typing import List, Dict, Any, Optional

def init_session_state() -> None:
    """Streamlit session state'i başlatır."""
    defaults = {
        "chat_history": [],
        "current_results": [],
        "search_params": {},
        "is_searching": False,
        "selected_creator": None,
        "search_sessions": [],
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_state(key: str) -> Any:
    """Belirtilen state değerini döner."""
    return st.session_state.get(key)

def set_state(key: str, value: Any) -> None:
    """Belirtilen state değerini günceller."""
    st.session_state[key] = value
