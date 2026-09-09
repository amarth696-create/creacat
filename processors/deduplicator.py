import re
from models.creator import Creator
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Deduplicator:
    """Farklı platformlardaki aynı içerik üreticilerini tespit eder ve birleştirir."""
    
    def deduplicate(self, creators: list[Creator]) -> list[Creator]:
        """
        Farklı platformlardaki aynı kişileri bulup birleştirerek tekilleştirme yapar.
        
        Args:
            creators (list[Creator]): Ham ve birden fazla platformda olabilecek üretici listesi.
            
        Returns:
            list[Creator]: Tekilleştirilmiş içerik üreticileri listesi.
        """
        grouped_creators = {}
        
        for c in creators:
            norm_username = self._normalize_username(c.username)
            if not norm_username:
                norm_username = f"unknown_{id(c)}"
                
            if norm_username not in grouped_creators:
                grouped_creators[norm_username] = []
            grouped_creators[norm_username].append(c)
            
        deduplicated_list = []
        duplication_count = 0
        
        for norm_name, group in grouped_creators.items():
            if len(group) > 1:
                duplication_count += len(group) - 1
                merged_creator = self._merge_creators(group)
                deduplicated_list.append(merged_creator)
            else:
                deduplicated_list.append(group[0])
                
        logger.info(f"Tekilleştirme tamamlandı: {duplication_count} mükerrer kayıt birleştirildi.")
        return deduplicated_list
        
    def _normalize_username(self, username: str) -> str:
        """Kullanıcı adını karşılaştırma için temizler (küçük harf, noktalama işaretlerini kaldırma)."""
        if not username:
            return ""
        name = str(username).lower().strip()
        name = re.sub(r'[_.]', '', name)
        return name
        
    def _merge_creators(self, group: list[Creator]) -> Creator:
        """Aynı kişiye ait birden fazla kaydı en yüksek skorlu ana kayıt altında birleştirir."""
        sorted_group = sorted(group, key=lambda c: getattr(c, 'score', 0) or 0, reverse=True)
        primary = sorted_group[0]
        
        other_platforms = [c.platform for c in sorted_group[1:] if getattr(c, 'platform', None) != getattr(primary, 'platform', None)]
        
        if other_platforms:
            note = f" (Ayrıca şurada da bulundu: {', '.join(set(other_platforms))})"
            if hasattr(primary, 'bio'):
                primary.bio = str(getattr(primary, 'bio', '')) + note
                
        return primary
