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
    
    CANDIDATE_MODELS = ['gemini-3.6-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']

    def __init__(self, gemini_api_key: str):
        self.model = None
        self.client = None
        self.api_key = gemini_api_key or ""
        
        if self.api_key:
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
        system_prompt = """Sen Türkçe konuşan bir içerik üretici (influencer) keşif asistanısın. 
Kullanıcının isteklerini analiz et ve arama, filtreleme, detay görme gibi işlemleri tespit et. 
Eğer kullanıcı arama yapmak istiyorsa JSON formatında parametreleri dön."""

        prompt = f"{system_prompt}\n\nKullanıcı: {user_message}\nSistem Durumu: {context}"
        
        try:
            lower_msg = user_message.lower()
            if "ara" in lower_msg or "bul" in lower_msg or "öner" in lower_msg:
                return {
                    "text": f"'{user_message}' için arama işlemini başlatıyorum...",
                    "action": "search",
                    "params": {"keyword": user_message}
                }
            elif "filtrele" in lower_msg:
                return {
                    "text": "Sonuçları filtreleniyor...",
                    "action": "filter",
                    "params": {}
                }
            else:
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
                        except Exception:
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
                        return {
                            "text": f"Model yanıt veremedi: {str(e)}",
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
