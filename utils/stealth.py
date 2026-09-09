import random
import time
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_random_user_agent() -> str:
    """Gerçekçi ve rastgele bir tarayıcı kimliği (user agent) döndürür."""
    return random.choice(USER_AGENTS)

def get_random_delay(min_sec: float, max_sec: float) -> float:
    """Belirtilen aralıkta rastgele bir gecikme süresi döndürür."""
    return random.uniform(min_sec, max_sec)

def configure_stealth_browser(page: Any) -> None:
    """Playwright sayfasına görünmezlik (stealth) ayarlarını uygular."""
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
        logger.bilgi("Görünmezlik (stealth) ayarları tarayıcıya uygulandı.")
    except ImportError:
        logger.uyari("playwright-stealth kütüphanesi bulunamadı, varsayılan ayarlarla devam ediliyor.")
    except Exception as e:
        logger.hata(f"Stealth ayarları uygulanırken hata oluştu: {str(e)}")

async def apply_stealth_async(page: Any) -> None:
    """Playwright async sayfasına görünmezlik (stealth) ayarlarını uygular."""
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
        logger.bilgi("Görünmezlik (stealth) async ayarları tarayıcıya uygulandı.")
    except ImportError:
        logger.uyari("playwright-stealth kütüphanesi bulunamadı, varsayılan ayarlarla devam ediliyor.")
    except Exception as e:
        logger.hata(f"Stealth async ayarları uygulanırken hata oluştu: {str(e)}")

def get_stealth_headers() -> Dict[str, str]:
    """Gerçekçi HTTP başlıkları (headers) döndürür."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": get_random_user_agent()
    }

def random_scroll(page: Any) -> None:
    """Playwright sayfasında gerçekçi bir şekilde aşağı/yukarı kaydırma yapar."""
    logger.ilerleme("Sayfa üzerinde rastgele kaydırma yapılıyor...")
    scrolls = random.randint(2, 5)
    for _ in range(scrolls):
        scroll_amount = random.randint(300, 800)
        direction = random.choice([1, 1, 1, -1])  # Çoğunlukla aşağı yönde
        
        try:
            page.mouse.wheel(0, scroll_amount * direction)
            time.sleep(get_random_delay(0.5, 2.0))
        except Exception as e:
            logger.hata(f"Kaydırma sırasında hata oluştu: {str(e)}")
            break
