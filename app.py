import streamlit as st
import time
from typing import List, Dict, Any, Optional
from config import Config
from ui.state import init_session_state, get_state, set_state
from ui.sidebar import render_sidebar
from ui.components import (
    render_creator_card, render_results_table, 
    render_summary_metrics, render_download_buttons, render_search_progress
)
from ui.chatbot import ChatBot
from ai.conversation import ConversationManager
from ai.response_formatter import format_search_results
from models.creator import Creator
from models.search_session import SearchSession
from searchers.youtube_searcher import YouTubeSearcher
from searchers.tiktok_searcher import TikTokSearcher
from searchers.instagram_searcher import InstagramSearcher
from searchers.ai_searcher import AISearcher
from searchers.live_searcher import LiveSearcher
from searchers.google_enricher import GoogleEnricher
from processors.normalizer import Normalizer
from processors.scorer import Scorer
from processors.deduplicator import Deduplicator
from processors.filterer import Filterer
from analyzers.analysis_orchestrator import AnalysisOrchestrator

from processors.expander import KeywordExpander

st.set_page_config(
    page_title="İçerik Üretici Keşif Sistemi",
    page_icon="🔍",
    layout="wide"
)

def balance_by_platform(creators: List[Creator], requested_platforms: List[str], limit: int = 30) -> List[Creator]:
    """
    Seçilen platformlar arasında homojen ve dengeli dağılım sağlar (Round-Robin).
    Böylece hiçbir platform (örneğin YouTube) diğer platformları (Instagram, TikTok) listeden eleyemez.
    """
    if not requested_platforms or len(requested_platforms) <= 1:
        return creators[:limit]
        
    plat_groups = {p.lower(): [] for p in requested_platforms}
    others = []
    
    for c in creators:
        p_name = str(getattr(c, 'platform', '')).lower()
        matched = False
        for p_key in plat_groups:
            if p_key in p_name:
                plat_groups[p_key].append(c)
                matched = True
                break
        if not matched:
            others.append(c)
            
    # Round-Robin sırayla her platformdan birer üretici seç
    balanced = []
    active_keys = [k for k in plat_groups if plat_groups[k]]
    idx = 0
    while len(balanced) < limit and active_keys:
        still_active = []
        for k in active_keys:
            if idx < len(plat_groups[k]):
                balanced.append(plat_groups[k][idx])
                if idx + 1 < len(plat_groups[k]):
                    still_active.append(k)
        active_keys = still_active
        idx += 1
        
    if len(balanced) < limit and others:
        balanced.extend(others[:limit - len(balanced)])
        
    return balanced[:limit]

def execute_search(params, settings):
    """Gerçek arama motorunu ve otomatik türetilen ilişkili anahtar kelimeleri çalıştırır."""
    keyword = params.get("keyword") or params.get("konu") or ""
    if not keyword:
        return [], [], []
        
    raw_platforms = params.get("platforms") or settings.get("platforms", ["YouTube", "TikTok", "Instagram"])
    selected_platforms = [p.lower() for p in raw_platforms]
    # Kullanıcı isteği doğrultusunda arama ve analiz derinliği her zaman maksimum (3) seviyededir
    depth = 3
    
    min_followers = params.get("min_followers") if params.get("min_followers") is not None else settings.get("min_followers", 1000)
    max_followers = params.get("max_followers") if params.get("max_followers") is not None else settings.get("max_followers")
    if max_followers == 0:
        max_followers = None
    if min_followers == 0:
        min_followers = None
    
    country = params.get("country") or settings.get("country")
    language = params.get("language") or settings.get("language")
    
    # 1. Otomatik İlgili Anahtar Kelime ve Hashtag Genişletmesi
    expanded = KeywordExpander.expand(keyword, api_key=Config.GEMINI_API_KEY)
    related_keywords = expanded.get("related_keywords", [])
    hashtags = expanded.get("hashtags", [])
    sub_niches = expanded.get("sub_niches", [])
    
    searchers = {}
    if "youtube" in selected_platforms and Config.YOUTUBE_API_KEY:
        searchers["youtube"] = YouTubeSearcher(Config.YOUTUBE_API_KEY)
    if "tiktok" in selected_platforms:
        searchers["tiktok"] = TikTokSearcher(Config)
    if "instagram" in selected_platforms:
        searchers["instagram"] = InstagramSearcher(Config)
        
    google_enricher = GoogleEnricher(Config)
    normalizer = Normalizer()
    analysis_orchestrator = AnalysisOrchestrator(depth=depth, config=Config)
    scorer = Scorer(depth=depth)
    deduplicator = Deduplicator()
    filterer = Filterer(min_followers=min_followers, max_followers=max_followers, country=country, language=language)
    
    raw_results = []
    
    # 1. CANLI VE AKTİF WEB TARAMASI (API anahtarsız gerçek zamanlı canlı platform kazıma)
    try:
        live_searcher = LiveSearcher()
        live_results = live_searcher.search(
            query=keyword,
            limit=Config.DEFAULT_LIMIT,
            filters={
                "min_followers": min_followers,
                "max_followers": max_followers,
                "platforms": raw_platforms
            }
        )
        raw_results.extend(live_results)
    except Exception as e:
        pass

    # 2. Platformlarda Ana Kelime ve Türetilen En İlgili Kelimeler ile Çoklu Tarama
    terms_to_search = [keyword] + [k for k in related_keywords[:3] if k.lower() != keyword.lower()]
    for term in terms_to_search:
        for plat_name, searcher in searchers.items():
            try:
                plat_results = searcher.search(query=term, limit=Config.DEFAULT_LIMIT)
                raw_results.extend(plat_results)
            except Exception as e:
                st.warning(f"{plat_name.capitalize()} '{term}' araması sırasında uyarı: {e}")
            
    # 2. Yapay Zeka & Hashtag Keşif Motoru (Tüm türetilen anahtar kelimeleri ve takipçi kısıtlarını işler)
    try:
        ai_searcher = AISearcher(Config.GEMINI_API_KEY)
        ai_results = ai_searcher.search(
            query=keyword,
            limit=Config.DEFAULT_LIMIT,
            filters={
                "min_followers": min_followers,
                "max_followers": max_followers,
                "platforms": raw_platforms,
                "country": country,
                "language": language
            }
        )
        raw_results.extend(ai_results)
    except Exception as e:
        st.warning(f"AI Keşif Motoru uyarısı: {e}")
            
    if not raw_results:
        return [], hashtags, related_keywords
        
    normalized = normalizer.normalize(raw_results)
    
    # Zenginleştirme
    enriched = []
    for c in normalized:
        try:
            enriched.append(google_enricher.enrich(c))
        except Exception:
            enriched.append(c)
            
    # Tekrarları temizle & filtrele
    unique_creators = deduplicator.deduplicate(enriched)
    filtered = filterer.filter(unique_creators)
    
    # Eğer katı filtreler sonucu 0'a indirdiyse, gizli olmayan ve 3 aydan eski olmayan profilleri koru
    if not filtered and unique_creators:
        valid_pool = [c for c in unique_creators if not getattr(c, 'is_private', False) and not getattr(c, 'is_excluded_for_inactivity', False)]
        filtered = valid_pool[:Config.DEFAULT_LIMIT]

    # Analiz
    analyzed = []
    for c in filtered:
        try:
            analyzed.append(analysis_orchestrator.analyze(c, keyword=keyword))
        except Exception:
            analyzed.append(c)
            
    # Puanlama & sıralama
    scored = scorer.score(analyzed, keyword=keyword)
    sorted_creators = sorted(scored, key=lambda c: getattr(c, "final_score", 0.0) or 0.0, reverse=True)
    # Seçilen platformlar arasında eşit ve homojen dağılım sağla (YouTube, Instagram, TikTok dengesi)
    final_creators = balance_by_platform(sorted_creators, raw_platforms, limit=Config.DEFAULT_LIMIT)
    
    # SQLite'a oturumu kaydet
    try:
        session = SearchSession(
            keyword=keyword,
            platforms=selected_platforms,
            filters={"min_followers": min_followers, "max_followers": max_followers, "country": country, "language": language},
            depth=depth,
            results=final_creators
        )
        session.save_to_db(Config.DB_PATH)
    except Exception:
        pass
        
    return final_creators, hashtags, related_keywords

def main():
    init_session_state()
    settings = render_sidebar()
    
    st.title("🗣️ İçerik Üretici Keşif Asistanı")
    st.caption("TikTok, Instagram ve YouTube üzerinde konulara göre içerik üreticilerini bulun ve analiz edin.")
    
    bot = ChatBot(Config.GEMINI_API_KEY)
    conv = ConversationManager()
    
    for msg in get_state("chat_history"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "results" in msg and msg["results"]:
                render_summary_metrics(msg["results"])
                render_results_table(msg["results"], settings["depth"])
                render_download_buttons(msg["results"], "arama")
                for c in msg["results"]:
                    render_creator_card(c)
            
    prompt = st.chat_input("Hangi konuda influencer arıyorsunuz?")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
            
        existing_history = get_state("chat_history")
        response = bot.process_message(prompt, settings, history=existing_history)
        
        history = list(existing_history)
        history.append({"role": "user", "content": prompt})
        set_state("chat_history", history)
        
        with st.chat_message("assistant"):
            results = None
            hashtags = []
            related_keywords = []
            if response["action"] == "search":
                st.info(response["text"])
                with st.status("🔍 Platformlarda aranıyor ve analiz ediliyor..."):
                    render_search_progress()
                    results, hashtags, related_keywords = execute_search(response["params"], settings)
                    if related_keywords:
                        st.write(f"💡 **Otomatik Türetilen İlgili Arama Kelimeleri:** {', '.join([f'`{k}`' for k in related_keywords[:6]])}")
                    if hashtags:
                        st.write(f"🏷️ **Taranan Hashtag & Alt Nişler:** {', '.join(hashtags[:6])}")
                
                kw = response["params"].get("keyword", prompt)
                if results:
                    list_text = format_search_results(results, kw, hashtags=hashtags, related_keywords=related_keywords)
                    st.markdown(list_text)
                    render_summary_metrics(results)
                    render_results_table(results, settings["depth"])
                    render_download_buttons(results, kw)
                    for c in results:
                        render_creator_card(c)
                    saved_content = list_text
                else:
                    empty_text = f"🔍 **'{kw}'** konusu için kriterlere uygun içerik üreticisi bulunamadı. Filtreleri genişleterek tekrar deneyebilirsiniz."
                    st.warning(empty_text)
                    saved_content = empty_text
            else:
                st.markdown(response["text"])
                saved_content = response["text"]
            
            history = get_state("chat_history")
            msg_data = {"role": "assistant", "content": saved_content}
            if results:
                msg_data["results"] = results
            history.append(msg_data)
            set_state("chat_history", history)

if __name__ == "__main__":
    main()
