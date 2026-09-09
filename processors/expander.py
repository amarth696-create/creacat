import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class KeywordExpander:
    """
    Kullanıcının girdiği tekil anahtar kelimeleri (örn: 'öğrencilik') analiz ederek
    otomatik olarak sektörle ilgili eş anlamlı arama kelimeleri, alt nişler
    ve sosyal medya hashtag'lerini türetir.
    """
    
    TAXONOMY = {
        "öğrenci": {
            "related_keywords": [
                "üniversite hayatı", "study with me", "yks hazırlık", "ders çalışma", 
                "kütüphane vlog", "kampüs yaşamı", "öğrenci evi", "tıp öğrencisi", 
                "hukuk öğrencisi", "studygram", "pomodoro çalışma", "bölüm tavsiyeleri"
            ],
            "hashtags": [
                "#studywithme", "#yks2026", "#öğrencilik", "#üniversitehayatı", 
                "#dersçalışma", "#kütüphane", "#vizehaftası", "#studygram", 
                "#kampüshayatı", "#tıpöğrencisi", "#hukuköğrencisi", "#ykskoçluk"
            ],
            "sub_niches": [
                "study vlog", "üniversite hayatı", "ders çalışma günlüğü", 
                "yks hazırlık", "kütüphane günlüğü", "öğrenci evi", "bölüm rehberi"
            ],
            "queries": [
                "öğrenci vlog", "study with me türkiye", "üniversite ders çalışma", 
                "vize haftası kütüphane", "yks öğrencisi", "üniversite kütüphane sabahlaması"
            ]
        },
        "fitness": {
            "related_keywords": [
                "vücut geliştirme", "gym motivasyon", "antrenman programı", "sağlıklı beslenme", 
                "kilo verme", "evde spor", "diyet tarifleri", "sporcu beslenmesi", "pilates"
            ],
            "hashtags": [
                "#sporgünlüğü", "#fitnesstürkiye", "#vücutgeliştirme", "#sağlıklıbeslenme",
                "#antrenman", "#evdespor", "#diyetisyen", "#sporcubeslenmesi", "#gymmotivation"
            ],
            "sub_niches": [
                "vücut geliştirme", "evde antrenman", "kilo verme günlüğü", 
                "fitness koçluğu", "sağlıklı tarifler", "pilates & yoga"
            ],
            "queries": [
                "fitness motivasyon", "antrenman programı", "günlük spor rutinim", "sağlıklı yaşam rehberi"
            ]
        },
        "teknoloji": {
            "related_keywords": [
                "yazılım geliştirme", "kodlama", "yapay zeka", "python dersleri", 
                "teknoloji inceleme", "yazılımcı günlüğü", "setup rehberi", "web geliştirme"
            ],
            "hashtags": [
                "#yazılımgeliştirme", "#yapayzeka", "#kodlama", "#teknolojihaberleri",
                "#pythonöğreniyorum", "#setuprehberi", "#webgeliştirme", "#yazılımcı"
            ],
            "sub_niches": [
                "yazılım eğitimi", "yapay zeka araçları", "ürün inceleme", 
                "yazılımcı günlüğü", "masa kurulumu (setup)", "donanım testi"
            ],
            "queries": [
                "yazılım öğrenme rehberi", "kodlama günlüğüm", "yapay zeka dersleri", "teknoloji inceleme"
            ]
        },
        "moda": {
            "related_keywords": [
                "kombin önerileri", "grwm benimle hazırlanın", "cilt bakımı", 
                "uygun fiyatlı alışveriş", "moda haftası", "makyaj tüyoları", "kapsül dolap"
            ],
            "hashtags": [
                "#kombinönerileri", "#modablogu", "#gününoutfiti", "#alisverisonerileri",
                "#grwm", "#makyajgünlüğü", "#skincare", "#koreanskincare"
            ],
            "sub_niches": [
                "günlük kombinler", "cilt bakımı rutini", "grwm (hazırlanma vlogu)", 
                "uygun fiyatlı alışveriş", "kapsül dolap"
            ],
            "queries": [
                "kombin önerileri", "grwm benimle hazırlanın", "cilt bakımı tüyoları", "haftalık alışveriş"
            ]
        },
        "gezi": {
            "related_keywords": [
                "seyahat vlog", "tatil rotaları", "ucuz bütçeli seyahat", 
                "kamp ve doğa", "karavan hayatı", "yurtdışı rehberi", "sırt çantalı gezgin"
            ],
            "hashtags": [
                "#geziyolu", "#seyahatgünlüğü", "#kampvedoga", "#interrail",
                "#vizesizülkeler", "#seyahatrehberi", "#karavangünlükleri", "#tatilrotaları"
            ],
            "sub_niches": [
                "sırt çantalı gezgin", "ucuz bütçeli seyahat", "kamp ve doğa", 
                "yurtdışı rehberi", "karavan hayatı", "şehir turları"
            ],
            "queries": [
                "seyahat vlog", "ucuz tatil rotaları", "kamp hayatı günlüğü", "sırt çantasıyla avrupa"
            ]
        },
        "yemek": {
            "related_keywords": [
                "pratik tarifler", "öğrenci evi yemekleri", "sokak lezzetleri", 
                "tatlı tarifleri", "mekan önerisi", "akşam yemeği menüsü", "fit tarifler"
            ],
            "hashtags": [
                "#yemektarifleri", "#pratiktarifler", "#lezzetliikramlar", "#sokaklezzetleri",
                "#mutfaksırları", "#mekanönerisi", "#kahvaltısofrası", "#fittarifler"
            ],
            "sub_niches": [
                "öğrenci dostu pratik yemekler", "sokak lezzetleri turu", 
                "fit tatlı tarifleri", "mekan inceleme", "dünya mutfağı"
            ],
            "queries": [
                "pratik akşam yemeği", "öğrenci evi yemekleri", "lezzetli tarifler", "istanbul mekan rehberi"
            ]
        },
        "finans": {
            "related_keywords": [
                "borsa istanbul", "finansal okuryazarlık", "tasarruf yöntemleri", 
                "yatırım rehberi", "pasif gelir", "öğrenci bütçe yönetimi", "hisse analizi"
            ],
            "hashtags": [
                "#finansalyatırım", "#borsaistanbul", "#tasarruf", "#kriptopara",
                "#finansalözgürlük", "#bütçeyönetimi", "#yatırımtavsiyeleri"
            ],
            "sub_niches": [
                "finansal okuryazarlık", "tasarruf yöntemleri", "hisse analizi", 
                "pasif gelir", "bütçe planlama"
            ],
            "queries": [
                "finansal özgürlük rehberi", "öğrenci bütçe yönetimi", "borsa temel analiz", "tasarruf tüyoları"
            ]
        },
        "oyun": {
            "related_keywords": [
                "oyun incelemeleri", "türkçe gameplay", "bağımsız oyunlar", 
                "espor rehberi", "gaming setup", "twitch yayınları", "komik anlar"
            ],
            "hashtags": [
                "#oyunvideolari", "#oyunsever", "#gamerlife", "#twitchtürkiye",
                "#valoranttürkiye", "#indieoyunlar", "#oyunistatistikleri"
            ],
            "sub_niches": [
                "hikayeli oyun incelemeleri", "indie oyunlar", "espor rehberi", 
                "gameplay ve komik anlar", "oyun haberleri"
            ],
            "queries": [
                "oyun inceleme türkçe", "gameplay walkthrough", "bağımsız oyun önerileri", "en iyi sistem oyunları"
            ]
        }
    }

    @classmethod
    def generate_ai_keywords(cls, keyword: str, api_key: str = "") -> Optional[Dict[str, Any]]:
        """Gemini kullanarak herhangi bir niş için anında ilgili arama terimlerini ve hashtag'leri türetir."""
        if not api_key:
            return None
            
        prompt = f"""
Sen bir sosyal medya ve arama keşif uzmanısın.
Kullanıcı '{keyword}' konusunda Türkiye'de YouTube, Instagram ve TikTok üzerinde içerik üreten kişileri arıyor.

GÖREV:
'{keyword}' kelimesiyle doğrudan ilişkili, içerik üreticilerini ve videolarını keşfetmek için kullanılabilecek:
1. En alakalı 6-8 alternatif arama terimini (keyword/tamlamayı) üret.
2. En popüler 6-8 platform hashtag'ini üret.

SADECE geçerli bir JSON nesnesi döndür:
{{
  "related_keywords": ["ilgili_kelime_1", "ilgili_kelime_2", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}}
"""
        try:
            raw_text = None
            try:
                import google.genai as new_genai
                client = new_genai.Client(api_key=api_key)
                for m in ['gemini-3.6-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
                    try:
                        res = client.models.generate_content(model=m, contents=prompt)
                        if res and hasattr(res, 'text') and res.text:
                            raw_text = res.text
                            break
                    except Exception:
                        continue
            except Exception:
                pass
                
            if not raw_text:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    for m in ['gemini-3.6-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
                        try:
                            model = genai.GenerativeModel(m)
                            res = model.generate_content(prompt)
                            if res and hasattr(res, 'text') and res.text:
                                raw_text = res.text
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
                    
            if raw_text:
                cleaned = raw_text.strip()
                s = cleaned.find("{")
                e = cleaned.rfind("}")
                if s != -1 and e != -1 and e > s:
                    data = json.loads(cleaned[s:e+1])
                    if isinstance(data.get("related_keywords"), list) and data.get("related_keywords"):
                        return {
                            "related_keywords": [str(k).strip() for k in data["related_keywords"]],
                            "hashtags": [str(h).strip() if str(h).startswith('#') else f"#{h}" for h in data.get("hashtags", [])]
                        }
        except Exception as e:
            logger.debug(f"AI keyword generation skipped: {e}")
            
        return None
    
    @classmethod
    def expand(cls, keyword: str, api_key: str = "") -> Dict[str, Any]:
        """
        Anahtar kelimeyi analiz ederek:
        - Otomatik türetilen ilgili arama kelimelerini (related_keywords)
        - Hashtag'leri (hashtags)
        - Alt nişleri (sub_niches)
        döndürür.
        """
        clean_kw = keyword.lower().strip()
        
        # 1. Önce kural/taksonomi tabanından eşleştirme ara
        matched_cat = None
        cat_data = None
        for cat_key, c_data in cls.TAXONOMY.items():
            if (cat_key in clean_kw or 
                (cat_key == "öğrenci" and any(k in clean_kw for k in ["öğrenci", "öğrencilik", "yks", "üniversite", "ders", "okul", "lise", "tıp", "sınav"])) or
                (cat_key == "fitness" and any(k in clean_kw for k in ["spor", "gym", "diyet", "kilo", "sağlık"])) or
                (cat_key == "teknoloji" and any(k in clean_kw for k in ["yazılım", "kod", "bilgisayar", "ai", "yapay zeka"])) or
                (cat_key == "moda" and any(k in clean_kw for k in ["giyim", "kombin", "makyaj", "bakım", "estetik"])) or
                (cat_key == "gezi" and any(k in clean_kw for k in ["seyahat", "tatil", "tur", "kamp", "karavan"])) or
                (cat_key == "yemek" and any(k in clean_kw for k in ["tarif", "lezzet", "tatlı", "mutfak", "pasta"])) or
                (cat_key == "finans" and any(k in clean_kw for k in ["borsa", "para", "kripto", "yatırım", "bütçe"])) or
                (cat_key == "oyun" and any(k in clean_kw for k in ["gamer", "gaming", "espor", "game"]))):
                
                matched_cat = cat_key
                cat_data = c_data
                break
                
        if cat_data:
            related_kws = list(cat_data.get("related_keywords", []))
            hashtags = list(cat_data.get("hashtags", []))
            sub_niches = list(cat_data.get("sub_niches", []))
            queries = list(cat_data.get("queries", []))
            
            return {
                "primary_keyword": keyword,
                "matched_category": matched_cat,
                "related_keywords": related_kws,
                "hashtags": hashtags,
                "sub_niches": sub_niches,
                "queries": queries,
                "all_search_terms": [keyword] + [k for k in related_kws if k.lower() != clean_kw]
            }
            
        # 2. Eğer taksonomide yoksa, AI ile dinamik türetmeyi dene
        ai_data = cls.generate_ai_keywords(keyword, api_key)
        if ai_data:
            return {
                "primary_keyword": keyword,
                "matched_category": "dinamik_ai",
                "related_keywords": ai_data["related_keywords"],
                "hashtags": ai_data["hashtags"],
                "sub_niches": ai_data["related_keywords"][:3],
                "queries": [f"{k} vlog" for k in ai_data["related_keywords"][:4]],
                "all_search_terms": [keyword] + ai_data["related_keywords"]
            }
            
        # 3. Son çare jenerik türetme
        tag_base = re.sub(r'[^a-zA-Z0-9çğıöşüÇĞİÖŞÜ]', '', clean_kw)
        generic_rel = [
            f"{clean_kw} vlog",
            f"{clean_kw} tavsiyeleri",
            f"{clean_kw} rehberi",
            f"{clean_kw} deneyimleri",
            f"{clean_kw} günlük yaşam"
        ]
        generic_tags = [
            f"#{tag_base}",
            f"#{tag_base}vlog",
            f"#{tag_base}türkiye",
            f"#{tag_base}rehberi",
            f"#{tag_base}önerileri",
            f"#{tag_base}günlüğü"
        ]
        
        return {
            "primary_keyword": keyword,
            "matched_category": "genel",
            "related_keywords": generic_rel,
            "hashtags": generic_tags,
            "sub_niches": [f"{clean_kw} içerikleri", f"{clean_kw} rehberliği"],
            "queries": generic_rel,
            "all_search_terms": [keyword] + generic_rel
        }
