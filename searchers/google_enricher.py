import time
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from utils.logger import Logger

class GoogleEnricher:
    """
    Google araması üzerinden ek influencer profilleri keşfeden destekleyici modül.
    Çok agresif rate limiting kullanır.
    """
    
    def __init__(self, config=None):
        self.config = config
        self.logger = Logger()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def enrich(self, creator):
        """Creator nesnesini ek Google verileriyle zenginleştirir."""
        return creator
        
    def ara(self, keyword: str, target_platform: str) -> List[str]:
        """
        Belirtilen platform için Google üzerinde arama yapar ve bulunan profil URL'lerini döndürür.
        """
        profile_urls = []
        platform_site = self._get_platform_site(target_platform)
        
        if not platform_site:
            self.logger.warning(f"Google Enricher için desteklenmeyen platform: {target_platform}")
            return profile_urls
            
        search_query = f'site:{platform_site} "{keyword}" "followers"'
        url = f"https://www.google.com/search?q={search_query}"
        
        self.logger.info(f"Google Zenginleştirme: '{target_platform}' için '{keyword}' aranıyor...")
        
        try:
            # Çok muhafazakar bekleme
            self.logger.info("Google araması için bekleniyor (Rate Limiting)...")
            time.sleep(15) 
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 429:
                self.logger.warning("Google aramasında CAPTCHA / 429 Too Many Requests engeli. Zenginleştirme atlanıyor.")
                return profile_urls
                
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.select('div.g a')
            
            for link in search_results:
                href = link.get('href', '')
                if platform_site in href and self._is_profile_url(href, target_platform):
                    profile_urls.append(href)
                    
            # Benzersiz URL'leri al
            profile_urls = list(set(profile_urls))
            self.logger.info(f"Google Zenginleştirme sonucunda {len(profile_urls)} adet potansiyel profil bulundu.")
            
            return profile_urls
            
        except requests.RequestException as e:
            self.logger.error(f"Google aramasında ağ hatası: {str(e)}")
            return profile_urls
        except Exception as e:
            self.logger.error(f"Google zenginleştirmede beklenmeyen hata: {str(e)}")
            return profile_urls
            
    def _get_platform_site(self, platform: str) -> Optional[str]:
        platform = platform.lower()
        if platform == 'tiktok':
            return 'tiktok.com'
        elif platform == 'instagram':
            return 'instagram.com'
        elif platform == 'youtube':
            return 'youtube.com'
        return None
        
    def _is_profile_url(self, url: str, platform: str) -> bool:
        """URL'nin geçerli bir profil URL'si olup olmadığını kontrol eder."""
        platform = platform.lower()
        if platform == 'tiktok':
            return '/@' in url and '/video/' not in url
        elif platform == 'instagram':
            return '/p/' not in url and '/reel/' not in url
        elif platform == 'youtube':
            return '/channel/' in url or '/c/' in url or '/@' in url
        return True
