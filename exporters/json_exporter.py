import os
import json
from datetime import datetime

from models.creator import Creator
from utils.logger import get_logger

logger = get_logger(__name__)

class JsonExporter:
    """JSON formatında dışa aktarma işlemlerini yöneten sınıf."""

    def export(self, creators: list[Creator], keyword: str, output_dir: str = "data/results") -> str:
        """
        İçerik üreticilerini yapılandırılmış JSON formatında dışa aktarır.
        """
        logger.info(f"'{keyword}' için JSON raporu oluşturuluyor...")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Çıktı dizini oluşturuldu: {output_dir}")

        if keyword.endswith(".json"):
            filename = keyword
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_keyword = keyword.replace(" ", "_").lower()
            filename = f"{safe_keyword}_{timestamp}.json"
            
        filepath = os.path.join(output_dir, filename)

        # Platformları topla
        platforms = list({c.platform for c in creators if hasattr(c, 'platform') and c.platform})
        
        # Depth'i tahmin et
        max_depth = 1
        for c in creators:
            if hasattr(c, 'llm_summary') and c.llm_summary:
                max_depth = max(max_depth, 3)
            elif hasattr(c, 'engagement_rate') and c.engagement_rate:
                max_depth = max(max_depth, 2)

        data = {
            "metadata": {
                "keyword": keyword,
                "search_date": datetime.now().isoformat(),
                "total_results": len(creators),
                "platforms": platforms,
                "depth": max_depth
            },
            "creators": [
                c.to_dict() if hasattr(c, 'to_dict') else c.__dict__ 
                for c in creators
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON raporu başarıyla oluşturuldu: {filepath}")
        return filepath
