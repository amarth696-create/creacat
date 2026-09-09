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
        
        link = f"[{username}]({url})" if url != "#" else f"**@{username}**"
        lines.append(f"{i}. 👤 **{link}** — *{plat_str}*")
        lines.append(f"   • 👥 **Takipçi:** {followers:,} | 📈 **Etkileşim:** %{eng:.2f} | ⭐ **Uygunluk Skoru:** {score:.1f}/100 | 🟢 **Herkese Açık**")
        
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
