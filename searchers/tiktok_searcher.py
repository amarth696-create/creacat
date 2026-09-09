import asyncio
import subprocess
import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from searchers.base import BaseSearcher
from models.creator import Creator
from utils.stealth import apply_stealth_async

class TikTokSearcher(BaseSearcher):
    """
    Playwright ve yt-dlp kullanarak TikTok'ta influencer araması yapar.
    """
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config

    @property
    def platform_name(self) -> str:
        return "TikTok"

    def search(self, query: str, limit: int = 50) -> List[Creator]:
        """ara metodu için alias."""
        return self.ara(query, {"limit": limit})
        
    def ara(self, keyword: str, filters: Dict[str, Any] = None) -> List[Creator]:
        """Senkron sarmalayıcı (wrapper) metot."""
        if filters is None:
            filters = {}
        return asyncio.run(self._async_ara(keyword, filters))
        
    async def _async_ara(self, keyword: str, filters: Dict[str, Any]) -> List[Creator]:
        creators = []
        try:
            self.logger.info(f"TikTok üzerinde '{keyword}' için Playwright ile arama başlatılıyor...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Adım b: Stealth ayarlarını uygula
                await apply_stealth_async(page)
                
                # Adım a: Arama sayfasına git
                search_url = f"https://www.tiktok.com/search?q={keyword}"
                await page.goto(search_url, wait_until="networkidle")
                
                # Adım c: Bekle ve aşağı kaydır
                await page.wait_for_timeout(3000)
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)
                
                # Adım d & e: Video kartlarını ayrıştır ve benzersiz kullanıcı adlarını çıkar
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                usernames = set()
                # Not: TikTok DOM yapısı değişebilir, genel bir seçim kullanıyoruz
                user_links = soup.select('a[href^="/@"]')
                for link in user_links:
                    href = link.get('href', '')
                    if href.startswith('/@'):
                        username = href.split('?')[0].strip('/').replace('@', '')
                        if username:
                            usernames.add(username)
                            
                self.logger.info(f"TikTok'ta {len(usernames)} benzersiz kullanıcı bulundu.")
                
                # Adım f & g: Profilleri ziyaret et
                for username in list(usernames)[:10]: # Sınır koyalım
                    try:
                        self.rate_limiter.wait()
                        profile_url = f"https://www.tiktok.com/@{username}"
                        await page.goto(profile_url, wait_until="networkidle")
                        await page.wait_for_timeout(2000)
                        
                        profile_html = await page.content()
                        p_soup = BeautifulSoup(profile_html, 'html.parser')
                        
                        # Bu seçiciler tahmini değerlerdir ve TikTok güncellemelerine göre değişebilir
                        followers_el = p_soup.select_one('[data-e2e="followers-count"]')
                        likes_el = p_soup.select_one('[data-e2e="likes-count"]')
                        bio_el = p_soup.select_one('[data-e2e="user-bio"]')
                        
                        followers_text = followers_el.text if followers_el else "0"
                        likes_text = likes_el.text if likes_el else "0"
                        bio = bio_el.text if bio_el else ""
                        
                        # Sayıları parse et (Örn: 1.2M -> 1200000)
                        followers = self._parse_number(followers_text)
                        likes = self._parse_number(likes_text)
                        
                        creator = Creator(
                            username=username,
                            platform='TikTok',
                            followers=followers,
                            profile_url=profile_url,
                            bio=bio
                        )
                        
                        # Adım h: Görünür video istatistiklerinden etkileşim hesapla
                        if followers > 0:
                            creator.engagement_rate = (likes / followers) * 100
                        else:
                            creator.engagement_rate = 0.0
                            
                        creators.append(creator)
                    except Exception as e:
                        self.logger.warning(f"'{username}' profili Playwright ile çekilirken hata: {str(e)}")
                        
                await browser.close()
                
            return self._apply_basic_filters(creators, filters)
            
        except Exception as e:
            self.logger.error(f"Playwright hatası, yt-dlp yedek sistemine geçiliyor: {str(e)}")
            return self._ytdlp_fallback(keyword, filters)
            
    def _ytdlp_fallback(self, keyword: str, filters: Dict[str, Any]) -> List[Creator]:
        """yt-dlp kullanarak arama yapar (yedek yöntem)."""
        creators = []
        self.logger.info(f"yt-dlp ile '{keyword}' araması başlatılıyor...")
        
        try:
            url = f"ytsearch10:{keyword} tiktok"
            result = subprocess.run(
                ['yt-dlp', '-J', '--flat-playlist', url],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            entries = data.get('entries', [])
            
            usernames = set()
            for entry in entries:
                uploader = entry.get('uploader')
                if uploader:
                    usernames.add(uploader)
                    
            for username in usernames:
                creator = Creator(
                    username=username,
                    platform='TikTok',
                    followers=0, # yt-dlp ile sadece profil adını alıyoruz
                    profile_url=f"https://www.tiktok.com/@{username}",
                    bio="yt-dlp ile bulundu"
                )
                creators.append(creator)
                
            return creators
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"yt-dlp araması başarısız oldu: {e.stderr}")
        except Exception as e:
            self.logger.error(f"yt-dlp yedeğinde beklenmeyen hata: {str(e)}")
            
        return creators
        
    def _parse_number(self, num_str: str) -> int:
        """K, M, B gibi ekleri olan sayı stringlerini tam sayıya çevirir."""
        num_str = num_str.upper().replace(',', '.')
        try:
            if 'K' in num_str:
                return int(float(num_str.replace('K', '')) * 1000)
            elif 'M' in num_str:
                return int(float(num_str.replace('M', '')) * 1000000)
            elif 'B' in num_str:
                return int(float(num_str.replace('B', '')) * 1000000000)
            else:
                return int(float(num_str))
        except ValueError:
            return 0
