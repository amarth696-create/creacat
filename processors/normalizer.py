from typing import Any, List
from models.creator import Creator
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Normalizer:
    """Platformdan gelen ham verileri standart Creator modeline dönüştürür."""
    
    def normalize(self, raw_data: Any, platform: str = "") -> Any:
        """
        Ham platform verisini veya veri listesini standartlaştırılmış Creator nesnesine dönüştürür.
        """
        if isinstance(raw_data, list):
            results = []
            for item in raw_data:
                if isinstance(item, Creator):
                    results.append(item)
                elif isinstance(item, dict):
                    p = platform or item.get('platform', 'unknown')
                    results.append(self.normalize(item, p))
            return results

        if isinstance(raw_data, Creator):
            return raw_data

        try:
            p = platform or (raw_data.get('platform') if isinstance(raw_data, dict) else 'unknown') or 'unknown'
            username = raw_data.get('username') or raw_data.get('handle') or ""
            followers = self._parse_followers(raw_data.get('followers') or raw_data.get('subscriberCount'))
            engagement = raw_data.get('engagement_rate') or raw_data.get('engagementRate')
            
            # Engagement rate eğer string veya None ise float'a çevir
            engagement_rate = 0.0
            if engagement is not None:
                try:
                    engagement_rate = float(engagement)
                except ValueError:
                    engagement_rate = 0.0
            
            display_name = raw_data.get('display_name') or raw_data.get('name') or username
            profile_url = self._normalize_url(raw_data.get('profile_url') or raw_data.get('url'), platform, username)

            # Temel Creator nesnesi oluştur
            creator = Creator(
                username=username,
                display_name=display_name,
                platform=platform,
                profile_url=profile_url,
                followers=followers,
                engagement_rate=engagement_rate,
                bio=raw_data.get('bio') or raw_data.get('description') or "",
                country=raw_data.get('country') or "",
                language=raw_data.get('language') or ""
            )
            
            logger.debug(f"{platform} için {username} adlı içerik üreticisi normalize edildi.")
            return creator
            
        except Exception as e:
            logger.error(f"{platform} platformu verisi normalize edilirken hata oluştu: {e}")
            return Creator(
                username="bilinmeyen",
                display_name="Bilinmeyen",
                platform=platform,
                profile_url=""
            )
            
    def _parse_followers(self, count_raw) -> int:
        """Takipçi sayısını (örneğin '245K') tam sayıya çevirir."""
        if count_raw is None:
            return 0
            
        if isinstance(count_raw, int):
            return count_raw
            
        count_str = str(count_raw).strip().upper()
        multiplier = 1
        
        if count_str.endswith('K'):
            multiplier = 1000
            count_str = count_str[:-1]
        elif count_str.endswith('M'):
            multiplier = 1000000
            count_str = count_str[:-1]
        elif count_str.endswith('B'):
            multiplier = 1000000000
            count_str = count_str[:-1]
            
        try:
            return int(float(count_str) * multiplier)
        except ValueError:
            return 0
            
    def _normalize_url(self, url: str | None, platform: str, username: str) -> str:
        """URL eksikse platform ve kullanıcı adından URL oluşturur."""
        if url:
            return url
            
        if not username:
            return ""
            
        platform = platform.lower()
        if platform == 'youtube':
            return f"https://youtube.com/@{username}"
        elif platform == 'instagram':
            return f"https://instagram.com/{username}"
        elif platform == 'tiktok':
            return f"https://tiktok.com/@{username}"
        elif platform == 'twitter':
            return f"https://twitter.com/{username}"
            
        return ""
