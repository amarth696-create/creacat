import time
import random
import threading
from typing import Dict, Tuple, Union
from utils.logger import get_logger

logger = get_logger()

class RateLimiter:
    """Platformlara göre istek hızını sınırlayan sınıf."""
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # platform: (min_delay, max_delay) or exact_delay
        self.delays: Dict[str, Union[float, Tuple[float, float]]] = {
            "youtube": 0.5,
            "tiktok": (3.0, 5.0),
            "instagram": (5.0, 8.0),
            "google": (10.0, 30.0)
        }
    
    def _get_delay(self, platform: str) -> float:
        """İlgili platform için bekleme süresini hesaplar."""
        delay_cfg = self.delays.get(platform.lower(), 1.0)
        if isinstance(delay_cfg, tuple):
            return random.uniform(delay_cfg[0], delay_cfg[1])
        return float(delay_cfg)
        
    def wait(self, platform: str) -> None:
        """Belirtilen platform için uygun süre kadar bekler."""
        with self._lock:
            delay = self._get_delay(platform)
            logger.ilerleme(f"[{platform.capitalize()}] İstek sınırı için bekleniyor: {delay:.2f} saniye...")
            time.sleep(delay)
            
    def exponential_backoff(self, platform: str, retry_count: int) -> None:
        """Hata durumunda katlanarak artan bekleme süresi uygular."""
        max_retries = 5
        if retry_count > max_retries:
            retry_count = max_retries
            
        base_delay = self._get_delay(platform)
        # starts at base_delay, doubles each retry
        delay = base_delay * (2 ** max(0, retry_count - 1))
        
        with self._lock:
            logger.uyari(f"[{platform.capitalize()}] Hata tespit edildi. Katlanarak bekleme devrede: {delay:.2f} saniye (Deneme: {retry_count}/{max_retries})...")
            time.sleep(delay)
