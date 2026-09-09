from models.creator import Creator
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Filterer:
    """Belirli kriterlere göre içerik üreticilerini filtreler."""
    
    def __init__(self, min_followers: int = None, max_followers: int = None, 
                 country: str = None, language: str = None, 
                 min_engagement_rate: float = None, platforms: list = None):
        self.default_filters = {}
        if min_followers is not None:
            self.default_filters['min_followers'] = min_followers
        if max_followers is not None:
            self.default_filters['max_followers'] = max_followers
        if country:
            self.default_filters['country'] = country
        if language:
            self.default_filters['language'] = language
        if min_engagement_rate is not None:
            self.default_filters['min_engagement_rate'] = min_engagement_rate
        if platforms:
            self.default_filters['platforms'] = platforms

    def filter(self, creators: list[Creator], filters: dict = None) -> list[Creator]:
        """
        Filtreleme kriterlerine uymayan içerik üreticilerini eler.
        """
        effective_filters = dict(self.default_filters)
        if filters:
            effective_filters.update(filters)
        initial_count = len(creators)
        filtered_creators = []
        
        for c in creators:
            if self._meets_criteria(c, effective_filters):
                filtered_creators.append(c)
                
        filtered_out_count = initial_count - len(filtered_creators)
        logger.info(f"Filtreleme sonucu: Toplam {filtered_out_count} içerik üreticisi elendi. Kalan: {len(filtered_creators)}.")
        
        return filtered_creators
        
    COUNTRY_ALIASES = {
        "türkiye": {"tr", "tur", "turkey", "türkiye"},
        "turkey": {"tr", "tur", "turkey", "türkiye"},
        "abd": {"us", "usa", "united states", "america", "abd"},
        "almanya": {"de", "deu", "germany", "deutschland", "almanya"},
        "ingiltere": {"gb", "gbr", "uk", "united kingdom", "ingiltere"},
        "fransa": {"fr", "fra", "france", "fransa"}
    }

    LANGUAGE_ALIASES = {
        "türkçe": {"tr", "tur", "turkish", "türkçe"},
        "turkish": {"tr", "tur", "turkish", "türkçe"},
        "ingilizce": {"en", "eng", "english", "ingilizce"},
        "almanca": {"de", "deu", "german", "almanca"}
    }

    def _meets_criteria(self, creator: Creator, filters: dict) -> bool:
        """İçerik üreticisinin tüm filtrelere uyup uymadığını kontrol eder."""
        if not filters:
            return True
            
        followers = getattr(creator, 'followers', 0)
        
        if 'min_followers' in filters and filters['min_followers'] is not None and filters['min_followers'] > 0:
            if followers < filters['min_followers']:
                return False
            
        if 'max_followers' in filters and filters['max_followers'] is not None and filters['max_followers'] > 0:
            if followers > filters['max_followers']:
                return False
            
        if 'country' in filters and filters['country']:
            target_country = str(filters['country']).lower().strip()
            allowed = self.COUNTRY_ALIASES.get(target_country, {target_country})
            creator_country = str(getattr(creator, 'country', '') or '').lower().strip()
            
            # Eğer hesapta ülke bilgisi varsa ve hedef ülke ile uyuşmuyorsa ele
            if creator_country and creator_country not in allowed:
                return False
                
        if 'language' in filters and filters['language']:
            target_lang = str(filters['language']).lower().strip()
            allowed_langs = self.LANGUAGE_ALIASES.get(target_lang, {target_lang})
            creator_lang = str(getattr(creator, 'language', '') or '').lower().strip()
            
            # Eğer hesapta dil bilgisi varsa ve hedef dil ile uyuşmuyorsa ele
            if creator_lang and creator_lang not in allowed_langs:
                return False
                
        if 'min_engagement_rate' in filters and filters['min_engagement_rate'] is not None:
            rate = getattr(creator, 'engagement_rate', 0.0) or 0.0
            if rate < filters['min_engagement_rate']:
                return False
                
        if 'platforms' in filters and filters['platforms']:
            platform = getattr(creator, 'platform', '')
            if platform:
                p_str = platform.value if hasattr(platform, 'value') else str(platform)
                if p_str.lower() not in [p.lower() for p in filters['platforms']]:
                    return False
                
        return True

