from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from searchers.base import BaseSearcher
from models.creator import Creator

class YouTubeSearcher(BaseSearcher):
    """
    YouTube Data API v3 kullanarak influencer arama işlemi yapar.
    """
    
    def __init__(self, api_key: Any = None):
        super().__init__()
        if hasattr(api_key, 'YOUTUBE_API_KEY'):
            self.api_key = api_key.YOUTUBE_API_KEY
        else:
            self.api_key = str(api_key or "")
        
        self.quota_used = 0
        self.youtube = None
        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                self.logger.error(f"YouTube servisi başlatılamadı: {e}")
        
    @property
    def platform_name(self) -> str:
        return "YouTube"

    def search(self, query: str, limit: int = 50) -> List[Creator]:
        """ara metodu için alias."""
        return self.ara(query, {"limit": limit})
        
    def ara(self, keyword: str, filters: Dict[str, Any] = None) -> List[Creator]:
        """
        YouTube'da belirtilen anahtar kelime ile kanal araması yapar.
        """
        if filters is None:
            filters = {}
        creators = []
        if not self.youtube:
            self.logger.warning("YouTube API anahtarı ayarlanmamış. YouTube araması atlanıyor.")
            return creators
        try:
            self.logger.info(f"YouTube üzerinde '{keyword}' için arama başlatılıyor...")
            self.rate_limiter.wait()
            
            # Adım a: Hem kanal araması hem de video araması yaparak içerik üreten kanalları topla
            channel_ids_set = set()
            
            # 1. Doğrudan kanal araması
            try:
                ch_resp = self.youtube.search().list(
                    q=keyword,
                    type='channel',
                    part='id',
                    maxResults=25
                ).execute()
                self.quota_used += 100
                for item in ch_resp.get('items', []):
                    cid = item.get('id', {}).get('channelId')
                    if cid:
                        channel_ids_set.add(cid)
            except Exception as e:
                self.logger.warning(f"YouTube kanal arama hatası: {e}")

            # 2. Bu konuda video üreten aktif kanal sahiplerini topla
            try:
                self.rate_limiter.wait()
                vid_resp = self.youtube.search().list(
                    q=keyword,
                    type='video',
                    part='snippet',
                    maxResults=35
                ).execute()
                self.quota_used += 100
                for item in vid_resp.get('items', []):
                    cid = item.get('snippet', {}).get('channelId')
                    if cid:
                        channel_ids_set.add(cid)
            except Exception as e:
                self.logger.warning(f"YouTube video arama hatası: {e}")
                
            # 3. İlgili genişletilmiş sorgularla (ör: study with me, öğrenci vlog) ek kanalları topla
            try:
                from processors.expander import KeywordExpander
                expanded = KeywordExpander.expand(keyword)
                queries = expanded.get("queries", [])
                for q in queries[:2]:
                    if len(channel_ids_set) >= 35:
                        break
                    try:
                        self.rate_limiter.wait()
                        q_resp = self.youtube.search().list(
                            q=q,
                            type='video',
                            part='snippet',
                            maxResults=20
                        ).execute()
                        self.quota_used += 100
                        for item in q_resp.get('items', []):
                            cid = item.get('snippet', {}).get('channelId')
                            if cid:
                                channel_ids_set.add(cid)
                    except Exception:
                        pass
            except Exception:
                pass
                        
            channel_ids = list(channel_ids_set)[:50]
            if not channel_ids:
                self.logger.warning(f"'{keyword}' için YouTube'da kanal bulunamadı.")
                return creators

                
            # Adım b: channels.list
            self.rate_limiter.wait()
            channels_response = self.youtube.channels().list(
                id=','.join(channel_ids),
                part='snippet,statistics,brandingSettings'
            ).execute()
            self.quota_used += 1
            
            channels = channels_response.get('items', [])
            
            # Adım c: Abonelik sayısına göre en iyi 5 kanalı seç (veya tümünü işleyip sonra sırala, prompt "For top 5 channels by subscriber count" diyor. Her kanal için en iyi videoları alacağız)
            # Tüm kanalları filtrele ve oluştur
            for channel in channels:
                channel_id = channel['id']
                snippet = channel.get('snippet', {})
                stats = channel.get('statistics', {})
                
                subscribers = int(stats.get('subscriberCount', 0))
                
                creator = Creator(
                    username=snippet.get('title', ''),
                    platform='YouTube',
                    followers=subscribers,
                    profile_url=f"https://www.youtube.com/channel/{channel_id}",
                    bio=snippet.get('description', ''),
                    country=snippet.get('country', ''),
                    language=snippet.get('defaultLanguage', '')
                )
                creators.append(creator)
                
            # Ön filtreleme uygulayalım
            creators = self._apply_basic_filters(creators, filters)
            
            # Top 5 kanal için detaylı video istatistikleri
            creators.sort(key=lambda c: c.followers, reverse=True)
            top_5_creators = creators[:5]
            
            for creator in top_5_creators:
                channel_id = creator.profile_url.split('/')[-1]
                
                self.rate_limiter.wait()
                video_search_response = self.youtube.search().list(
                    channelId=channel_id,
                    type='video',
                    part='id',
                    maxResults=5,
                    order='viewCount'
                ).execute()
                self.quota_used += 100
                
                video_ids = [item['id']['videoId'] for item in video_search_response.get('items', [])]
                
                if video_ids:
                    self.rate_limiter.wait()
                    videos_response = self.youtube.videos().list(
                        id=','.join(video_ids),
                        part='statistics,snippet'
                    ).execute()
                    self.quota_used += 1
                    
                    videos = videos_response.get('items', [])
                    total_likes = 0
                    total_comments = 0
                    
                    for video in videos:
                        v_stats = video.get('statistics', {})
                        total_likes += int(v_stats.get('likeCount', 0))
                        total_comments += int(v_stats.get('commentCount', 0))
                        
                    avg_likes = total_likes / len(videos) if videos else 0
                    avg_comments = total_comments / len(videos) if videos else 0
                    
                    if creator.followers > 0:
                        creator.engagement_rate = ((avg_likes + avg_comments) / creator.followers) * 100
                    else:
                        creator.engagement_rate = 0.0
                        
            self.logger.info(f"YouTube araması tamamlandı. Kullanılan kota: {self.quota_used}")
            return top_5_creators + creators[5:]
            
        except HttpError as e:
            self.logger.error(f"YouTube API Hatası oluştu: {str(e)}")
            return creators
        except Exception as e:
            self.logger.error(f"YouTube aramasında beklenmeyen bir hata oluştu: {str(e)}")
            return creators
