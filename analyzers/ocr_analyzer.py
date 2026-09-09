import os
from analyzers.base_analyzer import BaseAnalyzer
from models.creator import Creator

class OcrAnalyzer(BaseAnalyzer):
    """
    Seviye 2b: Thumbnail OCR analizi.
    """
    @property
    def level(self) -> int:
        return 2

    def analyze(self, creator: Creator, keyword: str, thumbnail_paths: list[str] = None) -> Creator:
        if not thumbnail_paths:
            return creator

        self.logger.info(f"{creator.username} için OCR analizi başlatılıyor.")
        
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            self.logger.error("pytesseract veya Pillow kütüphanesi bulunamadı.")
            return creator

        extracted_texts = []
        for path in thumbnail_paths:
            if not os.path.exists(path):
                self.logger.error(f"Thumbnail bulunamadı: {path}")
                continue
            
            try:
                text = pytesseract.image_to_string(Image.open(path))
                if text.strip():
                    extracted_texts.append(text.strip())
            except Exception as e:
                self.logger.error(f"OCR hatası {path}: {e}")
                
        if not creator.content_analysis:
            from models.analysis_result import ContentAnalysis
            creator.content_analysis = ContentAnalysis()
            
        creator.content_analysis.thumbnail_texts = extracted_texts
        self.logger.info(f"{creator.username} için OCR analizi tamamlandı.")
        return creator
