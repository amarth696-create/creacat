import os
from analyzers.base_analyzer import BaseAnalyzer
from models.creator import Creator

class VisualAnalyzer(BaseAnalyzer):
    """
    Seviye 2c: Thumbnail görsel analizi (CLIP).
    """
    def __init__(self, device=None):
        super().__init__()
        if device is None:
            try:
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except ImportError:
                self.device = 'cpu'
        else:
            self.device = device
            
        self.processor = None
        self.model = None
        self.default_categories = ['fitness', 'yemek', 'teknoloji', 'moda', 'güzellik', 'seyahat', 'eğitim', 'oyun', 'müzik', 'komedi', 'sanat', 'spor', 'sağlık', 'finans', 'otomobil']

    @property
    def level(self) -> int:
        return 2

    def analyze(self, creator: Creator, keyword: str, thumbnail_paths: list[str] = None, categories: list[str] = None) -> Creator:
        if not thumbnail_paths:
            return creator
            
        categories = categories or self.default_categories
        
        self.logger.info(f"{creator.username} için görsel analiz başlatılıyor.")
        
        try:
            from transformers import CLIPProcessor, CLIPModel
            from PIL import Image
            import torch
        except ImportError:
            self.logger.error("transformers, Pillow veya torch bulunamadı. Görsel analiz atlanıyor.")
            return creator

        if self.model is None:
            self.logger.info(f"CLIP modeli {self.device} üzerinde yükleniyor...")
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        best_category = None
        best_confidence = 0.0

        for path in thumbnail_paths:
            if not os.path.exists(path):
                continue
                
            try:
                image = Image.open(path)
                inputs = self.processor(text=categories, images=image, return_tensors="pt", padding=True).to(self.device)
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
                
                max_prob, max_idx = torch.max(probs, dim=1)
                confidence = max_prob.item()
                category = categories[max_idx.item()]
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_category = category
                    
            except Exception as e:
                self.logger.error(f"Görsel analiz hatası {path}: {e}")

        if not creator.content_analysis:
            from models.analysis_result import ContentAnalysis
            creator.content_analysis = ContentAnalysis()
            
        creator.content_analysis.gorsel_konu = best_category
        creator.content_analysis.gorsel_guven = best_confidence
        
        self.logger.info(f"{creator.username} için görsel analiz tamamlandı.")
        return creator
