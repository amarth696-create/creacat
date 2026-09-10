import re
from datetime import datetime
from typing import Tuple, Optional

def evaluate_activity_status(time_text: Optional[str]) -> Tuple[bool, Optional[str], Optional[str], bool]:
    """
    Son paylaşım tarihi/zaman metnini inceleyerek profilin aktivite ve hariç tutulma durumunu belirler.
    
    Kurallar:
    - 2 ay (60 gün) veya daha uzun süredir yeni içerik üretmeyen profiller İNAKTİF sayılır (uyarı rozeti verilir).
    - 3 aydan uzun süredir (> 3 ay / >= 90 gün) içerik üretmeyen profiller LİSTEYE DAHİL EDİLMEZ (is_excluded=True).
    - 2 - 3 ay arasındaki profiller ise listede tutulur ancak "⚠️ İNAKTİF (2+ aydır içerik yok)" uyarısı alır.
    
    Args:
        time_text: Örn. '3 gün önce', '2 hafta önce', '2 ay önce', '3 ay önce', '1 yıl önce', '2024-05-12'
        
    Returns:
        (is_active: bool, last_post_date: str, inactivity_warning: Optional[str], is_excluded: bool)
    """
    if not time_text:
        return True, None, None, False
        
    s = str(time_text).strip().lower()
    
    # 1. Yıl / Sene / Year (3 aydan çok daha eski -> kesinlikle elenmeli)
    m_year = re.search(r'(\d+)\s*(?:yıl|sene|year)', s)
    if m_year or "yıl önce" in s or "sene önce" in s or "year ago" in s or "years ago" in s:
        count = int(m_year.group(1)) if m_year else 1
        return False, time_text, f"⚠️ Bu profil yaklaşık {count} yıldır yeni içerik üretmemiştir (İnaktif).", True
        
    # 2. Ay / Month
    m_month = re.search(r'(\d+)\s*(?:ay|month)', s)
    if m_month:
        count = int(m_month.group(1))
        if count > 2:  # 3 ay veya daha fazla -> listeden elenir!
            return False, time_text, f"⚠️ Bu profil {count} aydır yeni içerik üretmemiştir (3+ ay inaktif).", True
        elif count == 2:  # 2 ay -> listede kalır, inaktiflik belirteci gösterilir
            return False, time_text, f"⚠️ Bu profil 2 aydır yeni içerik üretmemiştir (2+ ay inaktif).", False
        else:
            return True, time_text, None, False
            
    # 3. Hafta / Week
    m_week = re.search(r'(\d+)\s*(?:hafta|week)', s)
    if m_week:
        count = int(m_week.group(1))
        if count >= 13:  # ~3 aydan fazla
            return False, time_text, f"⚠️ Bu profil {count} haftadır (~{count//4} ay) yeni içerik üretmemiştir.", True
        elif count >= 9:  # 2 - 3 ay arası
            return False, time_text, f"⚠️ Bu profil {count} haftadır (~{count//4} ay) yeni içerik üretmemiştir.", False
        else:
            return True, time_text, None, False
            
    # 4. Gün / Day
    m_day = re.search(r'(\d+)\s*(?:gün|day)', s)
    if m_day:
        count = int(m_day.group(1))
        if count >= 90:  # 3 aydan fazla
            return False, time_text, f"⚠️ Bu profil {count} gündür yeni içerik üretmemiştir.", True
        elif count >= 60:  # 2 - 3 ay arası
            return False, time_text, f"⚠️ Bu profil {count} gündür yeni içerik üretmemiştir.", False
        else:
            return True, time_text, None, False
            
    # 5. Saat / Dakika / Dün / Yeni
    if any(w in s for w in ["saat", "dakika", "dün", "bugün", "hour", "minute", "yesterday", "today", "yeni"]):
        return True, time_text, None, False
        
    # 6. Doğrudan YYYY-MM-DD formatı
    m_date = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', s)
    if m_date:
        try:
            dt = datetime(int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)))
            diff = (datetime.now() - dt).days
            months = diff // 30
            if diff >= 90:  # 3 aydan fazla
                return False, time_text, f"⚠️ Son içerik {months} ay önce ({time_text}) yayınlanmıştır (İnaktif).", True
            elif diff >= 60:  # 2 - 3 ay arası
                return False, time_text, f"⚠️ Son içerik {months} ay önce ({time_text}) yayınlanmıştır (İnaktif).", False
            else:
                return True, time_text, None, False
        except Exception:
            pass
            
    return True, time_text, None, False
