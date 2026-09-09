from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class ContentAnalysis:
    """İçerik analizi sonuçlarını tutan veri sınıfı."""
    konu_etiketleri: List[str] = field(default_factory=list)
    ana_konular: List[str] = field(default_factory=list)
    keyword_skoru: float = 0.0
    en_sik_hashtags: List[str] = field(default_factory=list)
    icerik_tutarliligi: float = 0.0
    whisper_transcripts: Optional[List[str]] = None
    konusma_konulari: Optional[List[str]] = None
    thumbnail_texts: Optional[List[str]] = None
    gorsel_konu: Optional[str] = None
    gorsel_guven: Optional[float] = None
    nis_alani: Optional[str] = None
    alt_konular: Optional[List[str]] = None
    hedef_kitle: Optional[str] = None
    icerik_tarzi: Optional[str] = None
    sponsor_orani: Optional[str] = None
    llm_ozet: Optional[str] = None
    llm_keyword_ilgi: Optional[float] = None
    llm_kaynak: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe dönüştürür."""
        return asdict(self)


@dataclass
class Creator:
    """İçerik üreticisi bilgilerini tutan veri sınıfı."""
    username: str
    display_name: str
    platform: str
    profile_url: str
    followers: int = 0
    total_likes: int = 0
    total_views: int = 0
    video_count: int = 0
    post_count: int = 0
    bio: str = ""
    country: str = ""
    language: str = ""
    avg_likes_per_post: float = 0.0
    avg_comments_per_post: float = 0.0
    avg_views_per_video: float = 0.0
    engagement_rate: float = 0.0
    content_analysis: Optional[ContentAnalysis] = None
    final_score: float = 0.0
    search_keyword: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)
    analysis_depth: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe dönüştürür."""
        data = asdict(self)
        if self.scraped_at:
            data['scraped_at'] = self.scraped_at.isoformat()
        if self.content_analysis:
            data['content_analysis'] = self.content_analysis.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Creator':
        """Sözlükten sınıf oluşturur."""
        if 'scraped_at' in data and isinstance(data['scraped_at'], str):
            data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
            
        if 'content_analysis' in data and data['content_analysis']:
            if isinstance(data['content_analysis'], dict):
                data['content_analysis'] = ContentAnalysis(**data['content_analysis'])
                
        return cls(**data)
