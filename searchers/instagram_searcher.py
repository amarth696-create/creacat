import asyncio
from typing import List, Dict, Any

from searchers.base import BaseSearcher
from models.creator import Creator

try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False

class InstagramSearcher(BaseSearcher):
    """
    Instagram'da hashtag bazlı influencer araması yapar.
    Bu modül opsiyoneldir.
    """
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        if INSTALOADER_AVAILABLE:
            self.loader = instaloader.Instaloader(
                quiet=True,
                sleep=True,
                sanitize_paths=True
            )
        
    @property
    def platform_name(self) -> str:
        return "Instagram"

    def search(self, query: str, limit: int = 50) -> List[Creator]:
        """ara metodu için alias."""
        return self.ara(query, {"limit": limit})
        
    def ara(self, keyword: str, filters: Dict[str, Any] = None) -> List[Creator]:
        """Instagram araması başlatır."""
        if filters is None:
            filters = {}
        if not INSTALOADER_AVAILABLE:
            self.logger.warning("Instaloader kütüphanesi bulunamadı, Playwright yedeğine geçiliyor.")
            return asyncio.run(self._playwright_fallback(keyword, filters))
            
        return self._instaloader_search(keyword, filters)
        
    def _instaloader_search(self, keyword: str, filters: Dict[str, Any]) -> List[Creator]:
        creators = []
        try:
            self.logger.info(f"Instagram'da '{keyword}' hashtagi için Instaloader ile arama başlatılıyor...")
            keyword = keyword.replace('#', '')
            
            self.rate_limiter.wait()
            hashtag = instaloader.Hashtag.from_name(self.loader.context, keyword)
            
            top_posts = hashtag.get_top_posts()
            unique_profiles = set()
            
            count = 0
            for post in top_posts:
                if count >= 100:
                    break
                unique_profiles.add(post.owner_profile)
                count += 1
                
            self.logger.info(f"{len(unique_profiles)} benzersiz profil bulundu, detaylar çekiliyor...")
            
            for profile in list(unique_profiles)[:10]: # Limitleme
                try:
                    self.rate_limiter.wait()
                    
                    creator = Creator(
                        username=profile.username,
                        platform='Instagram',
                        followers=profile.followers,
                        profile_url=f"https://www.instagram.com/{profile.username}/",
                        bio=profile.biography
                    )
                    
                    # Son gönderilerden etkileşim hesapla
                    post_count = 0
                    total_likes = 0
                    total_comments = 0
                    
                    for post in profile.get_posts():
                        if post_count >= 5:
                            break
                        total_likes += post.likes
                        total_comments += post.comments
                        post_count += 1
                        
                    if post_count > 0 and profile.followers > 0:
                        avg_engagement = (total_likes + total_comments) / post_count
                        creator.engagement_rate = (avg_engagement / profile.followers) * 100
                    else:
                        creator.engagement_rate = 0.0
                        
                    creators.append(creator)
                except instaloader.exceptions.QueryReturnedBadRequestException:
                    self.logger.warning(f"'{profile.username}' için 429 Too Many Requests (Çok Fazla İstek) hatası, geçiliyor.")
                except instaloader.exceptions.LoginRequiredException:
                    self.logger.error("Instagram girişi gerekli, işlem durduruluyor.")
                    break
                except Exception as e:
                    self.logger.warning(f"Profil çekilirken hata: {str(e)}")
                    
            return self._apply_basic_filters(creators, filters)
            
        except instaloader.exceptions.ConnectionException as e:
            self.logger.error(f"Instaloader bağlantı hatası (429 olabilir): {str(e)}")
            self.logger.info("Playwright yedeğine geçiliyor...")
            return asyncio.run(self._playwright_fallback(keyword, filters))
        except Exception as e:
            self.logger.error(f"Instagram Instaloader aramasında hata: {str(e)}")
            return []
            
    async def _playwright_fallback(self, keyword: str, filters: Dict[str, Any]) -> List[Creator]:
        """Instagram için Playwright kullanan yedek yöntem."""
        from playwright.async_api import async_playwright
        from utils.stealth import apply_stealth_async
        from bs4 import BeautifulSoup
        
        creators = []
        try:
            self.logger.info(f"Playwright ile Instagram araması başlatılıyor: {keyword}")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                await apply_stealth_async(page)
                
                keyword = keyword.replace('#', '')
                search_url = f"https://www.instagram.com/explore/tags/{keyword}/"
                await page.goto(search_url, wait_until="networkidle")
                await page.wait_for_timeout(5000)
                
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                links = soup.select('a[href]')
                usernames = set()
                for link in links:
                    href = link.get('href', '')
                    if href.startswith('/p/') or href.startswith('/reel/'):
                        pass # Post linkleri, profile gitmek için ekstra işlem gerekir
                    elif len(href.split('/')) == 3 and href.startswith('/'):
                        username = href.strip('/')
                        if username not in ['explore', 'reels', 'direct']:
                            usernames.add(username)
                            
                for username in list(usernames)[:5]:
                    creator = Creator(
                        username=username,
                        platform='Instagram',
                        followers=0,
                        profile_url=f"https://www.instagram.com/{username}/",
                        bio="Playwright yedek araması ile bulundu"
                    )
                    creators.append(creator)
                    
                await browser.close()
                
            return self._apply_basic_filters(creators, filters)
        except Exception as e:
            self.logger.warning(f"Instagram Playwright yedeği başarısız oldu. Modül atlanıyor. Hata: {str(e)}")
            return []
