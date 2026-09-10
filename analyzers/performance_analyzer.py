"""
İçerik üreticilerinin video performanslarını (yatay video ortalaması ve shorts ortalaması)
ve ticari işbirliği / sponsorluk (paid promotion, reklam, sponsor) geçmişini analiz eden modül.
"""
import re
import json
import logging
import requests
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

# Sponsorluk ve reklam tespiti için anahtar kelime ve regex kuralları
SPONSOR_PATTERNS = [
    r'#işbirliği\b',
    r'#isbirligi\b',
    r'#reklam\b',
    r'#sponsorlu\b',
    r'#sponsor\b',
    r'#ad\b',
    r'#paidpromotion\b',
    r'\bişbirliği\b',
    r'\biş birliği\b',
    r'\breklam\b',
    r'\bsponsorlu\b',
    r'\bortaklığıyla\b',
    r'\bmarka işbirliği\b',
    r'\bindirim kodu\b',
    r'\bkupon kodu\b',
    r'\bhediye gönderi\b',
    r'\bpaid partnership\b',
    r'\bpaid promotion\b',
    r'\bsponsored by\b',
]

SPONSOR_REGEX = re.compile('|'.join(SPONSOR_PATTERNS), re.IGNORECASE)


def parse_view_text(text: str) -> int:
    """
    İzlenme metinlerini tam sayıya çevirir:
    '2,6 B' -> 2600
    '71 B görüntüleme' -> 71000
    '1,2 Mn' -> 1200000
    '850 görüntüleme' -> 850
    '45K views' -> 45000
    """
    if not text:
        return 0
    cleaned = str(text).replace("görüntüleme", "").replace("views", "").replace("izlenme", "").strip()
    match = re.search(r'([\d\.,]+)\s*([kKmMbB]|mn|Mn)?', cleaned)
    if not match:
        return 0
    num_str, suffix = match.groups()
    if suffix:
        num_str = num_str.replace(',', '.')
        try:
            val = float(num_str)
        except ValueError:
            return 0
        multiplier = 1
        s = suffix.lower()
        if s in ['k', 'b']:
            multiplier = 1_000
        elif s in ['m', 'mn']:
            multiplier = 1_000_000
        return int(val * multiplier)
    else:
        num_str = num_str.replace('.', '').replace(',', '')
        try:
            return int(num_str)
        except ValueError:
            return 0


def detect_sponsorship_in_texts(texts: List[str]) -> Tuple[bool, int, List[str]]:
    """
    Verilen metin listesinde (video başlıkları, açıklamalar, bio) sponsorluk ve işbirliği sinyallerini tarar.
    Döner: (has_sponsored_content, sponsored_count, keywords_found)
    """
    found_keywords = set()
    sponsored_count = 0

    for t in texts:
        if not t:
            continue
        matches = SPONSOR_REGEX.findall(t)
        if matches:
            sponsored_count += 1
            for m in matches:
                found_keywords.add(m.strip().lower())

    has_sponsored = (sponsored_count > 0)
    return has_sponsored, sponsored_count, sorted(list(found_keywords))


class PerformanceAnalyzer:
    """YouTube ve diğer platformlar için ortalama izlenme ve sponsorluk analizcisi."""

    @classmethod
    def analyze_youtube_channel(cls, channel_endpoint: str) -> Dict[str, Any]:
        """
        YouTube kanal sayfasından:
        1. Son 10 yatay videoyu ve izlenmelerini çeker -> avg_video_views
        2. Son 10 Shorts videosunu ve izlenmelerini çeker -> avg_shorts_views
        3. Başlıklar üzerinden sponsorluk / reklam tespiti yapar
        """
        result = {
            "avg_video_views": 0,
            "avg_shorts_views": 0,
            "has_sponsored_content": False,
            "sponsored_video_count": 0,
            "sponsor_keywords_found": [],
            "recent_video_titles": []
        }

        if not channel_endpoint:
            return result

        clean_ep = channel_endpoint.rstrip('/')
        all_titles = []

        # 1. YATAY VİDEOLAR SEKMENTİ (/videos)
        try:
            url_v = f"https://www.youtube.com{clean_ep}/videos"
            r_v = requests.get(url_v, headers=HEADERS, timeout=5)
            if r_v.status_code == 200:
                match_v = re.search(r'var ytInitialData = ({.*?});</script>', r_v.text)
                if match_v:
                    data_v = json.loads(match_v.group(1))
                    tabs_v = data_v.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
                    for tab in tabs_v:
                        tab_r = tab.get('tabRenderer', {})
                        if 'content' in tab_r:
                            items = tab_r['content'].get('richGridRenderer', {}).get('contents', [])
                            video_views = []
                            for it in items[:10]:
                                lvm = it.get('richItemRenderer', {}).get('content', {}).get('lockupViewModel', {})
                                if lvm:
                                    meta = lvm.get('metadata', {}).get('lockupMetadataViewModel', {})
                                    title = meta.get('title', {}).get('content')
                                    if title:
                                        all_titles.append(title)
                                        result["recent_video_titles"].append(title)
                                    rows = meta.get('metadata', {}).get('contentMetadataViewModel', {}).get('metadataRows', [])
                                    for row in rows:
                                        for part in row.get('metadataParts', []):
                                            t_val = part.get('text', {}).get('content', '')
                                            if any(unit in t_val for unit in ['B', 'Mn', 'M', 'K', 'görüntüleme', 'izlenme']):
                                                views = parse_view_text(t_val)
                                                if views > 0:
                                                    video_views.append(views)
                                                    break
                            if video_views:
                                result["avg_video_views"] = int(sum(video_views) / len(video_views))
                            break
        except Exception as e:
            logger.debug(f"Yatay video analiz hatası ({channel_endpoint}): {e}")

        # 2. SHORTS SEKMENTİ (/shorts)
        try:
            url_s = f"https://www.youtube.com{clean_ep}/shorts"
            r_s = requests.get(url_s, headers=HEADERS, timeout=5)
            if r_s.status_code == 200:
                match_s = re.search(r'var ytInitialData = ({.*?});</script>', r_s.text)
                if match_s:
                    data_s = json.loads(match_s.group(1))
                    tabs_s = data_s.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
                    for tab in tabs_s:
                        tab_r = tab.get('tabRenderer', {})
                        if 'content' in tab_r:
                            items = tab_r['content'].get('richGridRenderer', {}).get('contents', [])
                            shorts_views = []
                            for it in items[:10]:
                                content_obj = it.get('richItemRenderer', {}).get('content', {})
                                slvm = content_obj.get('shortsLockupViewModel')
                                if slvm:
                                    title = slvm.get('overlayMetadata', {}).get('primaryText', {}).get('content')
                                    if title:
                                        all_titles.append(title)
                                    view_text = slvm.get('overlayMetadata', {}).get('secondaryText', {}).get('content')
                                    if view_text:
                                        s_views = parse_view_text(view_text)
                                        if s_views > 0:
                                            shorts_views.append(s_views)
                            if shorts_views:
                                result["avg_shorts_views"] = int(sum(shorts_views) / len(shorts_views))
                            break
        except Exception as e:
            logger.debug(f"Shorts analiz hatası ({channel_endpoint}): {e}")

        # 3. SPONSORLUK VE İŞBİRLİĞİ TESPİTİ
        if all_titles:
            has_sp, count_sp, kws = detect_sponsorship_in_texts(all_titles)
            result["has_sponsored_content"] = has_sp
            result["sponsored_video_count"] = count_sp
            result["sponsor_keywords_found"] = kws

        return result
