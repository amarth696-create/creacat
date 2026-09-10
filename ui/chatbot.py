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
Sistemimizde sol kenar çubuğundaki filtreler tamamen kaldırılmıştır; filtreleme artık seninle kullanıcı arasındaki bu sohbet üzerinden yönetilmektedir.

SOHBET GEÇMİŞİ:
{history_str if history_str else '(Henüz geçmiş yok)'}

KULLANICININ SON MESAJI:
{user_message}

GÖREVLERİN VE MANTIK AKIŞI:
1. SOHBET GEÇMİŞİNİ VE SON MESAJI BİRLİKTE ANALİZ ET:
   - Aranmak istenen bir kategori, konu veya niş var mı? (Örn: 'dizi ve filmler', 'seyahat', 'teknoloji', 'üniversite öğrencileri', 'fitness')
   - Kullanıcı platform belirtti mi? (YouTube, Instagram, TikTok veya 'hepsi / tümü / fark etmez')
   - Kullanıcı takipçi aralığı/büyüklüğü belirtti mi? (Örn: '10k+', '50k-200k', 'mikro', 'makro', veya 'fark etmez / hepsi / sınırsız')

2. EKSİK FİLTRE VE SORU SORMA KURALI ('action': 'clarify'):
   - Eğer kullanıcı bir arama konusu/nişi belirtti AMA mesajında veya önceki sohbet geçmişinde platform VE/VEYA takipçi aralığı henüz netleşmediyse (ve 'fark etmez / hepsi' denmediyse):
     ARAMAYI HEMEN BAŞLATMA!
     Kullanıcıya nazik, profesyonel bir dille konuyu anladığını belirt ve eksik kalan kriterleri sor:
     * Hangi platformlara odaklanalım? (YouTube, Instagram, TikTok veya Hepsi)
     * Belirli bir takipçi kitlesi (mikro 10k-50k, makro 100k+ vb.) arıyor musunuz yoksa fark etmez mi?
     
     Bu durumda JSON yanıtı:
     {{
       "action": "clarify",
       "candidate_topic": "tespit_edilen_konu",
       "reply_text": "Kullanıcıya gösterilecek kibar, maddeli soru metni"
     }}

3. TÜM KRİTERLER TAMAMSA VEYA KULLANICI SORULARA CEVAP VERDİYSE ('action': 'search'):
   - Eğer kullanıcı ilk mesajında hem konuyu hem tercihleri belirttiyse (örn: 'youtube da 50k üzeri dizi eleştirmenleri'), VEYA önceki soruna istinaden filtre tercihlerini ilettiyse (örn: 'youtube ve tiktok olsun 50k üstü', 'hepsi olsun fark etmez' vb.):
     Aksiyonu 'search' yap!
     - 'keyword': Sosyal medya platformlarında (YouTube, Instagram, TikTok) arama yapmak için kullanılacak EN NET, EN KISA arama kelimesini veya tamlamasını çıkar (Örn: 'dizi film', 'seyahat', 'üniversite öğrencileri'). Kullanıcının konuşma dolgularını ('bana bul', 'homojen ağırlık ver', 'istiyorum' vb.) ASLA keyword içine koyma.
     - 'platforms': Kullanıcının seçtiği platform listesi (örn: ["YouTube", "TikTok"]). 'Hepsi' veya 'fark etmez' dendiyse: ["YouTube", "TikTok", "Instagram"].
     - 'min_followers': Varsa tam sayı (örn: 50000), yoksa null.
     - 'max_followers': Varsa tam sayı (örn: 200000), yoksa null.
     - 'reply_text': Kullanıcıya gösterilecek kibar Türkçe onay cümlesi.

4. GENEL SOHBET VEYA SELAMLAŞMA ('action': 'chat'):
   - Kullanıcı sadece 'merhaba', 'selam', 'nasılsın' dediyse ve aranacak bir konu yoksa:
     Aksiyonu 'chat' yap. Nasıl yardımcı olabileceğini, hangi alanda influencer keşfetmek istediğini sor.

YANIT FORMATI:
Yalnızca geçerli bir JSON nesnesi döndür. Markdown kod bloğu olmadan saf JSON ver:
{{
  "action": "search",
  "keyword": "kısa_arama_kelimesi",
  "candidate_topic": "tespit_edilen_konu",
  "min_followers": null,
  "max_followers": null,
  "platforms": ["YouTube", "TikTok", "Instagram"],
  "reply_text": "Kullanıcıya gösterilecek Türkçe mesaj"
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
                raw_kw = parsed.get("keyword") or parsed.get("candidate_topic") or ""
                clean_kw = self._clean_keyword_string(raw_kw) or self._clean_keyword_string(user_message)
                
                min_f = parsed.get("min_followers")
                max_f = parsed.get("max_followers")
                plats = parsed.get("platforms") or ["YouTube", "TikTok", "Instagram"]
                
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
            elif action == "clarify":
                return {
                    "text": parsed.get("reply_text") or "Hangi platformlarda ve hangi takipçi aralığında arama yapmamı istersiniz?",
                    "action": None,
                    "params": None
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
                "text": "Merhaba! Hangi kategoride veya nişte (örneğin teknoloji, seyahat, dizi/film, fitness vb.) içerik üreticisi keşfetmek istersiniz?",
                "action": None,
                "params": None
            }

        # Platform tespiti
        platforms = []
        has_platform = False
        if "youtube" in lower_msg:
            platforms.append("YouTube")
            has_platform = True
        if "tiktok" in lower_msg:
            platforms.append("TikTok")
            has_platform = True
        if "instagram" in lower_msg:
            platforms.append("Instagram")
            has_platform = True
        if any(w in lower_msg for w in ["hepsi", "tümü", "tüm platformlar", "fark etmez", "farketmez"]):
            platforms = ["YouTube", "TikTok", "Instagram"]
            has_platform = True
        if not platforms:
            platforms = ["YouTube", "TikTok", "Instagram"]

        # Takipçi aralığı tespiti
        min_followers = None
        max_followers = None
        has_followers = False

        if "mikro" in lower_msg:
            min_followers = 5000
            max_followers = 50000
            has_followers = True
        elif "makro" in lower_msg:
            min_followers = 100000
            has_followers = True
        elif "nano" in lower_msg:
            min_followers = 1000
            max_followers = 10000
            has_followers = True
        elif any(w in lower_msg for w in ["fark etmez", "farketmez", "sınır yok", "sınırsız", "hepsi"]):
            has_followers = True

        range_match = re.search(r'(\d+[\.,]?\d*[km]?)\s*(?:ile|-)\s*(\d+[\.,]?\d*[km]?)\s*arası', lower_msg)
        if range_match:
            min_followers = _parse_num_text(range_match.group(1))
            max_followers = _parse_num_text(range_match.group(2))
            has_followers = True
        else:
            min_match = re.search(r'(?:en az|minimum|min)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:üzeri|üstü|\+)', lower_msg)
            if min_match:
                min_followers = _parse_num_text(min_match.group(1) or min_match.group(2))
                has_followers = True
                
            max_match = re.search(r'(?:en fazla|en çok|maksimum|maks|max)\s*(\d+[\.,]?\d*[km]?)|(\d+[\.,]?\d*[km]?)\s*(?:altı|kadar)', lower_msg)
            if max_match:
                max_followers = _parse_num_text(max_match.group(1) or max_match.group(2))
                has_followers = True

        # Sohbet geçmişinde daha önce filtre sorusu sorulmuş mu?
        asked_clarification = False
        prev_topic = None
        if history:
            for m in reversed(history):
                if m.get("role") == "assistant" and any(k in m.get("content", "") for k in ["Hangi platformlara odaklanalım", "tercihlerinizi netleştirelim", "Platform:", "Takipçi Kitlesi"]):
                    asked_clarification = True
                    break
            if asked_clarification:
                for m in reversed(history):
                    if m.get("role") == "user":
                        cand = self._clean_keyword_string(m.get("content", ""))
                        if cand and len(cand) >= 3 and not any(p.lower() in cand.lower() for p in ["youtube", "tiktok", "instagram"]):
                            prev_topic = cand
                            break

        # Arama kelimesini ayıkla
        clean_keyword = self._clean_keyword_string(user_message)

        # Eğer kullanıcı daha önce sorulan filtre sorusuna yanıt veriyorsa:
        if asked_clarification and prev_topic:
            clean_keyword = prev_topic
        elif not has_platform and not has_followers:
            # Kullanıcı konu belirtti ama filtre belirtmedi -> Filtreleri sor!
            if clean_keyword and len(clean_keyword) >= 2:
                clarify_text = (
                    f"**'{clean_keyword.title()}'** konusunda içerik üreticilerini araştırmaya başlayabilirim! 🎬\n\n"
                    f"Aramayı başlatmadan önce tercihlerinizi netleştirelim:\n"
                    f"1. **Platform:** Hangi platformlara odaklanalım? (YouTube, Instagram, TikTok veya Hepsi)\n"
                    f"2. **Takipçi Kitlesi / Ölçek:** Belirli bir takipçi kitlesi arıyor musunuz? (Örn: Mikro 10k-50k, Makro 100k+ veya Fark etmez / Sınırsız)\n\n"
                    f"Tercihlerinizi belirttiğinizde hemen araştırmayı başlatacağım!"
                )
                return {
                    "text": clarify_text,
                    "action": None,
                    "params": None
                }

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
            r'içerik\s+üreten\s+kişiler',
            r'içerik\s+üretenler',
            r'içerik\s+üreten',
            r'içerik\s+üreticilerini',
            r'içerik\s+üreticileri',
            r'içerik\s+üreticisi',
            r'kişileri\s+arıyorum',
            r'kişileri\s+bul',
            r'kişileri',
            r'kişiler\s+lazım',
            r'kişiler',
            r'insanları\s+arıyorum',
            r'influencerları',
            r'influencerlarını',
            r'influencerlar',
            r'influencer',
            r'hesapları',
            r'hesaplar',
            r'kanalları',
            r'kanallar',
            r'lazım',
            r'gerekiyor',
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
            r'üzerine',
            r'konusunda'
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


