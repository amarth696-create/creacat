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
            if min_followers and getattr(creator, 'followers', 0) < min_followers:
                continue
                
            max_followers = filters.get('max_followers')
            if max_followers and getattr(creator, 'followers', 0) > max_followers:
                continue
                
            # Ülke filtresi (alias destekli)
            country = filters.get('country')
            if country:
                c_str = str(country).lower().strip()
                allowed_c = {"tr", "tur", "turkey", "türkiye"} if c_str in ["tr", "turkey", "türkiye"] else {c_str}
                cr_c = str(getattr(creator, 'country', '') or '').lower().strip()
                if cr_c and cr_c not in allowed_c:
                    continue
                
            # Dil filtresi (alias destekli)
            language = filters.get('language')
            if language:
                l_str = str(language).lower().strip()
                allowed_l = {"tr", "tur", "turkish", "türkçe"} if l_str in ["tr", "turkish", "türkçe"] else {l_str}
                cr_l = str(getattr(creator, 'language', '') or '').lower().strip()
                if cr_l and cr_l not in allowed_l:
                    continue
                
            filtered_creators.append(creator)
            
        return filtered_creators

