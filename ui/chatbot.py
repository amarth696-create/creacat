import re
import json
from typing import Dict, Any, Optional

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

def _parse_num_text(val_str: str) -> Optional[int]:
    """'10k', '500k', '1.5m', '50000' gibi stringleri tam sayıya çevirir."""
    if not val_str:
        return None
    s = str(val_str).strip().lower().replace(".", "").replace(",", "")
    multiplier = 1
    if "k" in s:
        multiplier = 1000
        s = s.replace("k", "")
    elif "m" in s:
        multiplier = 1000000
        s = s.replace("m", "")
    try:
        return int(float(s) * multiplier)
    except Exception:
        return None

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

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Gemini modeline istek atar ve metin döner."""
        self._ensure_init()
        if self.client:
            for m in self.CANDIDATE_MODELS:
                try:
                    res = self.client.models.generate_content(model=m, contents=prompt)
                    if res and hasattr(res, 'text') and res.text:
                        return res.text
                except Exception:
                    continue
        elif self.model:
            try:
                res = self.model.generate_content(prompt)
                if res and hasattr(res, 'text') and res.text:
                    return res.text
            except Exception:
                pass
        return None
        
    def process_message(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Kullanıcı mesajını işler ve aksiyon döner."""
        lower_msg = user_message.lower().strip()
        
        # 1. Takipçi aralığı regex tespiti
        min_followers = None
        max_followers = None
        
        # '10k ile 100k arası'
        range_match = re.search(r'(\d+[\.,]?\d*[km]?)\s*(?:ile|-)\s*(\d+[\.,]?\d*[km]?)\s*arası', lower_msg)
        if range_match:
            min_followers = _parse_num_text(range_match.group(1))
            max_followers = _parse_num_text(range_match.group(2))
        else:
            # Min tespiti ('en az 10k', 'min 5000', '10k üzeri')
            min_match = re.search(r'(?:en az|minimum|min)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:üzeri|üstü|\+)', lower_msg)
            if min_match:
                val = min_match.group(1) or min_match.group(2)
                min_followers = _parse_num_text(val)
                
            # Max tespiti ('en fazla 100k', 'en çok 500k', 'maksimum 50k', '50k altı')
            max_match = re.search(r'(?:en fazla|en çok|maksimum|maks|max)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:altı|kadar)', lower_msg)
            if max_match:
                val = max_match.group(1) or max_match.group(2)
                max_followers = _parse_num_text(val)

        # 2. Arama niyetini tespit et
        search_keywords = ["ara", "bul", "öner", "listele", "getir", "influencer", "üretici", "kanal", "hesap", "youtube", "tiktok", "instagram"]
        is_search = any(k in lower_msg for k in search_keywords) or len(user_message.split()) <= 4
        is_greeting = any(w in lower_msg for w in ["merhaba", "selam", "günaydın", "nasılsın", "kimsin", "ne yapabilirsin", "yardım"])
        
        if is_search and not is_greeting and "filtrele" not in lower_msg:
            clean_keyword = user_message
            for noise in [
                "bana", "için", "lütfen", "olan", "üreticilerini", "üreticileri", "influencerları", "influencerlarını",
                "bul", "ara", "listele", "getir", "hesapları", "kanalları"
            ]:
                clean_keyword = re.sub(rf'\b{noise}\b', '', clean_keyword, flags=re.IGNORECASE)
                
            # Sayı ve filtre kelimelerini de keyword'den temizle
            clean_keyword = re.sub(r'\d+[\.,]?\d*[km]?\s*(?:ile|-)?\s*\d*[\.,]?\d*[km]?\s*(?:arası|üzeri|altı|kadar|en az|en fazla|minimum|maksimum)?', '', clean_keyword, flags=re.IGNORECASE)
            clean_keyword = re.sub(r'\s+', ' ', clean_keyword).strip() or user_message
            
            detail_msg = f"'{clean_keyword}' konusu için içerik üreticileri aranıyor..."
            if min_followers or max_followers:
                f_details = []
                if min_followers:
                    f_details.append(f"Min: {min_followers:,}")
                if max_followers:
                    f_details.append(f"Maks: {max_followers:,}")
                detail_msg += f" (Filtre: {', '.join(f_details)} takipçi)"
                
            return {
                "text": detail_msg,
                "action": "search",
                "params": {
                    "keyword": clean_keyword,
                    "min_followers": min_followers,
                    "max_followers": max_followers
                }
            }
            
        elif "filtrele" in lower_msg:
            return {
                "text": "Filtreleme kriterleri güncelleniyor...",
                "action": "filter",
                "params": {"min_followers": min_followers, "max_followers": max_followers}
            }

        # 3. Genel sohbet için Gemini çağrısı (ASLA raw JSON üretmeyecek)
        prompt = (
            f"Sen Türkçe konuşan profesyonel bir içerik üretici (influencer) keşif asistanısın.\n"
            f"Kullanıcının sorusuna veya mesajına samimi, yardımcı ve akıcı bir Türkçe ile yanıt ver.\n"
            f"ÖNEMLİ KURAL: ASLA JSON veya kod formatında yanıt verme. Doğrudan kullanıcıya hitap eden düz metin yaz.\n\n"
            f"Kullanıcı mesajı: {user_message}"
        )
        
        gemini_text = self._call_gemini(prompt)
        if gemini_text:
            # Eğer model yanlışlıkla JSON döndüyse JSON bloklarını temizle
            if "```json" in gemini_text or (gemini_text.strip().startswith("{") and gemini_text.strip().endswith("}")):
                try:
                    cleaned_json = gemini_text.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(cleaned_json)
                    kw = parsed.get("keyword") or parsed.get("konu") or user_message
                    min_f = parsed.get("min_followers") or parsed.get("min_takipci") or min_followers
                    max_f = parsed.get("max_followers") or parsed.get("max_takipci") or max_followers
                    return {
                        "text": f"'{kw}' için içerik üreticileri aranıyor...",
                        "action": "search",
                        "params": {"keyword": kw, "min_followers": min_f, "max_followers": max_f}
                    }
                except Exception:
                    gemini_text = "Size yardımcı olmak için hazırım. Hangi konuda içerik üretici bulmak istersiniz?"
                    
            return {
                "text": gemini_text,
                "action": None,
                "params": None
            }

        return {
            "text": "Merhaba! Size hangi kategoride (örneğin fitness, teknoloji, yemek) içerik üreticisi bulmamı istersiniz?",
            "action": None,
            "params": None
        }

