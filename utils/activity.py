import re
from datetime import datetime
from typing import Tuple, Optional

def evaluate_activity_status(time_text: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Son paylaşım tarihi/zaman metnini inceleyerek profilin aktif olup olmadığını belirler.
    Kural: 2 ay (60 gün) veya daha uzun süredir yeni içerik üretmeyen profiller İNAKTİF sayılır.
    
    Args:
        time_text: Örn. '3 gün önce', '2 hafta önce', '3 ay önce', '1 yıl önce', '2024-05-12'
        
    Returns:
        (is_active: bool, last_post_date: str, inactivity_warning: Optional[str])
    """
    if not time_text:
        return True, None, None
        
    s = str(time_text).strip().lower()
    
    # 1. Yıl / Sene / Year
    m_year = re.search(r'(\d+)\s*(?:yıl|sene|year)', s)
    if m_year or "yıl önce" in s or "sene önce" in s or "year ago" in s or "years ago" in s:
        count = int(m_year.group(1)) if m_year else 1
        return False, time_text, f"⚠️ Bu profil yaklaşık {count} yıldır yeni içerik üretmemiştir (İnaktif)."
        
    # 2. Ay / Month
    m_month = re.search(r'(\d+)\s*(?:ay|month)', s)
    if m_month:
        count = int(m_month.group(1))
        if count >= 2:
            return False, time_text, f"⚠️ Bu profil {count} aydır yeni içerik üretmemiştir (2+ ay inaktif)."
        else:
            return True, time_text, None
            
    # 3. Hafta / Week
    m_week = re.search(r'(\d+)\s*(?:hafta|week)', s)
    if m_week:
        count = int(m_week.group(1))
        if count >= 9:
            return False, time_text, f"⚠️ Bu profil {count} haftadır (~{count//4} ay) yeni içerik üretmemiştir."
        else:
            return True, time_text, None
            
    # 4. Gün / Day
    m_day = re.search(r'(\d+)\s*(?:gün|day)', s)
    if m_day:
        count = int(m_day.group(1))
        if count >= 60:
            return False, time_text, f"⚠️ Bu profil {count} gündür yeni içerik üretmemiştir."
        else:
            return True, time_text, None
            
    # 5. Saat / Dakika / Dün / Yeni
    if any(w in s for w in ["saat", "dakika", "dün", "bugün", "hour", "minute", "yesterday", "today", "yeni"]):
        return True, time_text, None
        
    # 6. Doğrudan YYYY-MM-DD formatı
    m_date = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', s)
    if m_date:
        try:
            dt = datetime(int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)))
            diff = (datetime.now() - dt).days
            if diff >= 60:
                months = diff // 30
                return False, time_text, f"⚠️ Son içerik {months} ay önce ({time_text}) yayınlanmıştır (İnaktif)."
            else:
                return True, time_text, None
        except Exception:
            pass
            
    return True, time_text, None
