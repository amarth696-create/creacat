import json
import requests
from analyzers.base_analyzer import BaseAnalyzer
from models.creator import Creator

class LlmAnalyzer(BaseAnalyzer):
    """
    Seviye 3: Büyük Dil Modeli (LLM) ile derin analiz.
    """
    def __init__(self, provider='gemini', api_key=None, ollama_model='llama3.1:8b'):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.ollama_model = ollama_model

    @property
    def level(self) -> int:
        return 3

    def analyze(self, creator: Creator, keyword: str) -> Creator:
        self.logger.info(f"{creator.username} için LLM analizi başlatılıyor.")
        
        ca = creator.content_analysis
        if not ca:
            from models.analysis_result import ContentAnalysis
            ca = ContentAnalysis()
            creator.content_analysis = ca

        context = f"Bio: {creator.bio}\n"
        if getattr(ca, 'en_sik_hashtags', None):
            context += f"Hashtags: {', '.join(ca.en_sik_hashtags)}\n"
        if getattr(ca, 'whisper_transcripts', None):
            context += f"Transcripts: {' '.join(ca.whisper_transcripts)}\n"
        if getattr(ca, 'thumbnail_texts', None):
            context += f"OCR Texts: {' '.join(ca.thumbnail_texts)}\n"
        if getattr(ca, 'gorsel_konu', None):
            context += f"Visual Category: {ca.gorsel_konu}\n"

        prompt = (
            f"Sen bir içerik analiz uzmanısın. Aşağıdaki içerik üreticisi verilerini inceleyerek Türkçe bir değerlendirme yap.\n"
            f"Anahtar Kelime: {keyword}\n\n"
            f"İçerik Verileri:\n{context}\n\n"
            "Lütfen şu alanları içeren JSON formatında yanıt ver:\n"
            "{ \"ana_nis_alani\": \"str\", \"alt_konular\": [\"str\"], \"hedef_kitle\": \"str\", \"icerik_tarzi\": \"str\", \"sponsorlu_icerik_orani\": 0.0, \"keyword_ilgi_skoru\": 0, \"ozet\": \"str\" }"
        )

        try:
            result_text = ""
            if self.provider == 'gemini':
                import google.genai as genai
                client = genai.Client(api_key=self.api_key)
                for m in ['gemini-3.6-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
                    try:
                        response = client.models.generate_content(
                            model=m,
                            contents=prompt,
                        )
                        result_text = response.text
                        break
                    except Exception:
                        continue
                
            elif self.provider == 'ollama':
                url = "http://localhost:11434/api/generate"
                payload = {
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                res = requests.post(url, json=payload)
                res.raise_for_status()
                result_text = res.json().get('response', '{}')
            else:
                self.logger.error("Geçersiz LLM sağlayıcısı.")
                return creator

            result_text = result_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(result_text)
            
            ca.ana_nis_alani = data.get("ana_nis_alani", "")
            ca.alt_konular = data.get("alt_konular", [])
            ca.hedef_kitle = data.get("hedef_kitle", "")
            ca.icerik_tarzi = data.get("icerik_tarzi", "")
            sp_rate = float(data.get("sponsorlu_icerik_orani", 0.0))
            ca.sponsorlu_icerik_orani = sp_rate
            if sp_rate > 0:
                creator.has_sponsored_content = True
                creator.sponsored_video_count = max(creator.sponsored_video_count, int(sp_rate * 10))
                if not creator.sponsor_keywords_found:
                    creator.sponsor_keywords_found = ["Sponsorlu İçerik", "Marka İşbirliği"]
            ca.keyword_ilgi_skoru = int(data.get("keyword_ilgi_skoru", getattr(ca, 'keyword_skoru', 0) or 0))
            ca.ozet = data.get("ozet", "")
            
            self.logger.info(f"{creator.username} için LLM analizi başarıyla tamamlandı.")
        except Exception as e:
            self.logger.error(f"LLM analizi başarısız oldu: {e}")
            
        return creator
