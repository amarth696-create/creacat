import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def _get_api_key(key_name: str, default: str = "") -> str:
    val = os.getenv(key_name, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key_name, "")
        except Exception:
            pass
    return val or default

class Config:
    """Uygulama konfigürasyon sınıfı."""
    
    # API Keys
    YOUTUBE_API_KEY = _get_api_key('YOUTUBE_API_KEY')
    GEMINI_API_KEY = _get_api_key('GEMINI_API_KEY')
    
    # Varsayılan Değerler
    DEFAULT_DEPTH = 1
    DEFAULT_LIMIT = 50
    DEFAULT_MIN_FOLLOWERS = 1000
    DEFAULT_PLATFORMS = ['youtube', 'tiktok', 'instagram']
    
    # Arama Seviyesi Ağırlıkları
    SCORE_WEIGHTS = {
        1: {'engagement': 0.5, 'keyword': 0.5},
        2: {'engagement': 0.3, 'keyword': 0.4, 'content': 0.3},
        3: {'engagement': 0.2, 'keyword': 0.3, 'content': 0.3, 'transcript': 0.2},
        4: {'engagement': 0.1, 'keyword': 0.2, 'content': 0.3, 'transcript': 0.2, 'vision': 0.2}
    }
    
    # Modeller
    WHISPER_MODEL = 'base'
    CLIP_MODEL = 'ViT-B/32'
    
    # Yollar
    BASE_DIR = Path(__file__).parent
    DB_PATH = str(BASE_DIR / 'data' / 'history' / 'search_history.db')
    TEMP_DIR = str(BASE_DIR / 'data' / 'temp')
    RESULTS_DIR = str(BASE_DIR / 'data' / 'results')
    
    @classmethod
    def setup_directories(cls):
        """Gerekli dizinleri oluşturur."""
        directories = [
            Path(cls.DB_PATH).parent,
            Path(cls.TEMP_DIR),
            Path(cls.RESULTS_DIR)
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# Konfigürasyon nesnesi başlatıldığında dizinleri kur
Config.setup_directories()
