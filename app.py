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
        
    selected_platforms = [p.lower() for p in settings.get("platforms", ["YouTube", "TikTok", "Instagram"])]
    depth = settings.get("depth", 1)
    min_followers = settings.get("min_followers", 1000)
    country = settings.get("country")
    language = settings.get("language")
    
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
    filterer = Filterer(min_followers=min_followers, country=country, language=language)
    
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
            filters={"min_followers": min_followers, "country": country, "language": language},
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
            
        history = get_state("chat_history")
        history.append({"role": "user", "content": prompt})
        set_state("chat_history", history)
        
        response = bot.process_message(prompt, settings)
        
        with st.chat_message("assistant"):
            st.markdown(response["text"])
            results = None
            if response["action"] == "search":
                with st.status("Arama yapılıyor..."):
                    render_search_progress()
                    results = execute_search(response["params"], settings)
                
                if results:
                    st.success(format_search_results(results, prompt))
                    render_summary_metrics(results)
                    render_results_table(results, settings["depth"])
                    render_download_buttons(results, prompt)
                    for c in results:
                        render_creator_card(c)
            
            history = get_state("chat_history")
            msg_data = {"role": "assistant", "content": response["text"]}
            if results:
                msg_data["results"] = results
            history.append(msg_data)
            set_state("chat_history", history)

if __name__ == "__main__":
    main()
