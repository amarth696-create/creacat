try:
    import google.generativeai as genai
    HAS_LEGACY_GENAI = True
except ImportError:
    genai = None
    HAS_LEGACY_GENAI = False

try:
    import google.genai as new_genai
    HAS_NEW_GENAI = True
except ImportError:
    new_genai = None
    HAS_NEW_GENAI = False

from typing import Dict, Any, Optional
import json

class ChatBot:
    """Yapay Zeka Sohbet Botu."""
    
    CANDIDATE_MODELS = [
        'gemini-3.6-flash', 'models/gemini-3.6-flash',
        'gemini-2.0-flash', 'models/gemini-2.0-flash',
        'gemini-1.5-flash', 'models/gemini-1.5-flash',
        'gemini-1.5-pro', 'models/gemini-1.5-pro'
    ]

    def __init__(self, gemini_api_key: str = ""):
        self.api_key = gemini_api_key or ""
        self.model = None
        self.client = None
        self._ensure_init()

    def _ensure_init(self):
        """Modeli veya istemciyi başlatır."""
        if not self.api_key:
            from config import Config
            self.api_key = getattr(Config, 'GEMINI_API_KEY', '') or ""

        if self.api_key and not self.client and not self.model:
            if HAS_NEW_GENAI and new_genai:
                try:
                    self.client = new_genai.Client(api_key=self.api_key)
                except Exception:
                    pass
            if not self.client and HAS_LEGACY_GENAI and genai:
                try:
                    genai.configure(api_key=self.api_key)
                    for m in self.CANDIDATE_MODELS:
                        try:
                            self.model = genai.GenerativeModel(m)
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
        
    def process_message(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Kullanıcı mesajını işler ve aksiyon döner."""
        self._ensure_init()
        
        system_prompt = """Sen Türkçe konuşan bir içerik üretici (influencer) keşif asistanısın. 
Kullanıcının isteklerini analiz et ve arama, filtreleme, detay görme gibi işlemleri tespit et. 
Eğer kullanıcı arama yapmak istiyorsa JSON formatında parametreleri dön."""

        prompt = f"{system_prompt}\n\nKullanıcı: {user_message}\nSistem Durumu: {context}"
        
        try:
            lower_msg = user_message.lower().strip()
            
            # Arama niyetini tespit et (ara, bul, öner, listele, veya kısa konu girişi)
            search_keywords = ["ara", "bul", "öner", "listele", "getir", "influencer", "üretici", "kanal", "hesap", "youtube", "tiktok", "instagram"]
            is_search = any(k in lower_msg for k in search_keywords) or len(user_message.split()) <= 4
            
            if is_search and "filtrele" not in lower_msg and "yardım" not in lower_msg and "nasılsın" not in lower_msg and "merhaba" not in lower_msg:
                clean_keyword = user_message
                for noise in ["bana", "için", "lütfen", "olan", "üreticilerini", "üreticileri", "influencerları", "influencerlarını", "bul", "ara"]:
                    clean_keyword = clean_keyword.replace(noise, "")
                clean_keyword = clean_keyword.strip() or user_message
                
                return {
                    "text": f"'{clean_keyword}' konusu için içerik üreticilerini aramaya başlıyorum...",
                    "action": "search",
                    "params": {"keyword": clean_keyword}
                }
            elif "filtrele" in lower_msg:
                return {
                    "text": "Sonuçlar filtreleniyor...",
                    "action": "filter",
                    "params": {}
                }
            else:
                last_error = None
                if self.client:
                    for m in self.CANDIDATE_MODELS:
                        try:
                            response = self.client.models.generate_content(
                                model=m,
                                contents=prompt
                            )
                            return {
                                "text": response.text,
                                "action": None,
                                "params": None
                            }
                        except Exception as e:
                            last_error = e
                            continue
                elif self.model:
                    try:
                        response = self.model.generate_content(prompt)
                        return {
                            "text": response.text,
                            "action": None,
                            "params": None
                        }
                    except Exception as e:
                        last_error = e

                if not self.api_key:
                    return {
                        "text": "⚠️ Gemini API anahtarı algılanamadı. Lütfen Streamlit ayarlarındaki Secrets bölümüne `GEMINI_API_KEY` eklediğinizden emin olun.",
                        "action": None,
                        "params": None
                    }

                if last_error:
                    return {
                        "text": f"⚠️ Gemini modeli yanıt veremedi ({str(last_error)}). Lütfen API anahtarınızı kontrol edin.",
                        "action": None,
                        "params": None
                    }

                return {
                    "text": "API anahtarı bulunamadı veya model başlatılamadı.",
                    "action": None,
                    "params": None
                }
        except Exception as e:
            return {
                "text": f"Bir hata oluştu: {str(e)}",
                "action": None,
                "params": None
            }
