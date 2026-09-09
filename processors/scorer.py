import math
from models.creator import Creator
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Scorer:
    """İçerik üreticilerini belirli bir anahtar kelime ve derinliğe göre puanlar."""
    
    def __init__(self, depth: int = 1):
        """
        Derinlik seviyesine göre puanlama ağırlıklarını ayarlar.
        
        Args:
            depth (int): Analiz derinliği (1, 2 veya 3).
        """
        self.depth = depth
        if depth == 1:
            self.weights = {
                'metin_keyword': 0.35,
                'engagement': 0.30,
                'takipci': 0.15,
                'siklik': 0.10,
                'platform': 0.10
            }
        elif depth == 2:
            self.weights = {
                'metin_keyword': 0.20,
                'ses_keyword': 0.25,
                'gorsel_uyum': 0.10,
                'engagement': 0.25,
                'takipci': 0.10,
                'siklik': 0.05,
                'platform': 0.05
            }
        elif depth == 3:
            self.weights = {
                'llm_keyword_ilgi': 0.40,
                'engagement': 0.25,
                'takipci': 0.10,
                'icerik_tutarliligi': 0.15,
                'siklik': 0.05,
                'platform': 0.05
            }
        else:
            logger.warning(f"Geçersiz derinlik seviyesi: {depth}. Varsayılan (1) kullanılacak.")
            self.depth = 1
            self.weights = {
                'metin_keyword': 0.35, 'engagement': 0.30, 'takipci': 0.15, 
                'siklik': 0.10, 'platform': 0.10
            }
            
        logger.info(f"Scorer başlatıldı. Derinlik: {self.depth}")

    def calculate_score(self, creator: Creator, keyword: str = "") -> float:
        """İçerik üreticisi için genel skoru hesaplar (0-100 arası)."""
        score = 0.0
        
        # Takipçi ve etkileşim skorları
        takipci_skoru = self._normalize_followers(creator.followers) * self.weights.get('takipci', 0)
        engagement_skoru = self._normalize_engagement(getattr(creator, 'engagement_rate', 0.0)) * self.weights.get('engagement', 0)
        
        # Sıklık (frequency) ve Platform
        siklik_skoru = self._calculate_content_frequency(creator) * self.weights.get('siklik', 0)
        platform_skoru = 80.0 * self.weights.get('platform', 0)
        
        # Keyword skoru
        if self.depth in [1, 2]:
            keyword_skoru = self._calculate_keyword_score(creator, keyword) * self.weights.get('metin_keyword', 0)
            score += keyword_skoru
            
            if self.depth == 2:
                score += 50.0 * self.weights.get('ses_keyword', 0)
                score += 50.0 * self.weights.get('gorsel_uyum', 0)
        else: # Depth 3
            keyword_skoru = self._calculate_keyword_score(creator, keyword) * self.weights.get('llm_keyword_ilgi', 0)
            score += keyword_skoru
            score += 50.0 * self.weights.get('icerik_tutarliligi', 0)
            
        score += takipci_skoru + engagement_skoru + siklik_skoru + platform_skoru
        
        final_score = max(0.0, min(100.0, score))
        
        creator.final_score = final_score
        setattr(creator, 'score', final_score)
            
        return final_score

    def _normalize_followers(self, count: int) -> float:
        """Takipçi sayısını log10 kullanarak 0-100 arasına normalize eder."""
        if not count or count <= 0:
            return 0.0
            
        # 1 takipçi -> 0, 100,000,000 takipçi -> ~8
        log_val = math.log10(count)
        normalized = (log_val / 8.0) * 100.0
        return max(0.0, min(100.0, normalized))

    def _normalize_engagement(self, rate: float) -> float:
        """
        Etkileşim oranını 0-100 arasına çeker. 
        > %10 mükemmel kabul edilir (100 puan).
        """
        if rate is None or rate <= 0:
            return 0.0
            
        normalized = (rate / 10.0) * 100.0
        return max(0.0, min(100.0, normalized))

    def _calculate_keyword_score(self, creator: Creator, keyword: str) -> float:
        """Anahtar kelimenin bio içindeki durumuna göre skor (0-100)."""
        if not keyword:
            return 0.0
            
        score = 0.0
        keyword_lower = keyword.lower()
        bio = getattr(creator, 'bio', '')
        
        if bio and keyword_lower in bio.lower():
            score += 50.0
            
        if score > 0:
            score += 25.0
            
        return score

    def _calculate_content_frequency(self, creator: Creator) -> float:
        """İçerik paylaşım sıklığına göre skor (0-100)."""
        return 50.0

    def score(self, creators: list[Creator], keyword: str = "") -> list[Creator]:
        """score_all için alias metot."""
        return self.score_all(creators, keyword)

    def score_all(self, creators: list[Creator], keyword: str = "") -> list[Creator]:
        """Tüm içerik üreticilerini puanlar ve azalan sırayla sıralar."""
        for c in creators:
            c.final_score = self.calculate_score(c, keyword)
            setattr(c, 'score', c.final_score)
            
        sorted_creators = sorted(creators, key=lambda x: getattr(x, 'final_score', 0), reverse=True)
        logger.info(f"{len(sorted_creators)} içerik üreticisi '{keyword}' kelimesine göre puanlandı ve sıralandı.")
        return sorted_creators
