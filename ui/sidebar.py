import streamlit as st
from typing import Dict, Any

def render_sidebar() -> Dict[str, Any]:
    """Yan menüyü oluşturur ve seçilen ayarları döner."""
    st.sidebar.title("🔍 İçerik Üretici Keşif Sistemi")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("Arama Ayarları")
    
    platforms = st.sidebar.multiselect(
        "Platformlar",
        options=["YouTube", "TikTok", "Instagram"],
        default=["YouTube", "TikTok", "Instagram"],
        help="Arama yapılacak platformları seçin."
    )
    
    depth_labels = {
        1: "1 - Hızlı Tarama",
        2: "2 - Ses+Görsel Analiz",
        3: "3 - Derin AI Analiz"
    }
    depth = st.sidebar.slider(
        "Analiz Derinliği",
        min_value=1,
        max_value=3,
        value=1,
        format="%d",
        help="1: Sadece temel metrikler, 2: İçerik analizi, 3: Detaylı profil analizi"
    )
    st.sidebar.caption(depth_labels[depth])
    
    min_followers = st.sidebar.number_input(
        "Minimum Takipçi",
        min_value=0,
        value=1000,
        step=1000,
        help="Minimum takipçi sayısını belirleyin."
    )
    
    country = st.sidebar.selectbox(
        "Ülke",
        options=["Hepsi", "Türkiye", "ABD", "Almanya", "İngiltere", "Fransa"],
        index=0
    )
    
    language = st.sidebar.selectbox(
        "Dil",
        options=["Hepsi", "Türkçe", "İngilizce", "Almanca"],
        index=0
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 Geçmiş Aramalar")
    
    try:
        import sqlite3
        from config import Config
        import os
        if os.path.exists(Config.DB_PATH):
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, keyword, created_at FROM search_sessions ORDER BY created_at DESC LIMIT 5")
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                for row in rows:
                    session_id, kw, dt_str = row
                    date_display = dt_str[:10] if dt_str else ""
                    if st.sidebar.button(f"🔍 {kw} ({date_display})", key=f"hist_{session_id}"):
                        st.session_state["selected_history_kw"] = kw
                        st.rerun()
            else:
                st.sidebar.caption("Henüz kayıtlı arama yok.")
        else:
            st.sidebar.caption("Henüz kayıtlı arama yok.")
    except Exception:
        st.sidebar.caption("Arama geçmişi yüklenemedi.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 API Durumu")
    import os
    from config import Config
    gemini_key = getattr(Config, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    youtube_key = getattr(Config, 'YOUTUBE_API_KEY', '') or os.getenv('YOUTUBE_API_KEY', '')
    
    if gemini_key:
        st.sidebar.success("🤖 Gemini API: Aktif ✅")
    else:
        st.sidebar.warning("⚠️ Gemini API: Eksik")
        manual_gemini = st.sidebar.text_input("Gemini API Key Girin:", type="password", key="manual_gemini")
        if manual_gemini:
            os.environ["GEMINI_API_KEY"] = manual_gemini
            st.rerun()
            
    if youtube_key:
        st.sidebar.success("▶️ YouTube API: Aktif ✅")
    else:
        st.sidebar.info("▶️ YouTube API: Eksik (Opsiyonel)")
        manual_yt = st.sidebar.text_input("YouTube API Key Girin:", type="password", key="manual_yt")
        if manual_yt:
            os.environ["YOUTUBE_API_KEY"] = manual_yt
            st.rerun()
    
    return {
        "platforms": platforms,
        "depth": depth,
        "min_followers": min_followers,
        "country": country if country != "Hepsi" else None,
        "language": language if language != "Hepsi" else None
    }
