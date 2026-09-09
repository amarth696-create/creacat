import google.generativeai as genai
from typing import Dict, Any, Optional
import json

class ChatBot:
    """Yapay Zeka Sohbet Botu."""
    
    def __init__(self, gemini_api_key: str):
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None
        
    def process_message(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Kullanıcı mesajını işler ve aksiyon döner."""
        system_prompt = """Sen Türkçe konuşan bir içerik üretici (influencer) keşif asistanısın. 
Kullanıcının isteklerini analiz et ve arama, filtreleme, detay görme gibi işlemleri tespit et. 
Eğer kullanıcı arama yapmak istiyorsa JSON formatında parametreleri dön."""

        prompt = f"{system_prompt}\n\nKullanıcı: {user_message}\nSistem Durumu: {context}"
        
        try:
            # Basit bir simülasyon, gerçek implementasyonda function calling kullanılmalı
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
                if self.model:
                    response = self.model.generate_content(prompt)
                    return {
                        "text": response.text,
                        "action": None,
                        "params": None
                    }
                return {
                    "text": "API anahtarı bulunamadı, sohbet özelliği devre dışı.",
                    "action": None,
                    "params": None
                }
        except Exception as e:
            return {
                "text": f"Bir hata oluştu: {str(e)}",
                "action": None,
                "params": None
            }
