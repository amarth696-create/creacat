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
    avg_video_views: int = 0
    avg_shorts_views: int = 0
    has_sponsored_content: bool = False
    sponsored_video_count: int = 0
    sponsor_keywords_found: List[str] = field(default_factory=list)
    collaborated_brands: List[str] = field(default_factory=list)
    engagement_rate: float = 0.0
    content_analysis: Optional[ContentAnalysis] = None
    final_score: float = 0.0
    recent_contents: List[str] = field(default_factory=list)
    is_private: bool = False
    is_active: bool = True
    is_excluded_for_inactivity: bool = False
    last_post_date: Optional[str] = None
    inactivity_warning: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    analysis_depth: int = 1

    def set_activity(self, time_text: Optional[str] = None, is_active: Optional[bool] = None) -> None:
        """Son paylaşım tarihine göre profilin aktivite ve 3+ ay hariç tutulma durumunu belirler."""
        if time_text:
            self.last_post_date = str(time_text).strip()
            from utils.activity import evaluate_activity_status
            act, dt, warn, is_exc = evaluate_activity_status(self.last_post_date)
            self.is_active = act if is_active is None else is_active
            self.inactivity_warning = warn if not self.is_active else None
            self.is_excluded_for_inactivity = is_exc
        elif is_active is not None:
            self.is_active = is_active
            if not is_active and not self.inactivity_warning:
                self.inactivity_warning = "⚠️ Bu profil 2 aydan uzun süredir yeni içerik üretmemiştir (İnaktif)."


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
