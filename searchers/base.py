import abc
from typing import List, Dict, Any

from models.creator import Creator
from utils.rate_limiter import RateLimiter
from utils.logger import Logger

class BaseSearcher(abc.ABC):
    """
    Influencer arama işlemleri için temel soyut sınıf.
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.logger = Logger()
        
    @property
    @abc.abstractmethod
    def platform_name(self) -> str:
        """Platform adını döndürür."""
        pass
        
    @abc.abstractmethod
    def ara(self, keyword: str, filters: Dict[str, Any]) -> List[Creator]:
        """
        Belirtilen anahtar kelime ve filtrelere göre içerik üreticilerini arar.
        """
        pass
        
    def _apply_basic_filters(self, creators: List[Creator], filters: Dict[str, Any]) -> List[Creator]:
        """
        Temel filtreleri (minimum takipçi, ülke, dil) uygular.
        """
        filtered_creators = []
        for creator in creators:
            # Minimum takipçi filtresi
            min_followers = filters.get('min_followers', 0)
            if getattr(creator, 'followers', 0) < min_followers:
                continue
                
            # Ülke filtresi
            country = filters.get('country')
            if country and getattr(creator, 'country', None) != country:
                continue
                
            # Dil filtresi
            language = filters.get('language')
            if language and getattr(creator, 'language', None) != language:
                continue
                
            filtered_creators.append(creator)
            
        return filtered_creators
