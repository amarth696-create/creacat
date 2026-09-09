import logging
from typing import Any
from rich.progress import Progress

from analyzers.text_analyzer import TextAnalyzer
from analyzers.whisper_analyzer import WhisperAnalyzer
from analyzers.ocr_analyzer import OcrAnalyzer
from analyzers.visual_analyzer import VisualAnalyzer
from analyzers.llm_analyzer import LlmAnalyzer
from models.creator import Creator

class AnalysisOrchestrator:
    """
    Analiz sürecini yöneten orkestratör sınıfı.
    """
    def __init__(self, depth: int = 1, config: Any = None, llm_provider: str = "gemini", ollama_model: str = "llama3.1:8b", **kwargs):
        self.depth = depth
        self.config = config or {}
        self.llm_provider = llm_provider
        self.ollama_model = ollama_model
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.text_analyzer = TextAnalyzer()
        if self.depth >= 2:
            self.whisper_analyzer = WhisperAnalyzer()
            self.ocr_analyzer = OcrAnalyzer()
            self.visual_analyzer = VisualAnalyzer()
        if self.depth >= 3:
            # Config üzerinden Gemini API key'i al
            gemini_key = getattr(config, 'GEMINI_API_KEY', '') if config else ''
            self.llm_analyzer = LlmAnalyzer(provider=llm_provider, api_key=gemini_key, ollama_model=ollama_model)

    def analyze(self, creator: Creator, keyword: str = "") -> Creator:
        """Tekil creator için analiz çalıştırır."""
        self.text_analyzer.analyze(creator, keyword)
        if self.depth >= 2 and hasattr(self, 'whisper_analyzer'):
            try:
                self.whisper_analyzer.analyze(creator, keyword, [])
                self.ocr_analyzer.analyze(creator, keyword, [])
                self.visual_analyzer.analyze(creator, keyword, [])
            except Exception as e:
                self.logger.warning(f"Medya analizi hatası ({creator.username}): {e}")
        if self.depth >= 3 and hasattr(self, 'llm_analyzer'):
            try:
                self.llm_analyzer.analyze(creator, keyword)
            except Exception as e:
                self.logger.warning(f"LLM analizi hatası ({creator.username}): {e}")
        return creator

    def analyze_all(self, creators: list[Creator], keyword: str) -> list[Creator]:
        self.logger.info(f"Analiz süreci başlatılıyor (Derinlik: {self.depth})")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Derinlik 1: Metin Analizi...", total=len(creators))
            for creator in creators:
                self.text_analyzer.analyze(creator, keyword)
                progress.update(task, advance=1)
                
        if self.depth >= 2:
            top_10 = sorted(creators, key=lambda c: getattr(c.content_analysis, 'keyword_skoru', 0) if getattr(c, 'content_analysis', None) else 0, reverse=True)[:10]
            with Progress() as progress:
                task = progress.add_task("[green]Derinlik 2: Medya Analizi...", total=len(top_10))
                for creator in top_10:
                    self.whisper_analyzer.analyze(creator, keyword, [])
                    self.ocr_analyzer.analyze(creator, keyword, [])
                    self.visual_analyzer.analyze(creator, keyword, [])
                    progress.update(task, advance=1)
                    
        if self.depth >= 3:
            top_50 = sorted(creators, key=lambda c: getattr(c.content_analysis, 'keyword_skoru', 0) if getattr(c, 'content_analysis', None) else 0, reverse=True)[:50]
            with Progress() as progress:
                task = progress.add_task("[magenta]Derinlik 3: LLM Analizi...", total=len(top_50))
                for creator in top_50:
                    self.llm_analyzer.analyze(creator, keyword)
                    progress.update(task, advance=1)

        self.logger.info("Analiz süreci tamamlandı.")
        return creators
