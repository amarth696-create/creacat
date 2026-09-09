from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass
class AnalysisResult:
    """Seviye bazlı analiz sonuçlarını sarmalayan veri sınıfı."""
    level: int
    score: float
    data: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe dönüştürür."""
        return asdict(self)
