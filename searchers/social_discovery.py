"""
Arama motorları (DuckDuckGo + opsiyonel Google CSE) üzerinden
TikTok ve Instagram profili keşfeden canlı arama modülü.

Hiçbir platform API anahtarı veya login gerektirmez.
"""
import re
import logging
from typing import List, Optional, Dict, Any
from models.creator import Creator, ContentAnalysis

logger = logging.getLogger(__name__)


def parse_social_number(text: str) -> int:
    """
    Türkçe ve İngilizce takipçi/beğeni metinlerini tam sayıya çevirir:
    '15,2 B' -> 15200, '1.2M' -> 1200000, '125K' -> 125000,
    '450 Takipçi' -> 450, '15.2B Takipçi' -> 15200, '15.200' -> 15200
    """
    if not text:
        return 0
    cleaned = str(text).strip()
    
    match = re.search(r'([\d\.,]+)\s*([kKmMbB]|mn|Mn|MN)?', cleaned)
    if not match:
        return 0
    
    num_str, suffix = match.groups()
    
    # Eğer suffix varsa (K, M, B): '1.2' veya '15,2' ondalık sayıdır
    if suffix:
        # Hem '.' hem ',' ondalık ayırıcı olarak float'a çevrilmeli
        num_str = num_str.replace(',', '.')
        try:
            val = float(num_str)
        except ValueError:
            return 0
        
        multiplier = 1
        s = suffix.lower()
        if s in ['k', 'b']:      # K = thousand, B = Bin
            multiplier = 1_000
        elif s in ['m', 'mn']:   # M = million, Mn = Milyon
            multiplier = 1_000_000
        return int(val * multiplier)
    else:
        # Suffix yoksa: '15.200' veya '15,200' binlik ayırıcıdır
        num_str = num_str.replace('.', '').replace(',', '')
        try:
            return int(num_str)
        except ValueError:
            return 0


def extract_metrics_from_snippet(snippet: str) -> Dict[str, int]:
    """Arama motoru snippet'inden takipçi ve beğeni sayısı çıkarır."""
    result = {"followers": 0, "likes": 0}
    if not snippet:
        return result
    
    # Takipçi: "15.2B Takipçi" / "15.2K Followers"
    f_match = re.search(r'([\d\.,]+\s*[kKmMbB]?(?:mn)?)\s*(?:followers|takipçi|abonesi|abone)', snippet, re.IGNORECASE)
    if f_match:
        result["followers"] = parse_social_number(f_match.group(1))
    
    # Beğeni: "1.2M Beğeni" / "1.2M Likes"
    l_match = re.search(r'([\d\.,]+\s*[kKmMbB]?(?:mn)?)\s*(?:likes|beğeni)', snippet, re.IGNORECASE)
    if l_match:
        result["likes"] = parse_social_number(l_match.group(1))
    
    return result


# Sistem yolları: profil değil, genel sayfa olan path'ler
TIKTOK_SYSTEM_PATHS = {'tag', 'discover', 'video', 'music', 'about', 'legal', 'business', 'foryou', 'login', 'signup', 'live', 'search', 'effect'}
INSTAGRAM_SYSTEM_PATHS = {'p', 'reel', 'reels', 'explore', 'stories', 'channel', 'about', 'developer', 'legal', 'accounts', 'help', 'tags', 'direct', 'tv', 'nametag'}


class SocialDiscovery:
    """
    DuckDuckGo (ve opsiyonel Google CSE) kullanarak
    TikTok ve Instagram profillerini keşfeden arama motoru.
    """
    
    def __init__(self, google_cse_key: str = "", google_cse_cx: str = ""):
        self.google_cse_key = google_cse_key
        self.google_cse_cx = google_cse_cx
    
    def discover_tiktok(self, keyword: str, min_f: int = 0, max_f: Optional[int] = None, related_kws: List[str] = None) -> List[Dict[str, Any]]:
        """DuckDuckGo (+ opsiyonel Google CSE) ile TikTok profillerini keşfeder."""
        candidates = []
        seen_users = set()
        
        # Birden fazla sorgu ile genişlet
        queries = [
            f'site:tiktok.com/@* "{keyword}" türkiye',
            f'site:tiktok.com "{keyword}" takipçi',
        ]
        if related_kws:
            for rk in related_kws[:2]:
                queries.append(f'site:tiktok.com/@* "{rk}"')
        
        # DuckDuckGo ile arama
        for q in queries:
            results = self._ddg_search(q, max_results=15)
            for r in results:
                parsed = self._parse_tiktok_result(r, keyword)
                if parsed and parsed["username"] not in seen_users:
                    seen_users.add(parsed["username"])
                    candidates.append(parsed)
        
        # Google CSE ile arama (opsiyonel)
        if self.google_cse_key and self.google_cse_cx:
            for q in queries[:2]:  # İlk 2 sorgu yeter
                cse_results = self._google_cse_search(q, num=10)
                for r in cse_results:
                    parsed = self._parse_tiktok_result(r, keyword)
                    if parsed and parsed["username"] not in seen_users:
                        seen_users.add(parsed["username"])
                        candidates.append(parsed)
        
        # Takipçi filtresi uygula
        filtered = []
        for c in candidates:
            f = c.get("followers", 0)
            if min_f and f > 0 and f < min_f:
                continue
            if max_f and f > 0 and f > max_f:
                continue
            filtered.append(c)
        
        logger.info(f"SocialDiscovery TikTok: '{keyword}' için {len(filtered)} profil keşfedildi")
        return filtered
    
    def discover_instagram(self, keyword: str, min_f: int = 0, max_f: Optional[int] = None, related_kws: List[str] = None) -> List[Dict[str, Any]]:
        """DuckDuckGo (+ opsiyonel Google CSE) ile Instagram profillerini keşfeder."""
        candidates = []
        seen_users = set()
        
        queries = [
            f'site:instagram.com "{keyword}" "takipçi" türkiye -/p/ -/reel/',
            f'site:instagram.com "{keyword}" "followers" -/p/ -/reel/',
        ]
        if related_kws:
            for rk in related_kws[:2]:
                queries.append(f'site:instagram.com "{rk}" "takipçi" -/p/ -/reel/')
        
        for q in queries:
            results = self._ddg_search(q, max_results=15)
            for r in results:
                parsed = self._parse_instagram_result(r, keyword)
                if parsed and parsed["username"] not in seen_users:
                    seen_users.add(parsed["username"])
                    candidates.append(parsed)
        
        if self.google_cse_key and self.google_cse_cx:
            for q in queries[:2]:
                cse_results = self._google_cse_search(q, num=10)
                for r in cse_results:
                    parsed = self._parse_instagram_result(r, keyword)
                    if parsed and parsed["username"] not in seen_users:
                        seen_users.add(parsed["username"])
                        candidates.append(parsed)
        
        filtered = []
        for c in candidates:
            f = c.get("followers", 0)
            if min_f and f > 0 and f < min_f:
                continue
            if max_f and f > 0 and f > max_f:
                continue
            filtered.append(c)
        
        logger.info(f"SocialDiscovery Instagram: '{keyword}' için {len(filtered)} profil keşfedildi")
        return filtered
    
    def _ddg_search(self, query: str, max_results: int = 15) -> List[Dict[str, str]]:
        """DuckDuckGo ile arama yapar ve sonuçları döner."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region='tr-tr', max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", "")
                    })
            return results
        except Exception as e:
            logger.debug(f"DuckDuckGo arama hatası: {e}")
            return []
    
    def _google_cse_search(self, query: str, num: int = 10) -> List[Dict[str, str]]:
        """Google Custom Search Engine API ile arama yapar."""
        if not self.google_cse_key or not self.google_cse_cx:
            return []
        try:
            import requests
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_cse_key,
                "cx": self.google_cse_cx,
                "q": query,
                "num": min(num, 10),
                "lr": "lang_tr"
            }
            resp = requests.get(url, params=params, timeout=8)
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = []
            for item in data.get("items", []):
                # OpenGraph metatag'lerden ek bilgi çek
                og_desc = ""
                metatags = item.get("pagemap", {}).get("metatags", [{}])
                if metatags:
                    og_desc = metatags[0].get("og:description", "")
                
                results.append({
                    "title": item.get("title", ""),
                    "href": item.get("link", ""),
                    "body": og_desc or item.get("snippet", "")
                })
            return results
        except Exception as e:
            logger.debug(f"Google CSE arama hatası: {e}")
            return []
    
    def _parse_tiktok_result(self, result: Dict[str, str], keyword: str) -> Optional[Dict[str, Any]]:
        """Arama sonucundan TikTok profil bilgilerini ayrıştırır."""
        href = result.get("href", "")
        title = result.get("title", "")
        body = result.get("body", "")
        
        # URL'den kullanıcı adı çıkar: tiktok.com/@username
        match = re.search(r'tiktok\.com/@([a-zA-Z0-9_\.]{2,30})', href)
        if not match:
            return None
        
        username = match.group(1).rstrip('.').lower()
        if username in TIKTOK_SYSTEM_PATHS:
            return None
        
        # Snippet'ten takipçi sayısı çıkar
        combined_text = f"{title} {body}"
        metrics = extract_metrics_from_snippet(combined_text)
        
        # Başlıktan display name çıkar
        display_name = username
        name_match = re.match(r'^(.+?)\s*[\(\|@]', title)
        if name_match:
            display_name = name_match.group(1).strip()
        elif " on TikTok" in title:
            display_name = title.split(" on TikTok")[0].strip()
        elif " TikTok" in title:
            display_name = title.split(" TikTok")[0].strip().rstrip('|').rstrip('-').strip()
        
        return {
            "platform": "TikTok",
            "username": username,
            "display_name": display_name,
            "followers": metrics["followers"],
            "likes": metrics["likes"],
            "bio": body[:200] if body else "",
            "profile_url": f"https://www.tiktok.com/@{username}",
            "snippet": combined_text,
            "keyword": keyword
        }
    
    def _parse_instagram_result(self, result: Dict[str, str], keyword: str) -> Optional[Dict[str, Any]]:
        """Arama sonucundan Instagram profil bilgilerini ayrıştırır."""
        href = result.get("href", "")
        title = result.get("title", "")
        body = result.get("body", "")
        
        # URL'den kullanıcı adı çıkar: instagram.com/username/
        match = re.search(r'instagram\.com/([a-zA-Z0-9_\.]{2,30})', href)
        if not match:
            return None
        
        username = match.group(1).rstrip('.').lower()
        if username in INSTAGRAM_SYSTEM_PATHS:
            return None
        
        # Post veya reel linklerini atla
        if '/p/' in href or '/reel/' in href or '/reels/' in href or '/stories/' in href:
            return None
        
        combined_text = f"{title} {body}"
        metrics = extract_metrics_from_snippet(combined_text)
        
        display_name = username
        name_match = re.search(r'(?:^|\()@?([^)]+)\)', title)
        if not name_match:
            # "Name (@username)" formatı
            name_match2 = re.match(r'^(.+?)\s*[\(\|@•]', title)
            if name_match2:
                display_name = name_match2.group(1).strip()
        else:
            # Parantez öncesi isim
            pre_paren = title.split('(')[0].strip()
            if pre_paren:
                display_name = pre_paren
        
        return {
            "platform": "Instagram",
            "username": username,
            "display_name": display_name,
            "followers": metrics["followers"],
            "bio": body[:200] if body else "",
            "profile_url": f"https://www.instagram.com/{username}/",
            "snippet": combined_text,
            "keyword": keyword
        }
