"""
İçerik üreticilerinin video performanslarını (yatay video ortalaması ve shorts ortalaması)
ve ticari işbirliği / sponsorluk (paid promotion, reklam, sponsor, marka ortaklığı) geçmişini analiz eden modül.
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

# 1. Sponsorluk ve reklam tespiti için anahtar kelime ve kalıp kuralları
SPONSOR_PATTERNS = [
    r'#işbirliği\b',
    r'#isbirligi\b',
    r'#reklam\b',
    r'#sponsorlu\b',
    r'#sponsor\b',
    r'#ad\b',
    r'#paidpromotion\b',
    r'#işortaklığı\b',
    r'\bişbirliği\b',
    r'\biş birliği\b',
    r'\breklam\b',
    r'\bsponsorlu\b',
    r'\bsponsorluk\b',
    r'\bortaklığıyla\b',
    r'\bmarka işbirliği\b',
    r'\bindirim kodu\b',
    r'\bkupon kodu\b',
    r'\bindirim kuponu\b',
    r'\bhediye gönderi\b',
    r'\bhediye ürün\b',
    r'\bpaid partnership\b',
    r'\bpaid promotion\b',
    r'\bsponsored by\b',
    r'\btanıtım\b',
    r'\bkatkılarıyla\b',
    r'\bdestekleriyle\b',
    r'\biş ortaklığı\b',
]

# 2. Türkiye'de en yaygın influencer işbirliği yapan popüler markalar
POPULAR_BRANDS = [
    'trendyol', 'hepsiburada', 'yemeksepeti', 'getir', 'mavi', 'defacto', 'lc waikiki',
    'gratis', 'watsons', 'sephora', 'flormar', 'loreal', 'yves rocher',
    'dyson', 'philips', 'samsung', 'apple', 'huawei', 'xiaomi', 'arçelik', 'monster',
    'papara', 'garanti', 'storytel', 'audible', 'nordvpn', 'surfshark', 'cambly', 'open english',
    'red bull', 'starbucks', 'eti', 'ülker', 'karaca', 'ikea', 'english home', 'decathlon'
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
    '1.5M' -> 1500000
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
    Verilen metin listesinde (video başlıkları, açıklamalar, bio) sponsorluk, reklam
    ve bilinen marka ortaklığı sinyallerini tarar.
    Döner: (has_sponsored_content, sponsored_count, keywords_found)
    """
    found_keywords = set()
    sponsored_count = 0

    for t in texts:
        if not t:
            continue
        text_lower = t.lower()
        
        # 1. Regex kural kontrolü (#reklam, işbirliği, indirim kodu vb.)
        matches = SPONSOR_REGEX.findall(t)
        matched_this_text = False
        if matches:
            matched_this_text = True
            for m in matches:
                clean_m = m.strip().lower()
                found_keywords.add(clean_m)

        # 2. Popüler sponsor markaları ve link kalıpları kontrolü (örn: "trendyol.com", "link bio'da", "nordvpn.com")
        for b in POPULAR_BRANDS:
            if b in text_lower and any(indicator in text_lower for indicator in ['link', 'kod', 'fırsat', 'indirim', 'özel', 'https:', 'http:']):
                matched_this_text = True
                found_keywords.add(b.capitalize())

        if matched_this_text:
            sponsored_count += 1

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
        3. Videoların detay açıklamalarından gerçek sponsorluk / reklam tespiti yapar
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
        all_text_blobs = []
        video_ids_to_inspect = []

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
                                    cid = lvm.get('contentId')
                                    if cid and len(video_ids_to_inspect) < 3:
                                        video_ids_to_inspect.append(cid)
                                        
                                    meta = lvm.get('metadata', {}).get('lockupMetadataViewModel', {})
                                    title = meta.get('title', {}).get('content')
                                    if title:
                                        all_text_blobs.append(title)
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
                                        all_text_blobs.append(title)
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

        # 3. VİDEO AÇIKLAMALARINDAN DERİN SPONSORLUK VE REKLAM TESPİTİ
        # YouTuber'lar sponsorlukları genellikle başlığa değil açıklama kısmına yazar
        for vid in video_ids_to_inspect:
            try:
                v_url = f"https://www.youtube.com/watch?v={vid}"
                r_v = requests.get(v_url, headers=HEADERS, timeout=3)
                if r_v.status_code == 200:
                    desc_matches = re.findall(r'"shortDescription":"(.*?)"', r_v.text)
                    if desc_matches:
                        raw_desc = desc_matches[0]
                        try:
                            clean_desc = raw_desc.encode('utf-8').decode('unicode_escape')
                        except Exception:
                            clean_desc = raw_desc
                        all_text_blobs.append(clean_desc)
            except Exception:
                pass

        # 4. SPONSORLUK ANALİZİNİ ÇALIŞTIR
        if all_text_blobs:
            has_sp, count_sp, kws = detect_sponsorship_in_texts(all_text_blobs)
            result["has_sponsored_content"] = has_sp
            result["sponsored_video_count"] = count_sp
            result["sponsor_keywords_found"] = kws

        return result
