import streamlit as st
import time
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
from searchers.google_enricher import GoogleEnricher
from processors.normalizer import Normalizer
from processors.scorer import Scorer
from processors.deduplicator import Deduplicator
from processors.filterer import Filterer
from analyzers.analysis_orchestrator import AnalysisOrchestrator

st.set_page_config(
    page_title="İçerik Üretici Keşif Sistemi",
    page_icon="🔍",
    layout="wide"
)

def execute_search(params, settings):
    """Gerçek arama motorunu çalıştırır."""
    keyword = params.get("keyword") or params.get("konu") or ""
    if not keyword:
        return []
        
    raw_platforms = params.get("platforms") or settings.get("platforms", ["YouTube", "TikTok", "Instagram"])
    selected_platforms = [p.lower() for p in raw_platforms]
    depth = params.get("depth") or settings.get("depth", 1)
    
    min_followers = params.get("min_followers") if params.get("min_followers") is not None else settings.get("min_followers", 1000)
    max_followers = params.get("max_followers") if params.get("max_followers") is not None else settings.get("max_followers")
    if max_followers == 0:
        max_followers = None
    if min_followers == 0:
        min_followers = None
    
    country = params.get("country") or settings.get("country")
    language = params.get("language") or settings.get("language")

    
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
    for plat_name, searcher in searchers.items():
        try:
            plat_results = searcher.search(query=keyword, limit=Config.DEFAULT_LIMIT)
            raw_results.extend(plat_results)
        except Exception as e:
            st.warning(f"{plat_name.capitalize()} araması sırasında uyarı: {e}")
            
    if not raw_results:
        return []
        
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
    final_creators = sorted_creators[:Config.DEFAULT_LIMIT]
    
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
        
    return final_creators

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
            if response["action"] == "search":
                st.info(response["text"])
                with st.status("🔍 Platformlarda aranıyor ve analiz ediliyor..."):
                    render_search_progress()
                    results = execute_search(response["params"], settings)
                
                kw = response["params"].get("keyword", prompt)
                if results:
                    list_text = format_search_results(results, kw)
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
