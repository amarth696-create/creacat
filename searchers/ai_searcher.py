import json
import logging
from typing import List, Dict, Any, Optional
from models.creator import Creator
from searchers.base import BaseSearcher

logger = logging.getLogger(__name__)

class AISearcher(BaseSearcher):
    """
    Gemini yapay zeka modelinin bilgi tabanını kullanarak 
    belirli konu ve filtre kriterlerine uygun gerçek sosyal medya içerik üreticilerini keşfeder.
    """
    
    CANDIDATE_MODELS = [
        'gemini-2.0-flash', 'models/gemini-2.0-flash',
        'gemini-1.5-flash', 'models/gemini-1.5-flash',
        'gemini-1.5-pro', 'models/gemini-1.5-pro'
    ]
    
    def __init__(self, api_key: str = ""):
        super().__init__()
        self.api_key = api_key or ""
        self.client = None
        self.model = None
        self._init_gemini()
        
    def _init_gemini(self):
        if not self.api_key:
            from config import Config
            self.api_key = getattr(Config, 'GEMINI_API_KEY', '') or ""
            
        if self.api_key:
            try:
                import google.genai as new_genai
                self.client = new_genai.Client(api_key=self.api_key)
            except Exception:
                pass
                
            if not self.client:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    for m in self.CANDIDATE_MODELS:
                        try:
                            self.model = genai.GenerativeModel(m)
                            break
                        except Exception:
                            continue
                except Exception:
                    pass

    @property
    def platform_name(self) -> str:
        return "AI Discovery"

    def search(self, query: str, limit: int = 15, filters: Dict[str, Any] = None) -> List[Creator]:
        return self.ara(query, filters or {})

    def ara(self, keyword: str, filters: Dict[str, Any] = None) -> List[Creator]:
        filters = filters or {}
        min_f = filters.get("min_followers", 0) or 0
        max_f = filters.get("max_followers")
        plats = filters.get("platforms") or ["YouTube", "TikTok", "Instagram"]
        country = filters.get("country") or "Türkiye"
        language = filters.get("language") or "Türkçe"
        
        limit = filters.get("limit", 15)
        
        prompt = f"""
Sen Türkiye ve dünya sosyal medya ekosistemini (YouTube, Instagram, TikTok) çok iyi tanıyan uzman bir influencer keşif asistanısın.

GÖREVİN:
Aşağıdaki kriterlere en iyi uyan, Türkiye'de aktif ve bilinen GERÇEK içerik üreticilerini (kanalları / hesapları) bulmak.

KRİTERLER:
- Konu / Niş: {keyword}
- Hedef Platformlar: {plats}
- Takipçi Aralığı: Minimum {min_f:,} - Maksimum {str(max_f) if max_f else 'Sınırsız'} takipçi
- Ülke / Bölge: {country}
- İçerik Dili: {language}

KURALLAR:
1. Uydurma veya hayali hesaplar YAZMA. Türkiye'de gerçekten içerik üreten, bu alanda bilinen hesapları seç.
2. Takipçi aralığına dikkat et (Mikro/Makro ölçeğine uygun hesaplar öner).
3. Her üretici için gerçekçi veya bilinen ortalama takipçi sayısı, profil linki ve biyografi yaz.
4. En az 6, en fazla {limit} adet içerik üreticisi listele.

YANIT FORMATI:
SADECE aşağıdaki JSON formatında geçerli bir JSON listesi döndür. Kesinlikle markdown kod bloğu olmadan saf JSON ver:
[
  {{
    "username": "Kullanıcı veya Kanal Adı",
    "platform": "YouTube",
    "followers": 12500,
    "profile_url": "https://www.youtube.com/...",
    "bio": "İçerik üreticisinin konusu ve ürettiği içerikler hakkında kısa bilgi",
    "engagement_rate": 3.8
  }}
]
"""
        raw_text = self._call_llm(prompt)
        if not raw_text:
            return []
            
        return self._parse_response(raw_text)

    def _call_llm(self, prompt: str) -> Optional[str]:
        self._init_gemini()
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

    def _parse_response(self, text: str) -> List[Creator]:
        creators = []
        try:
            cleaned = text.strip()
            if "`json" in cleaned:
                cleaned = cleaned.split("`json")[1].split("`")[0].strip()
            elif "`" in cleaned:
                cleaned = cleaned.split("`")[1].split("`")[0].strip()
            elif "[" in cleaned and "]" in cleaned:
                start = cleaned.find("[")
                end = cleaned.rfind("]") + 1
                cleaned = cleaned[start:end].strip()
                
            data = json.loads(cleaned)
            if not isinstance(data, list):
                return []
                
            for item in data:
                plat_str = str(item.get("platform", "YouTube")).capitalize()
                u_name = str(item.get("username", "Bilinmeyen"))
                d_name = str(item.get("display_name") or u_name)
                followers = int(item.get("followers", 0) or 0)
                eng_rate = float(item.get("engagement_rate", 0.0) or 0.0)
                url = item.get("profile_url") or f"https://www.google.com/search?q={u_name}"
                
                c = Creator(
                    username=u_name,
                    display_name=d_name,
                    platform=plat_str,
                    profile_url=url,
                    followers=followers,
                    bio=item.get("bio", ""),
                    country="Türkiye",
                    language="Türkçe"
                )
                c.engagement_rate = eng_rate
                creators.append(c)
        except Exception as e:
            logger.warning(f"AI Searcher yanıtı ayrıştırılamadı: {e}")
            
        return creators
