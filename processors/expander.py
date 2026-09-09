import re
from typing import Dict, List, Any

class KeywordExpander:
    """
    Kullanıcının girdiği tekil anahtar kelimeleri analiz ederek
    ilgili hashtag'ler (#studywithme, #yks2026), alt nişler ve eş anlamlı
    arama sorgularına genişletir.
    """
    
    TAXONOMY = {
        "öğrenci": {
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
                "vize haftası kütüphane", "yks öğrencisi"
            ]
        },
        "fitness": {
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
    def expand(cls, keyword: str) -> Dict[str, Any]:
        """
        Anahtar kelimeyi analiz ederek ilgili hashtag ve niş terimleri döndürür.
        """
        clean_kw = keyword.lower().strip()
        
        # Önceden tanımlı haritalamayı kontrol et
        for cat_key, cat_data in cls.TAXONOMY.items():
            if (cat_key in clean_kw or 
                (cat_key == "öğrenci" and any(k in clean_kw for k in ["öğrenci", "öğrencilik", "yks", "üniversite", "ders", "okul", "lise", "tıp", "sınav"])) or
                (cat_key == "fitness" and any(k in clean_kw for k in ["spor", "gym", "diyet", "kilo", "sağlık"])) or
                (cat_key == "teknoloji" and any(k in clean_kw for k in ["yazılım", "kod", "bilgisayar", "ai", "yapay zeka"])) or
                (cat_key == "moda" and any(k in clean_kw for k in ["giyim", "kombin", "makyaj", "bakım", "estetik"])) or
                (cat_key == "gezi" and any(k in clean_kw for k in ["seyahat", "tatil", "tur", "kamp", "karavan"])) or
                (cat_key == "yemek" and any(k in clean_kw for k in ["tarif", "lezzet", "tatlı", "mutfak", "pasta"])) or
                (cat_key == "finans" and any(k in clean_kw for k in ["borsa", "para", "kripto", "yatırım", "bütçe"])) or
                (cat_key == "oyun" and any(k in clean_kw for k in ["gamer", "gaming", "espor", "game"]))):
                
                return {
                    "primary_keyword": keyword,
                    "matched_category": cat_key,
                    "hashtags": cat_data["hashtags"],
                    "sub_niches": cat_data["sub_niches"],
                    "queries": cat_data["queries"]
                }
                
        # Özel kategori bulunamadıysa jenerik genişletme yap
        tag_base = re.sub(r'[^a-zA-Z0-9çğıöşüÇĞİÖŞÜ]', '', clean_kw)
        generic_tags = [
            f"#{tag_base}",
            f"#{tag_base}vlog",
            f"#{tag_base}türkiye",
            f"#{tag_base}rehberi",
            f"#{tag_base}önerileri",
            f"#{tag_base}günlüğü"
        ]
        generic_queries = [
            f"{clean_kw} vlog",
            f"{clean_kw} tavsiyeleri",
            f"{clean_kw} rehberi",
            f"{clean_kw} günlük yaşam"
        ]
        
        return {
            "primary_keyword": keyword,
            "matched_category": "genel",
            "hashtags": generic_tags,
            "sub_niches": [f"{clean_kw} deneyimleri", f"{clean_kw} rehberliği"],
            "queries": generic_queries
        }
