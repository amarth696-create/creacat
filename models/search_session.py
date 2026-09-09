import sqlite3
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from .creator import Creator

@dataclass
class SearchSession:
    """Arama oturumunu temsil eden veri sınıfı."""
    keyword: str
    platforms: List[str]
    filters: Dict[str, Any]
    depth: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    results: List[Creator] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    chat_history: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Sınıfı sözlüğe dönüştürür."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['results'] = [creator.to_dict() for creator in self.results]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchSession':
        """Sözlükten sınıf oluşturur."""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
        if 'results' in data:
            data['results'] = [Creator.from_dict(c) for c in data['results']]
            
        return cls(**data)

    def save_to_db(self, db_path: str) -> None:
        """Oturumu SQLite veritabanına kaydeder."""
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tablo yoksa oluştur
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_sessions (
                id TEXT PRIMARY KEY,
                keyword TEXT,
                platforms TEXT,
                filters TEXT,
                depth INTEGER,
                results TEXT,
                created_at TEXT,
                chat_history TEXT
            )
        ''')
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_sessions 
            (id, keyword, platforms, filters, depth, results, created_at, chat_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.id,
            self.keyword,
            json.dumps(self.platforms),
            json.dumps(self.filters),
            self.depth,
            json.dumps([c.to_dict() for c in self.results]),
            self.created_at.isoformat(),
            json.dumps(self.chat_history)
        ))
        
        conn.commit()
        conn.close()

    @classmethod
    def load_from_db(cls, db_path: str, session_id: str) -> Optional['SearchSession']:
        """ID'ye göre oturumu veritabanından yükler."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM search_sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if not row:
                return None
                
            data = {
                'id': row[0],
                'keyword': row[1],
                'platforms': json.loads(row[2]),
                'filters': json.loads(row[3]),
                'depth': row[4],
                'results': [Creator.from_dict(c) for c in json.loads(row[5])],
                'created_at': datetime.fromisoformat(row[6]),
                'chat_history': json.loads(row[7])
            }
            return cls(**data)
        except Exception as e:
            print(f"Veritabanından yüklenirken hata oluştu: {e}")
            return None
