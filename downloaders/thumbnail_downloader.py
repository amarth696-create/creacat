import os
import requests
import logging
from urllib.parse import urlparse

class ThumbnailDownloader:
    """
    Küçük resimleri (thumbnail) indiren araç.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, url: str, output_dir: str) -> str | None:
        """
        URL'den küçük resmi indirir ve kaydeder.
        """
        self.logger.info(f"Küçük resim indiriliyor: {url}")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or not (filename.endswith(".jpg") or filename.endswith(".png")):
                filename = "thumbnail.jpg"
                
            output_path = os.path.join(output_dir, filename)
            
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return output_path
        except Exception as e:
            self.logger.error(f"Küçük resim indirme hatası: {e}")
            return None
