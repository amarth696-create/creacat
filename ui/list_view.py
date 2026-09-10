import streamlit as st
from typing import List, Any, Dict, Optional
from ui.components import (
    render_summary_metrics,
    render_results_table,
    render_download_buttons,
    render_creator_card,
    get_platform_name
)

def render_standalone_list_page(
    creators: List[Any], 
    keyword: str = "", 
    settings: Optional[Dict[str, Any]] = None,
    conv_id: Optional[str] = None
) -> None:
    """
    Sohbet akışından bağımsız, odaklanmış ve temiz tam sayfa liste görünümü.
    Kullanıcı arama yaptığında doğrudan bu sayfaya yönlendirilebilir veya butona basarak açabilir.
    """
    settings = settings or {}
    
    # Üst Navigasyon Çubuğu (Geri Dön ve Başlık)
    nav_col1, nav_col2 = st.columns([1, 4])
    with nav_col1:
        if st.button("⬅️ Sohbete Geri Dön", key="btn_back_to_chat", use_container_width=True, type="primary"):
            st.session_state["view_mode"] = "chat"
            st.query_params.clear()
            st.rerun()
            
    with nav_col2:
        title_str = keyword.title() if keyword else "İçerik Üreticileri"
        st.markdown(f"### 📋 **{title_str}** — Arama Sonuç Listesi")

    st.caption("Aşağıda yapılan arama neticesinde doğrulanmış, filtrelenmiş ve performansları analiz edilmiş içerik üreticileri listelenmektedir.")
    st.markdown("---")

    if not creators:
        st.warning(f"🔍 **'{keyword}'** araması için gösterilecek bir liste bulunamadı.")
        if st.button("💬 Sohbete Dönerek Yeni Arama Yap", key="btn_empty_back"):
            st.session_state["view_mode"] = "chat"
            st.query_params.clear()
            st.rerun()
        return

    # 1. ÖZET METRİKLER (KPI KARTLARI)
    render_summary_metrics(creators)
    
    # 2. HIZLI FİLTRELEME & ARAMA ÇUBUĞU (LİSTE İÇİNDE ANLIK ARAMA)
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_filter = st.text_input("🔎 Liste İçinde Filtrele (Kullanıcı Adı veya Niş)", "", placeholder="Örn: barisözcan, teknoloji, gezi...")
    with f_col2:
        platform_filter = st.selectbox(
            "Platform", 
            ["Tümü"] + sorted(list(set(get_platform_name(c) for c in creators))),
            key="list_view_plat_filter"
        )
    with f_col3:
        sponsor_filter = st.selectbox(
            "İşbirliği Durumu",
            ["Tümü", "Yalnızca İşbirliği Yapanlar", "Yalnızca Organikler"],
            key="list_view_sp_filter"
        )

    # Filtreleri uygula
    filtered_creators = creators
    if search_filter:
        s_low = search_filter.lower()
        filtered_creators = [
            c for c in filtered_creators 
            if s_low in getattr(c, "username", "").lower()
            or s_low in getattr(c, "bio", "").lower()
            or any(s_low in str(item).lower() for item in getattr(c, "recent_contents", []))
            or (getattr(c, "content_analysis", None) and s_low in str(getattr(getattr(c, "content_analysis"), "nis_alani", "")).lower())
        ]
        
    if platform_filter != "Tümü":
        filtered_creators = [c for c in filtered_creators if get_platform_name(c) == platform_filter]
        
    if sponsor_filter == "Yalnızca İşbirliği Yapanlar":
        filtered_creators = [c for c in filtered_creators if getattr(c, "has_sponsored_content", False)]
    elif sponsor_filter == "Yalnızca Organikler":
        filtered_creators = [c for c in filtered_creators if not getattr(c, "has_sponsored_content", False)]

    # 3. İNDİRME BUTONLARI (EXCEL & JSON)
    st.markdown("##### 📥 Listeyi Dışa Aktar")
    render_download_buttons(filtered_creators, keyword or "influencer_listesi")

    # 4. İNTERAKTİF TABLO
    st.markdown(f"##### 📊 Detaylı Tablo ({len(filtered_creators)} / {len(creators)} Üretici)")
    render_results_table(filtered_creators, depth=settings.get("depth", 3))

    # 5. PROFİL KARTLARI (EXPANDER FORMATINDA İNCELEME)
    st.markdown("---")
    st.markdown("##### 🔍 Profil Detayları & İçerik Analizleri")
    
    # 2 sütunlu kart ızgarası
    col_left, col_right = st.columns(2)
    for idx, c in enumerate(filtered_creators):
        target_col = col_left if idx % 2 == 0 else col_right
        with target_col:
            render_creator_card(c)

    # Alt Kısım Sohbete Geri Dön Butonu
    st.markdown("---")
    bottom_c1, bottom_c2 = st.columns([1, 3])
    with bottom_c1:
        if st.button("⬅️ Sohbete Geri Dön", key="btn_back_to_chat_bottom", use_container_width=True):
            st.session_state["view_mode"] = "chat"
            st.query_params.clear()
            st.rerun()
