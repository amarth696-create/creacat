import streamlit as st
from typing import Dict, Any
from auth.auth_manager import AuthManager
from ai.chat_storage import ChatStorage

def render_sidebar() -> Dict[str, Any]:
    """Yan menüyü oluşturur: Kullanıcı bilgisi, Gemini tarzı Sohbet Listesi ve Arama Ayarları."""
    
    # 1. KULLANICI PROFİLİ VE ÇIKIŞ YAP
    current_user = AuthManager.get_current_user()
    if current_user:
        st.sidebar.markdown(f"👤 **{current_user['name']}** (`{current_user['email']}`)")
        if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True, key="btn_logout"):
            AuthManager.logout()
            st.rerun()
        st.sidebar.markdown("---")
    
    # 2. GEMINI TARZI YENİ SOHBET BUTONU
    if st.sidebar.button("➕ Yeni Sohbet Başlat", type="primary", use_container_width=True, key="btn_new_chat"):
        if current_user:
            new_id = ChatStorage.create_conversation(current_user["email"], title="Yeni Sohbet")
            st.session_state["active_chat_id"] = new_id
            st.session_state["chat_history"] = []
            st.session_state["view_mode"] = "chat"
            st.query_params.clear()
            st.rerun()

    # 3. SOHBET GEÇMİŞİ LİSTESİ (GEMINI / CHATGPT TARZI)
    st.sidebar.subheader("💬 Sohbet Geçmişi")
    if current_user:
        conversations = ChatStorage.get_user_conversations(current_user["email"])
        active_id = st.session_state.get("active_chat_id")
        
        # Eğer henüz aktif bir sohbet yoksa sonuncuyu seç veya yeni aç
        if not active_id and conversations:
            active_id = conversations[0]["id"]
            st.session_state["active_chat_id"] = active_id
            st.session_state["chat_history"] = ChatStorage.get_messages(active_id)
        
        if conversations:
            for conv in conversations[:12]:
                c_id = conv["id"]
                title = conv["title"] or "Yeni Sohbet"
                is_active = (c_id == active_id)
                prefix = "👉 " if is_active else "💭 "
                display_label = f"{prefix}{title}"
                
                col_btn, col_del = st.sidebar.columns([5, 1])
                with col_btn:
                    if st.button(display_label, key=f"conv_{c_id}", use_container_width=True):
                        st.session_state["active_chat_id"] = c_id
                        st.session_state["chat_history"] = ChatStorage.get_messages(c_id)
                        st.session_state["view_mode"] = "chat"
                        st.query_params.clear()
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{c_id}", help="Bu sohbeti sil"):
                        ChatStorage.delete_conversation(c_id)
                        if st.session_state.get("active_chat_id") == c_id:
                            st.session_state["active_chat_id"] = None
                            st.session_state["chat_history"] = []
                        st.rerun()
        else:
            st.sidebar.caption("Henüz kayıtlı bir sohbetiniz yok.")
            
    st.sidebar.markdown("---")
    
    # 4. ARAMA AYARLARI
    with st.sidebar.expander("⚙️ Arama & Platform Filtreleri", expanded=True):
        platforms = st.multiselect(
            "Platformlar",
            options=["YouTube", "TikTok", "Instagram"],
            default=["YouTube", "TikTok", "Instagram"],
            help="Arama yapılacak platformları seçin."
        )
        
        depth = 3
        st.caption("⚡ **Analiz Seviyesi:** Maksimum (Derin AI Analizi)")
        
        min_followers = st.number_input(
            "Minimum Takipçi",
            min_value=0,
            value=1000,
            step=1000,
            help="Minimum takipçi sayısını belirleyin."
        )
        
        max_followers = st.number_input(
            "Maksimum Takipçi (0 = Sınırsız)",
            min_value=0,
            value=0,
            step=10000,
            help="Maksimum takipçi sınırı. 0 bırakılırsa üst sınır uygulanmaz."
        )
        
        country = st.selectbox(
            "Ülke",
            options=["Hepsi", "Türkiye", "ABD", "Almanya", "İngiltere", "Fransa"],
            index=0
        )
        
        language = st.selectbox(
            "Dil",
            options=["Hepsi", "Türkçe", "İngilizce", "Almanca"],
            index=0
        )

        st.markdown("---")
        st.subheader("📊 Sıralama & İşbirliği")
        sort_by = st.selectbox(
            "Sonuçları Sırala",
            options=[
                "AI Uygunluk Skoru (Varsayılan)",
                "Yatay Video Ortalama İzlenmesi",
                "Shorts Ortalama İzlenmesi",
                "Takipçi Sayısı"
            ],
            index=0,
            help="İçerik üreticilerini seçtiğiniz performans metriğine göre sıralar."
        )

        sponsor_filter = st.selectbox(
            "İşbirliği / Reklam Filtresi",
            options=[
                "Tümü (Filtresiz)",
                "Yalnızca İşbirliği Yapmış Hesaplar",
                "Yalnızca Organik (İşbirliksiz)"
            ],
            index=0,
            help="Önceden ticari işbirliği/reklam yapmış hesapları ayıklar."
        )

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
        "max_followers": max_followers if max_followers > 0 else None,
        "country": country if country != "Hepsi" else None,
        "language": language if language != "Hepsi" else None,
        "sort_by": sort_by,
        "sponsor_filter": sponsor_filter
    }
