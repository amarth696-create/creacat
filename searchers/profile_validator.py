"""
Keşfedilen TikTok ve Instagram profillerinin gerçekliğini,
erişilebilirliğini ve herkese açıklık durumunu doğrulayan modül.

TikTok: __UNIVERSAL_DATA_FOR_REHYDRATION__ SSR JSON + OpenGraph fallback
Instagram: Snippet-based + OpenGraph + Picuki mirror fallback
"""
import re
import json
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


class TikTokValidator:
    """
    TikTok profil doğrulayıcı.
    Profil sayfasından __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON'u çekerek
    gerçek takipçi sayısı, bio, gizlilik durumu ve video sayısını doğrular.
    """
    
    @classmethod
    def validate(cls, username: str) -> Optional[Dict[str, Any]]:
        """
        TikTok profilini doğrular ve gerçek metrikleri döner.
        Profil yoksa, gizliyse veya erişilemiyorsa None döner.
        """
        clean_user = username.lstrip('@').strip().lower()
        url = f"https://www.tiktok.com/@{clean_user}"
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=6, allow_redirects=True)
            
            if resp.status_code == 404:
                logger.debug(f"TikTok profil bulunamadı: @{clean_user}")
                return None
            if resp.status_code != 200:
                logger.debug(f"TikTok HTTP {resp.status_code}: @{clean_user}")
                return None
            
            html = resp.text
            
            # Yöntem 1: SSR Rehydration JSON (en güvenilir)
            json_match = re.search(
                r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"\s+type="application/json">(.*?)</script>',
                html,
                re.DOTALL
            )
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    user_scope = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                    user_info = user_scope.get("userInfo", {})
                    user = user_info.get("user", {})
                    stats = user_info.get("stats", {})
                    
                    if user and stats:
                        is_private = user.get("privateAccount", False)
                        if is_private:
                            logger.debug(f"TikTok @{clean_user} gizli hesap, atlanıyor")
                            return None
                        
                        return {
                            "platform": "TikTok",
                            "username": user.get("uniqueId", clean_user),
                            "display_name": user.get("nickname", clean_user),
                            "followers": int(stats.get("followerCount", 0)),
                            "following": int(stats.get("followingCount", 0)),
                            "likes": int(stats.get("heartCount", 0)),
                            "video_count": int(stats.get("videoCount", 0)),
                            "bio": user.get("signature", ""),
                            "is_private": False,
                            "is_verified": user.get("verified", False),
                            "profile_url": url,
                            "source": "tiktok_ssr"
                        }
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"TikTok SSR JSON ayrıştırma hatası @{clean_user}: {e}")
            
            # Yöntem 2: OpenGraph meta tag fallback
            og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html)
            og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
            
            if og_desc:
                from searchers.social_discovery import extract_metrics_from_snippet
                desc_text = og_desc.group(1)
                metrics = extract_metrics_from_snippet(desc_text)
                
                display_name = clean_user
                if og_title:
                    raw_title = og_title.group(1)
                    # "DisplayName (@username) | TikTok" formatı
                    name_part = raw_title.split("(@")[0].strip() if "(@" in raw_title else raw_title.split(" on TikTok")[0].strip()
                    if name_part:
                        display_name = name_part
                
                # Gizli hesap kontrolü
                if "hesab" in html.lower() and "gizli" in html.lower():
                    return None
                if "private account" in html.lower():
                    return None
                
                if metrics["followers"] > 0:
                    return {
                        "platform": "TikTok",
                        "username": clean_user,
                        "display_name": display_name,
                        "followers": metrics["followers"],
                        "likes": metrics["likes"],
                        "bio": desc_text[:200],
                        "is_private": False,
                        "is_verified": False,
                        "profile_url": url,
                        "source": "tiktok_og"
                    }
            
            # Profil var ama metrik çıkaramadık — yine de URL erişilebilir
            if resp.status_code == 200 and f"@{clean_user}" in html.lower():
                return {
                    "platform": "TikTok",
                    "username": clean_user,
                    "display_name": clean_user,
                    "followers": 0,
                    "bio": "",
                    "is_private": False,
                    "profile_url": url,
                    "source": "tiktok_basic"
                }
                
        except requests.RequestException as e:
            logger.debug(f"TikTok doğrulama isteği başarısız @{clean_user}: {e}")
        
        return None


class InstagramValidator:
    """
    Instagram profil doğrulayıcı.
    Arama motoru snippet'i, doğrudan OpenGraph ve Picuki mirror
    ile profili doğrular.
    """
    
    SYSTEM_PATHS = {
        'p', 'reel', 'reels', 'explore', 'stories', 'channel',
        'about', 'developer', 'legal', 'accounts', 'help', 'tags', 'direct', 'tv'
    }
    
    @classmethod
    def is_valid_username(cls, username: str) -> bool:
        clean = username.strip().lower()
        return bool(re.match(r'^[a-zA-Z0-9_\.]{3,30}$', clean)) and clean not in cls.SYSTEM_PATHS
    
    @classmethod
    def validate(cls, username: str, known_snippet: str = "") -> Optional[Dict[str, Any]]:
        """
        Instagram profilini doğrular.
        known_snippet: Arama motorundan gelen snippet (takipçi içerebilir)
        """
        clean_user = username.lstrip('@').strip().lower()
        if not cls.is_valid_username(clean_user):
            return None
        
        from searchers.social_discovery import extract_metrics_from_snippet
        
        # Adım 1: Snippet zaten takipçi bilgisi içeriyorsa doğrudan kullan
        if known_snippet:
            metrics = extract_metrics_from_snippet(known_snippet)
            if metrics["followers"] > 0:
                display_name = clean_user
                # Snippet'ten display name çıkarmayı dene
                name_match = re.match(r'^(.+?)\s*[\(\|@•]', known_snippet)
                if name_match:
                    display_name = name_match.group(1).strip()
                
                return {
                    "platform": "Instagram",
                    "username": clean_user,
                    "display_name": display_name,
                    "followers": metrics["followers"],
                    "bio": known_snippet[:200],
                    "is_private": False,
                    "profile_url": f"https://www.instagram.com/{clean_user}/",
                    "source": "ig_snippet"
                }
        
        # Adım 2: Doğrudan Instagram sayfasına GET (lokal / residential IP'lerde çalışır)
        try:
            resp = requests.get(
                f"https://www.instagram.com/{clean_user}/",
                headers=HEADERS,
                timeout=5,
                allow_redirects=False
            )
            if resp.status_code == 200:
                html = resp.text
                og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html)
                if og_desc:
                    desc_text = og_desc.group(1)
                    metrics = extract_metrics_from_snippet(desc_text)
                    
                    og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
                    display_name = clean_user
                    if og_title:
                        raw_title = og_title.group(1)
                        name_part = raw_title.split("(@")[0].strip() if "(@" in raw_title else raw_title.split("•")[0].strip()
                        if name_part:
                            display_name = name_part
                    
                    if metrics["followers"] > 0:
                        return {
                            "platform": "Instagram",
                            "username": clean_user,
                            "display_name": display_name,
                            "followers": metrics["followers"],
                            "bio": desc_text[:200],
                            "is_private": False,
                            "profile_url": f"https://www.instagram.com/{clean_user}/",
                            "source": "ig_og"
                        }
            elif resp.status_code == 404:
                return None  # Profil yok
        except requests.RequestException:
            pass
        
        # Adım 3: Picuki mirror fallback (cloud datacenter IP'lerde çalışır)
        try:
            from bs4 import BeautifulSoup
            picuki_url = f"https://www.picuki.com/profile/{clean_user}"
            resp = requests.get(picuki_url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                followers_el = soup.select_one('.followed_by span') or soup.select_one('.total_followers')
                name_el = soup.select_one('.profile-name-top') or soup.select_one('.profile-name')
                desc_el = soup.select_one('.profile-description')
                
                followers = 0
                if followers_el:
                    from searchers.social_discovery import parse_social_number
                    followers = parse_social_number(followers_el.get_text(strip=True))
                
                display_name = name_el.get_text(strip=True) if name_el else clean_user
                bio = desc_el.get_text(strip=True) if desc_el else ""
                
                if followers > 0:
                    return {
                        "platform": "Instagram",
                        "username": clean_user,
                        "display_name": display_name,
                        "followers": followers,
                        "bio": bio[:200],
                        "is_private": False,
                        "profile_url": f"https://www.instagram.com/{clean_user}/",
                        "source": "ig_picuki"
                    }
        except Exception as e:
            logger.debug(f"Instagram Picuki fallback hatası @{clean_user}: {e}")
        
        # Hiçbir yöntem çalışmadıysa, en azından snippet varsa kabul et
        if known_snippet:
            return {
                "platform": "Instagram",
                "username": clean_user,
                "display_name": clean_user,
                "followers": 0,
                "bio": known_snippet[:200],
                "is_private": False,
                "profile_url": f"https://www.instagram.com/{clean_user}/",
                "source": "ig_unverified"
            }
        
        return None
