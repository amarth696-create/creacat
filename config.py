import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def _get_api_key(key_name: str, default: str = "") -> str:
    # 1. Environment variables (büyük veya küçük harf)
    val = os.getenv(key_name, "") or os.getenv(key_name.lower(), "")
    if val:
        return val
        
    # 2. Streamlit secrets
    try:
        import streamlit as st
        # Doğrudan anahtar
        if key_name in st.secrets:
            return str(st.secrets[key_name])
        if key_name.lower() in st.secrets:
            return str(st.secrets[key_name.lower()])
            
        # Alt bölümleri (sections) tara
        for section_key, section_val in st.secrets.items():
            if isinstance(section_val, dict):
                if key_name in section_val:
                    return str(section_val[key_name])
                if key_name.lower() in section_val:
                    return str(section_val[key_name.lower()])
    except Exception:
        pass
        
    return default

class ConfigMeta(type):
    @property
    def YOUTUBE_API_KEY(cls) -> str:
        return _get_api_key('YOUTUBE_API_KEY')
        
    @property
    def GEMINI_API_KEY(cls) -> str:
        return _get_api_key('GEMINI_API_KEY')

class Config(metaclass=ConfigMeta):
    """Uygulama konfigürasyon sınıfı."""
    
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
