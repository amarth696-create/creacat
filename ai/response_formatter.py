from typing import List, Any

def format_search_results(creators: List[Any], keyword: str, hashtags: List[str] = None, related_keywords: List[str] = None) -> str:
    """Arama sonuçlarını özetleyen zengin, içerik odaklı ve spesifik bir Türkçe liste metni oluşturur."""
    if not creators:
        return f"🔍 **'{keyword}'** konusu için kriterlere uygun içerik üreticisi bulunamadı. Lütfen filtreleri genişleterek tekrar deneyin."
    
    info_blocks = []
    if related_keywords:
        info_blocks.append(f"💡 **Otomatik Türetilen İlgili Arama Kelimeleri:** {', '.join([f'`{k}`' for k in related_keywords[:6]])}")
    if hashtags:
        info_blocks.append(f"🏷️ **Taranan Hashtag & Nişler:** {' '.join([f'`{t}`' for t in hashtags[:8]])}")
        
    header_extra = "\n\n".join(info_blocks) + "\n\n" if info_blocks else ""
        
    lines = [
        f"### 🎯 '{keyword.capitalize()}' Konusunda İçerikleri Doğrulanan En Uygun Üreticiler ({len(creators)} Kişi):",
        header_extra
    ]
    
    for i, c in enumerate(creators, 1):
        username = getattr(c, "username", "bilinmeyen")
        plat = getattr(c, "platform", "")
        if hasattr(plat, "value"):
            plat = plat.value
        plat_str = str(plat).capitalize()
        followers = getattr(c, "followers", 0) or 0
        eng = getattr(c, "engagement_rate", 0.0) or 0.0
        score = getattr(c, "final_score", 0.0) or getattr(c, "score", 0.0) or 0.0
        url = getattr(c, "profile_url", "") or "#"
        bio = getattr(c, "bio", "") or ""
        
        ca = getattr(c, "content_analysis", None)
        llm_ozet = getattr(ca, "llm_ozet", "") if ca else ""
        nis = getattr(ca, "nis_alani", "") if ca else ""
        
        # Son incelenen somut içerikler / videolar
        recent = getattr(c, "recent_contents", []) or (getattr(ca, "ana_konular", []) if ca else [])
        
        plat_lower = plat_str.lower()
        badge = "🔴 YouTube" if "youtube" in plat_lower else ("🟣 Instagram" if "instagram" in plat_lower else ("⚫ TikTok" if "tiktok" in plat_lower else plat_str))
        
        # Aktivite & güncellik bilgisi
        is_active = getattr(c, "is_active", True)
        last_post = getattr(c, "last_post_date", None)
        inactivity_warn = getattr(c, "inactivity_warning", None)
        
        act_badge = "🟢 **Aktif Üretici**" if is_active else "⚠️ **İNAKTİF (2+ aydır içerik yok)**"
        
        link = f"[{username}]({url})" if url != "#" else f"**@{username}**"
        lines.append(f"{i}. 👤 **{link}** — **{badge}** — {act_badge}")
        
        v_views = getattr(c, "avg_video_views", 0) or 0
        s_views = getattr(c, "avg_shorts_views", 0) or 0
        v_str = f"📺 **Yatay İzlenme:** {v_views:,}" if v_views > 0 else ""
        s_str = f"📱 **Shorts:** {s_views:,}" if s_views > 0 else ""
        views_part = f" | {v_str} | {s_str}" if (v_str or s_str) else ""
        
        lines.append(f"   • 👥 **Takipçi:** {followers:,} | 📈 **Etkileşim:** %{eng:.2f} | ⭐ **Uygunluk Skoru:** {score:.1f}/100{views_part}")
        
        has_sp = getattr(c, "has_sponsored_content", False)
        sp_cnt = getattr(c, "sponsored_video_count", 0)
        sp_kws = getattr(c, "sponsor_keywords_found", [])
        if has_sp:
            kw_text = f" ({', '.join(sp_kws[:3])})" if sp_kws else ""
            lines.append(f"   • 🤝 **İşbirliği Geçmişi:** Ticari İşbirliği / Reklam Yapmış ({sp_cnt} video tespit edildi){kw_text}")
        else:
            lines.append("   • 🌿 **İşbirliği Durumu:** Organik İçerik Üreticisi (Ticari reklam tespit edilmedi)")
        
        if not is_active:
            warning_msg = inactivity_warn or f"Bu profil 2 aydan uzun süredir yeni içerik üretmemiştir ({last_post or 'uzun süredir inaktif'})."
            lines.append(f"   • ⚠️ **İNAKTİFLİK UYARISI:** {warning_msg}")
        elif last_post:
            lines.append(f"   • 🕒 **Son İçerik:** {last_post}")

        if bio:
            short_bio = bio[:180] + ("..." if len(bio) > 180 else "")
            lines.append(f"   • 📝 **Biyografi:** {short_bio}")
            
        if recent:
            lines.append("   • 🎬 **İncelenen Son İçerik / Video Konuları:**")
            for item in recent[:3]:
                lines.append(f"     ▫️ *{item}*")
            
        if llm_ozet:
            lines.append(f"   • 🔍 **İçerik İnceleme & Tarzı:** {llm_ozet}")
        elif nis:
            lines.append(f"   • 🎯 **Odak Alanı:** {nis}")
            
        lines.append(f"   • 🔗 **Doğrudan Kanal/Hesap:** {url}")
        lines.append("")
        
    return "\n".join(lines)


def format_creator_detail(creator: Any) -> str:
    """İçerik üreticinin detaylarını Türkçe özetler."""
    plat = getattr(creator, "platform", "")
    if hasattr(plat, "value"):
        plat = plat.value
    return f"{creator.username} adlı yayıncı {str(plat).capitalize()} platformunda içerik üretiyor."

def format_comparison(creators: List[Any]) -> str:
    """Üreticilerin karşılaştırmasını döner."""
    names = ", ".join(c.username for c in creators)
    return f"Seçilen yayıncılar karşılaştırılıyor: {names}"

def format_error(error_type: str, details: str) -> str:
    """Hata mesajlarını formatlar."""
    return f"Hata ({error_type}): {details}. Lütfen tekrar deneyin."
