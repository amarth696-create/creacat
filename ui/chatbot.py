import re
import json
from typing import Dict, List, Any, Optional

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
        
    def process_message(
        self, 
        user_message: str, 
        context: Dict[str, Any], 
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Kullanıcı mesajını, kenar çubuğu ayarlarını ve sohbet geçmişini birlikte değerlendirir.
        """
        # 1. Kenar çubuğu filtrelerini hazırla
        ctx_platforms = context.get("platforms") or ["YouTube", "TikTok", "Instagram"]
        ctx_min_followers = context.get("min_followers", 0) or 0
        ctx_max_followers = context.get("max_followers")
        ctx_country = context.get("country") or "Belirtilmedi"
        ctx_language = context.get("language") or "Belirtilmedi"

        # 2. Sohbet geçmişini derle (son 6 mesaj)
        conv_lines = []
        if history:
            for m in history[-6:]:
                role = "Kullanıcı" if m.get("role") == "user" else "Asistan"
                txt = (m.get("content") or "").strip()
                if txt and not txt.startswith("```"):
                    if len(txt) > 250:
                        txt = txt[:250] + "..."
                    conv_lines.append(f"{role}: {txt}")
        conv_history_str = "\n".join(conv_lines)

        # 3. Gemini LLM ile Akıllı Niyet & Parametre Analizi
        gemini_result = self._analyze_with_gemini(
            user_message=user_message,
            context={
                "platforms": ctx_platforms,
                "min_followers": ctx_min_followers,
                "max_followers": ctx_max_followers,
                "country": ctx_country,
                "language": ctx_language
            },
            history_str=conv_history_str
        )
        
        if gemini_result:
            return gemini_result

        # 4. Gemini yanıt vermezse veya hata oluşursa Kural Tabanlı Fallback
        return self._rule_based_fallback(user_message, context, history)

    def _analyze_with_gemini(
        self, 
        user_message: str, 
        context: Dict[str, Any], 
        history_str: str
    ) -> Optional[Dict[str, Any]]:
        """Gemini kullanarak mesajın ve konuşma bağlamının niyetini çıkarır."""
        prompt = f"""
Sen Türkçe konuşan profesyonel bir sosyal medya içerik üreticisi (influencer) keşif uzmanısın.

KENAR ÇUBUĞU (SIDEBAR) AKTİF AYARLARI:
Kullanıcı sol kenar çubuğunda filtrelerini zaten ayarlamıştır:
- Platformlar: {context.get('platforms')}
- Minimum Takipçi: {context.get('min_followers')}
- Maksimum Takipçi: {context.get('max_followers') or 'Sınırsız'}
- Ülke: {context.get('country')}
- Dil: {context.get('language')}

ÇOK ÖNEMLİ KURALLAR:
1. KENAR ÇUBUĞU AYARLARINI TEKRAR SORMA:
   Kullanıcı platformları ve takipçi aralığını sol menüde zaten belirlemiştir. Kullanıcıya 'hangi platform?', 'bütçeniz/takipçi aralığınız nedir?' gibi sol menüde zaten seçili olan filtreleri ASLA TEKRAR SORMA.
2. DİYALOG BAĞLAMI VE SORU-CEVAP:
   Kullanıcının son mesajı önceki konuşmanın veya bir sorun varsa onun yanıtı olabilir. Konuşma geçmişini ve son mesajı birlikte değerlendir.
3. ARAMA KARARI ('action': 'search'):
   - Eğer kullanıcının mesajında veya konuşma akışında bir hedef kitle, niş, sektör veya konu (örneğin 'üniversite öğrencileri', 'yks hazırlık', 'fitness', 'yazılım', 'gezi') varsa aksiyonu 'search' yap.
   - 'keyword': Sosyal medya platformlarında (YouTube, Instagram, TikTok) arama yapmak için kullanılacak EN NET, EN KISA arama kelimesini veya tamlamasını çıkar.
     * DOĞRU KEYWORD: 'üniversite öğrencileri', 'fitness', 'yks', 'yazılım'
     * KESİNLİKLE YASAK: Kullanıcının konuşma cümlesini ('platformlara homojen şekilde ağırlık ver...', 'kişileri arıyorum', 'hedef kitlem', 'istiyorum', 'bana bul') keyword içine KOYMA! Yalnızca aranacak öz konuyu yaz.
   - 'min_followers': Kullanıcı mesajında özel olarak yeni bir sayı belirttiyse onu al, yoksa kenar çubuğundaki ({context.get('min_followers')}) değerini kullan.
   - 'max_followers': Kullanıcı mesajında özel olarak üst sınır belirttiyse onu al, yoksa kenar çubuğundaki ({context.get('max_followers') or 'null'}) değerini kullan.
   - 'reply_text': Kullanıcıya chat ekranında gösterilecek kısa, kibar Türkçe onay cümlesi. Kullanıcının aradığı konuya ek olarak sistemin bu konuyla ilgili türettiği alt başlıkları da (ör: 'üniversite hayatı, study with me, yks hazırlık, ders çalışma') tarayacağını belirten samimi bir cümle kur.
4. SOHBET KARARI ('action': 'chat'):
   - Yalnızca kullanıcı sadece 'merhaba', 'selam', 'nasılsın' dediğinde ve aranacak hiçbir konu/kategori yoksa kullan.
   - 'reply_text': Samimi Türkçe yanıt. Kenar çubuğundaki filtrelerin farkında olduğunu hissettir.

Önceki Sohbet Geçmişi:
{history_str if history_str else '(Henüz geçmiş yok)'}

Kullanıcının Son Mesajı:
{user_message}

YANIT FORMATI:
Yalnızca geçerli bir JSON nesnesi döndür. Markdown kod bloğu olmadan saf JSON ver:
{{
  "action": "search",
  "keyword": "kısa_arama_kelimesi",
  "min_followers": {context.get('min_followers') or 0},
  "max_followers": {context.get('max_followers') or 'null'},
  "platforms": {json.dumps(context.get('platforms', ['YouTube', 'TikTok', 'Instagram']))},
  "reply_text": "Kullanıcıya gösterilecek Türkçe onay mesajı"
}}
"""
        raw_text = self._call_gemini(prompt)
        if not raw_text:
            return None
            
        try:
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            elif "{" in cleaned and "}" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                cleaned = cleaned[start:end].strip()
                
            parsed = json.loads(cleaned)
            action = parsed.get("action", "search")
            
            if action == "search":
                raw_kw = parsed.get("keyword") or ""
                # Keyword temizliği
                clean_kw = self._clean_keyword_string(raw_kw) or self._clean_keyword_string(user_message)
                
                min_f = parsed.get("min_followers")
                if min_f is None:
                    min_f = context.get("min_followers")
                    
                max_f = parsed.get("max_followers")
                if max_f is None:
                    max_f = context.get("max_followers")
                    
                plats = parsed.get("platforms") or context.get("platforms") or ["YouTube", "TikTok", "Instagram"]
                
                reply = parsed.get("reply_text") or f"'{clean_kw}' konusu için içerik üreticileri aranıyor..."
                
                return {
                    "text": reply,
                    "action": "search",
                    "params": {
                        "keyword": clean_kw,
                        "min_followers": min_f,
                        "max_followers": max_f,
                        "platforms": plats
                    }
                }
            else:
                return {
                    "text": parsed.get("reply_text") or "Size nasıl yardımcı olabilirim? Hangi alanda influencer aramak istersiniz?",
                    "action": None,
                    "params": None
                }
        except Exception:
            return None

    def _rule_based_fallback(
        self, 
        user_message: str, 
        context: Dict[str, Any], 
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Gemini çevrimdışı veya yanıt veremezse çalışan gelişmiş kural tabanlı ayrıştırıcı."""
        lower_msg = user_message.lower().strip()
        
        # Selamlaşma kontrolü
        greetings = ["merhaba", "selam", "günaydın", "iyi günler", "nasılsın", "kimsin", "ne yapabilirsin"]
        if any(lower_msg == g or lower_msg == f"{g}!" for g in greetings):
            return {
                "text": "Merhaba! Sol paneldeki filtrelerinize uygun olarak hangi kategoride (örneğin üniversite öğrencileri, teknoloji, fitness) içerik üreticisi aramak istersiniz?",
                "action": None,
                "params": None
            }

        # Takipçi aralığı regex tespiti
        min_followers = context.get("min_followers")
        max_followers = context.get("max_followers")
        
        # '1000-15000 arası' veya '10k ile 100k arası'
        range_match = re.search(r'(\d+[\.,]?\d*[km]?)\s*(?:ile|-)\s*(\d+[\.,]?\d*[km]?)\s*arası', lower_msg)
        if range_match:
            min_followers = _parse_num_text(range_match.group(1))
            max_followers = _parse_num_text(range_match.group(2))
        else:
            min_match = re.search(r'(?:en az|minimum|min)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:üzeri|üstü|\+)', lower_msg)
            if min_match:
                min_followers = _parse_num_text(min_match.group(1) or min_match.group(2))
                
            max_match = re.search(r'(?:en fazla|en çok|maksimum|maks|max)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:altı|kadar)', lower_msg)
            if max_match:
                max_followers = _parse_num_text(max_match.group(1) or max_match.group(2))

        # Platform tespiti
        platforms = list(context.get("platforms") or ["YouTube", "TikTok", "Instagram"])
        mentioned_plats = []
        if "youtube" in lower_msg:
            mentioned_plats.append("YouTube")
        if "tiktok" in lower_msg:
            mentioned_plats.append("TikTok")
        if "instagram" in lower_msg:
            mentioned_plats.append("Instagram")
        if mentioned_plats:
            platforms = mentioned_plats

        # Arama kelimesini ayıkla
        clean_keyword = self._clean_keyword_string(user_message)
        
        # Eğer temizlenmiş kelime boş kaldıysa ama önceki geçmişte konu varsa
        if not clean_keyword and history:
            for m in reversed(history):
                if m.get("role") == "user":
                    candidate = self._clean_keyword_string(m.get("content", ""))
                    if candidate:
                        clean_keyword = candidate
                        break
                        
        if not clean_keyword:
            clean_keyword = user_message.strip()

        from processors.expander import KeywordExpander
        exp = KeywordExpander.expand(clean_keyword)
        rel_list = exp.get("related_keywords", [])
        if rel_list:
            detail_msg = f"'{clean_keyword}' ve otomatik türetilen ilişkili konular ({', '.join(rel_list[:4])}) taranıyor..."
        else:
            detail_msg = f"'{clean_keyword}' konusu için içerik üreticileri aranıyor..."
            
        f_details = []
        if min_followers:
            f_details.append(f"Min: {min_followers:,}")
        if max_followers:
            f_details.append(f"Maks: {max_followers:,}")
        if f_details:
            detail_msg += f" (Filtre: {', '.join(f_details)} takipçi)"

        return {
            "text": detail_msg,
            "action": "search",
            "params": {
                "keyword": clean_keyword,
                "min_followers": min_followers,
                "max_followers": max_followers,
                "platforms": platforms
            }
        }

    def _clean_keyword_string(self, text: str) -> str:
        """Kullanıcı cümlesinden konuşma dolgu sözcüklerini ve filtreleri temizleyip salt arama terimini çıkarır."""
        if not text:
            return ""
            
        s = text
        # 'hedef kitlem X' yapısı varsa doğrudan X kısmını al
        hk_match = re.search(r'hedef\s+kitlem\s+([a-zA-ZçğıöşüÇĞİÖŞÜ0-9\s]+?)(?:için|arıyorum|bul|\.|$)', s, re.IGNORECASE)
        if hk_match:
            extracted = hk_match.group(1).strip()
            if len(extracted.split()) <= 4:
                return extracted

        # Dolgu cümlelerini temizle
        noise_phrases = [
            r'platformlara\s+homojen\s+şekilde\s+ağırlık\s+ver',
            r'homojen\s+şekilde\s+ağırlık\s+ver',
            r'homojen\s+şekilde',
            r'ağırlık\s+ver',
            r'tüm\s+platformlar(?:da|dan)?',
            r'hedef\s+kitlem',
            r'hedef\s+kitle',
            r'kişileri\s+arıyorum',
            r'kişileri\s+bul',
            r'kişileri',
            r'insanları\s+arıyorum',
            r'içerik\s+üreticilerini',
            r'içerik\s+üreticileri',
            r'influencerları',
            r'influencerlarını',
            r'hesapları',
            r'kanalları',
            r'bana\s+bul',
            r'bana\s+getir',
            r'bana\s+öner',
            r'bana\s+listele',
            r'bana',
            r'lütfen',
            r'arıyorum',
            r'istiyorum',
            r'bulur\s+musun',
            r'bulabilir\s+misin',
            r'önerir\s+misin',
            r'listeler\s+misin',
            r'listele',
            r'getir',
            r'bul',
            r'ara',
            r'olan',
            r'için',
            r'hakkında',
            r'üzerine'
        ]
        for np in noise_phrases:
            s = re.sub(rf'\b{np}\b', ' ', s, flags=re.IGNORECASE)

        # Sayı ve filtre aralıklarını temizle (1000-15000 arası takipçili vb.)
        s = re.sub(r'\d+[\.,]?\d*[km]?\s*(?:ile|-)?\s*\d*[\.,]?\d*[km]?\s*(?:arası|üzeri|üstü|altı|kadar|en az|en fazla|minimum|maksimum)?', ' ', s, flags=re.IGNORECASE)
        s = re.sub(r'\btakipçili\b', ' ', s, flags=re.IGNORECASE)
        s = re.sub(r'\btakipçi\b', ' ', s, flags=re.IGNORECASE)

        # Fazla boşlukları temizle
        s = re.sub(r'\s+', ' ', s).strip()
        # Başındaki ve sonundaki noktalama işaretlerini sil
        s = s.strip('.,;:-_!?"\'')
        return s


