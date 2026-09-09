import os
from analyzers.base_analyzer import BaseAnalyzer
from models.creator import Creator

class WhisperAnalyzer(BaseAnalyzer):
    """
    Seviye 2a: Fısıltı ile video transkript analizi.
    """
    def __init__(self, model_name='base', device=None):
        super().__init__()
        self.model_name = model_name
        if device is None:
            try:
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except ImportError:
                self.device = 'cpu'
        else:
            self.device = device
        self.model = None

    @property
    def level(self) -> int:
        return 2

    def analyze(self, creator: Creator, keyword: str, video_paths: list[str] = None) -> Creator:
        if not video_paths:
            self.logger.warning(f"{creator.username} için video yolu belirtilmedi.")
            return creator

        self.logger.info(f"{creator.username} için Whisper transkript analizi başlatılıyor.")
        
        try:
            import whisper
        except ImportError:
            self.logger.error("Whisper kütüphanesi bulunamadı.")
            return creator

        if self.model is None:
            self.logger.info(f"Whisper {self.model_name} modeli {self.device} üzerinde yükleniyor...")
            self.model = whisper.load_model(self.model_name, device=self.device)

        transcripts = []
        for path in video_paths:
            if not os.path.exists(path):
                self.logger.error(f"Video bulunamadı: {path}")
                continue
            
            self.logger.info(f"{path} transkript ediliyor...")
            try:
                result = self.model.transcribe(path)
                transcripts.append(result["text"])
            except Exception as e:
                self.logger.error(f"Transkript hatası {path}: {e}")

        if not creator.content_analysis:
            from models.analysis_result import ContentAnalysis
            creator.content_analysis = ContentAnalysis()

        creator.content_analysis.whisper_transcripts = transcripts
        creator.content_analysis.konusma_konulari = [keyword] if keyword.lower() in " ".join(transcripts).lower() else []

        self.logger.info(f"{creator.username} için Whisper analizi tamamlandı.")
        return creator
