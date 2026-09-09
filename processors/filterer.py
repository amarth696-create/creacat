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
        
    def _meets_criteria(self, creator: Creator, filters: dict) -> bool:
        """İçerik üreticisinin tüm filtrelere uyup uymadığını kontrol eder."""
        if not filters:
            return True
            
        followers = getattr(creator, 'followers', 0)
        
        if 'min_followers' in filters and followers < filters['min_followers']:
            return False
            
        if 'max_followers' in filters and filters['max_followers'] is not None and filters['max_followers'] > 0:
            if followers > filters['max_followers']:
                return False
            
        if 'country' in filters and filters['country']:
            creator_country = getattr(creator, 'country', None)
            if not creator_country or creator_country.lower() != filters['country'].lower():
                return False
                
        if 'language' in filters and filters['language']:
            creator_lang = getattr(creator, 'language', None)
            if not creator_lang or creator_lang.lower() != filters['language'].lower():
                return False
                
        if 'min_engagement_rate' in filters:
            rate = getattr(creator, 'engagement_rate', 0.0) or 0.0
            if rate < filters['min_engagement_rate']:
                return False
                
        if 'platforms' in filters and filters['platforms']:
            platform = getattr(creator, 'platform', '')
            if platform.lower() not in [p.lower() for p in filters['platforms']]:
                return False
                
        return True
