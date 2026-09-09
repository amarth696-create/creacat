import os
import subprocess
import logging
import shutil

class VideoDownloader:
    """
    Video içeriklerini veya seslerini indiren araç.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, url: str, output_dir: str) -> str | None:
        """
        yt-dlp kullanarak sadece sesi indirir ve mp3 olarak kaydeder.
        """
        self.logger.info(f"Ses indiriliyor: {url}")
        os.makedirs(output_dir, exist_ok=True)
        
        output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        command = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", output_template,
            url
        ]
        
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            for file in os.listdir(output_dir):
                if file.endswith(".mp3"):
                    return os.path.join(output_dir, file)
            return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"İndirme hatası (yt-dlp): {e}")
            return None

    def cleanup(self, output_dir: str):
        """
        Geçici dosyaları temizler.
        """
        self.logger.info(f"Geçici dizin temizleniyor: {output_dir}")
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except Exception as e:
                self.logger.error(f"Temizleme hatası: {e}")
