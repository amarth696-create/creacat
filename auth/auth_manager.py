"""
Yetkilendirme ve Kullanıcı Kimlik Doğrulama Yöneticisi.
Yalnızca tanımlı e-posta adresleri ve şifreler ile erişim sağlar.
"""
import hashlib
import hmac
from typing import Optional, Dict, Any

def _get_session_state():
    try:
        import streamlit as st
        return st.session_state
    except ImportError:
        return {}

# Tanımlı kullanıcılar ve şifre hash'leri
# Ortak şifre: turuncu3614
def _hash_password(password: str) -> str:
    """Şifreyi SHA-256 ile özetler."""
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

COMMON_PASSWORD_HASH = _hash_password("turuncu3614")

ALLOWED_USERS = {
    "enes@nabulu.com.tr": {
        "name": "Enes",
        "email": "enes@nabulu.com.tr",
        "password_hash": COMMON_PASSWORD_HASH,
        "role": "admin"
    },
    "elif@nabulu.com.tr": {
        "name": "Elif",
        "email": "elif@nabulu.com.tr",
        "password_hash": COMMON_PASSWORD_HASH,
        "role": "member"
    },
    "akif@nabulu.com.tr": {
        "name": "Akif",
        "email": "akif@nabulu.com.tr",
        "password_hash": COMMON_PASSWORD_HASH,
        "role": "member"
    },
    "begum@nabulu.com.tr": {
        "name": "Begüm",
        "email": "begum@nabulu.com.tr",
        "password_hash": COMMON_PASSWORD_HASH,
        "role": "member"
    },
    "kubra@nabulu.com.tr": {
        "name": "Kübra",
        "email": "kubra@nabulu.com.tr",
        "password_hash": COMMON_PASSWORD_HASH,
        "role": "member"
    }
}


class AuthManager:
    """Kullanıcı girişini ve Streamlit oturum durumunu yönetir."""

    SESSION_KEY_USER = "auth_user"
    SESSION_KEY_LOGGED_IN = "is_authenticated"

    @classmethod
    def verify_credentials(cls, email: str, password: str) -> Optional[Dict[str, Any]]:
        """E-posta ve şifreyi doğrular. Başarılıysa kullanıcı verisini döner."""
        clean_email = email.strip().lower()
        user = ALLOWED_USERS.get(clean_email)
        if not user:
            return None
        
        entered_hash = _hash_password(password)
        if hmac.compare_digest(entered_hash, user["password_hash"]):
            return {
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        return None

    @classmethod
    def login(cls, email: str, password: str) -> bool:
        """Kullanıcıyı oturuma alır."""
        user = cls.verify_credentials(email, password)
        if user:
            state = _get_session_state()
            state[cls.SESSION_KEY_LOGGED_IN] = True
            state[cls.SESSION_KEY_USER] = user
            return True
        return False

    @classmethod
    def logout(cls) -> None:
        """Kullanıcı oturumunu kapatır ve state'i temizler."""
        state = _get_session_state()
        state[cls.SESSION_KEY_LOGGED_IN] = False
        state[cls.SESSION_KEY_USER] = None
        # Sohbet geçmişi ve aktif chat değişkenlerini sıfırla
        if "active_chat_id" in state:
            del state["active_chat_id"]
        if "chat_history" in state:
            state["chat_history"] = []

    @classmethod
    def is_authenticated(cls) -> bool:
        """Kullanıcının aktif bir oturumu olup olmadığını kontrol eder."""
        state = _get_session_state()
        return bool(state.get(cls.SESSION_KEY_LOGGED_IN, False))

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """Mevcut oturum açmış kullanıcıyı döner."""
        if cls.is_authenticated():
            state = _get_session_state()
            return state.get(cls.SESSION_KEY_USER)
        return None
