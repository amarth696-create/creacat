import io
import json
import pandas as pd
import streamlit as st
from typing import List, Any

def get_platform_name(creator: Any) -> str:
    """Creator platformunu okunabilir string olarak döner."""
    plat = getattr(creator, "platform", "Bilinmeyen")
    if hasattr(plat, "value"):
        plat = plat.value
    return str(plat).capitalize()

def render_creator_card(creator: Any) -> None:
    """Tek bir içerik üreticinin detaylarını gösterir."""
    username = getattr(creator, "username", "bilinmeyen")
    platform = get_platform_name(creator)
    followers = getattr(creator, "followers", 0) or 0
    
    score = getattr(creator, "final_score", 0.0) or getattr(creator, "score", 0.0) or 0.0
    eng_rate = getattr(creator, "engagement_rate", 0.0) or 0.0
    
    with st.expander(f"👤 {username} - {platform} ({followers:,} Takipçi) | Skor: {score:.1f}/100"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Takipçi", f"{followers:,}")
        with col2:
            st.metric("Etkileşim Oranı", f"%{eng_rate:.2f}")
        with col3:
            st.metric("Uygunluk Skoru", f"{score:.1f}/100")
            
        st.caption("🟢 **Hesap Durumu:** Herkese Açık (Public) • Doğrulanmış Profil")
        bio = getattr(creator, "bio", "") or "Bilgi yok"
        st.write("📝 **Hakkında (Bio):**", bio[:250] + ("..." if len(bio) > 250 else ""))
        
        ca = getattr(creator, "content_analysis", None)
        recent = getattr(creator, "recent_contents", []) or (getattr(ca, "ana_konular", []) if ca else [])
        if recent:
            st.write("🎬 **İncelenen Son İçerikler / Videolar:**")
            for item in recent[:3]:
                st.markdown(f"- ▫️ *{item}*")
                
        if ca:
            if getattr(ca, "llm_ozet", None):
                st.write("🔍 **İçerik İnceleme & Tarzı:**", ca.llm_ozet)
            if getattr(ca, "nis_alani", None):
                st.write("🎯 **Niş Alanı:**", ca.nis_alani)
            if getattr(ca, "hedef_kitle", None):
                st.write("👥 **Hedef Kitle:**", ca.hedef_kitle)
            
            tags = getattr(ca, "konu_etiketleri", []) or []
            if tags:
                st.write("🏷️ **Konu Etiketleri:**", ", ".join([f"`{t}`" for t in tags]))
        
        url = getattr(creator, "profile_url", None) or getattr(creator, "url", "#")
        if url and url != "#":
            st.link_button(f"🌐 @{username} Profiline Git", url)


def render_results_table(creators: List[Any], depth: int = 1) -> None:
    """Arama sonuçlarını interaktif bir tablo olarak gösterir."""
    if not creators:
        st.warning("Gösterilecek sonuç bulunamadı.")
        return
        
    data = []
    for i, c in enumerate(creators, 1):
        ca = getattr(c, "content_analysis", None)
        llm_ozet = getattr(ca, "llm_ozet", "") if ca else ""
        
        item = {
            "#": i,
            "Kullanıcı Adı": getattr(c, "username", ""),
            "Platform": get_platform_name(c),
            "Takipçi": getattr(c, "followers", 0) or 0,
            "Etkileşim (%)": round(getattr(c, "engagement_rate", 0.0) or 0.0, 2),
            "Skor": round(getattr(c, "final_score", 0.0) or getattr(c, "score", 0.0) or 0.0, 1),
            "Profil URL": getattr(c, "profile_url", "")
        }
        if depth >= 3:
            item["AI Özeti"] = llm_ozet[:80] + "..." if len(llm_ozet) > 80 else llm_ozet
            
        data.append(item)
        
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

def render_summary_metrics(creators: List[Any]) -> None:
    """Arama sonuçlarının genel istatistiklerini gösterir."""
    if not creators:
        return
        
    total = len(creators)
    scores = [getattr(c, "final_score", 0.0) or getattr(c, "score", 0.0) or 0.0 for c in creators]
    avg_score = sum(scores) / max(1, len(scores))
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Bulunan", total)
    col2.metric("Ortalama Skor", f"{avg_score:.1f}/100")
    
    platforms = {}
    for c in creators:
        plat = get_platform_name(c)
        platforms[plat] = platforms.get(plat, 0) + 1
    
    platform_str = ", ".join([f"{k}: {v}" for k, v in platforms.items()])
    col3.metric("Platform Dağılımı", platform_str)

def render_download_buttons(creators: List[Any], keyword: str) -> None:
    """Sonuçları indirme butonlarını gösterir."""
    if not creators:
        return
        
    records = []
    for c in creators:
        ca = getattr(c, "content_analysis", None)
        records.append({
            "Kullanıcı Adı": getattr(c, "username", ""),
            "Platform": get_platform_name(c),
            "Takipçi": getattr(c, "followers", 0) or 0,
            "Etkileşim Oranı (%)": getattr(c, "engagement_rate", 0.0) or 0.0,
            "Skor": getattr(c, "final_score", 0.0) or getattr(c, "score", 0.0) or 0.0,
            "Bio": getattr(c, "bio", ""),
            "Profil URL": getattr(c, "profile_url", ""),
            "AI Özeti": getattr(ca, "llm_ozet", "") if ca else ""
        })
        
    df = pd.DataFrame(records)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Tüm Sonuçlar")
    excel_data = excel_buffer.getvalue()
    
    json_data = json.dumps([c.to_dict() if hasattr(c, "to_dict") else dict(c) for c in creators], indent=2, ensure_ascii=False)

    safe_kw = keyword.replace(" ", "_").lower()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📗 Excel Raporu İndir (.xlsx)",
            data=excel_data,
            file_name=f"influencer_{safe_kw}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            label="📁 JSON Formatında İndir",
            data=json_data.encode('utf-8'),
            file_name=f"influencer_{safe_kw}.json",
            mime="application/json"
        )

def render_comparison_table(creators: List[Any]) -> None:
    """Seçilen içerik üreticilerini yan yana karşılaştırır."""
    if not creators:
        return
        
    st.subheader("Karşılaştırma")
    cols = st.columns(min(len(creators), 4))
    for i, c in enumerate(creators[:4]):
        with cols[i]:
            st.markdown(f"**{getattr(c, 'username', '')}**")
            st.markdown(f"**Platform:** {get_platform_name(c)}")
            st.markdown(f"**Takipçi:** {getattr(c, 'followers', 0):,}")
            st.markdown(f"**Etkileşim:** %{getattr(c, 'engagement_rate', 0.0):.2f}")
            st.markdown(f"**Skor:** {getattr(c, 'final_score', 0.0):.1f}")

def render_search_progress() -> None:
    """Arama işlemi için animasyonlu ilerleme çubuğu gösterir."""
    st.info("🔎 Platformlarda arama yapılıyor ve profiller analiz ediliyor...")
