"""
Çoklu Sohbet (Multi-Session Chat) ve Mesaj Depolama Yöneticisi.
SQLite tabanlıdır; kullanıcıların sohbetlerini, mesaj geçmişini ve bulunan influencer sonuçlarını kalıcı olarak saklar.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import Config
from models.creator import Creator

class ChatStorage:
    """Kullanıcıya özel sohbetleri ve mesaj geçmişini veritabanında yönetir."""

    @classmethod
    def get_db_connection(cls) -> sqlite3.Connection:
        db_file = Path(Config.DB_PATH)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_file), check_same_thread=False)
        cls._init_db(conn)
        return conn

    @classmethod
    def _init_db(cls, conn: sqlite3.Connection) -> None:
        """Gerekli tabloları oluşturur."""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                results_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

    @classmethod
    def create_conversation(cls, user_email: str, title: str = "Yeni Sohbet") -> str:
        """Yeni bir sohbet oturumu açar ve conversation_id döner."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        conv_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO chat_conversations (id, user_email, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (conv_id, user_email.strip().lower(), title, now_str, now_str))
        
        conn.commit()
        conn.close()
        return conv_id

    @classmethod
    def update_conversation_title(cls, conversation_id: str, new_title: str) -> None:
        """Sohbet başlığını günceller."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE chat_conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
        """, (new_title[:60], datetime.now().isoformat(), conversation_id))
        conn.commit()
        conn.close()

    @classmethod
    def get_user_conversations(cls, user_email: str) -> List[Dict[str, Any]]:
        """Kullanıcının tüm sohbetlerini en yeniden eskiye sıralı döner."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM chat_conversations
            WHERE user_email = ?
            ORDER BY updated_at DESC
        """, (user_email.strip().lower(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "title": r[1],
                "created_at": r[2],
                "updated_at": r[3]
            }
            for r in rows
        ]

    @classmethod
    def add_message(cls, conversation_id: str, role: str, content: str, results: Optional[List[Any]] = None) -> None:
        """Sohbete yeni bir mesaj (ve varsa bulunan influencer sonuçlarını) ekler."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        msg_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        
        results_json = None
        if results:
            serializable = []
            for r in results:
                if hasattr(r, "to_dict"):
                    serializable.append(r.to_dict())
                elif isinstance(r, dict):
                    serializable.append(r)
            results_json = json.dumps(serializable, ensure_ascii=False)
            
        cursor.execute("""
            INSERT INTO chat_messages (id, conversation_id, role, content, results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, conversation_id, role, content, results_json, now_str))
        
        # Sohbetin updated_at tarihini güncelle
        cursor.execute("""
            UPDATE chat_conversations
            SET updated_at = ?
            WHERE id = ?
        """, (now_str, conversation_id))
        
        conn.commit()
        conn.close()

    @classmethod
    def get_messages(cls, conversation_id: str) -> List[Dict[str, Any]]:
        """Belirtilen sohbetin tüm mesaj geçmişini kronolojik sırada döner."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, results_json, created_at
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conversation_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for r in rows:
            role, content, results_json, created_at = r
            msg_obj = {
                "role": role,
                "content": content,
                "created_at": created_at
            }
            if results_json:
                try:
                    raw_list = json.loads(results_json)
                    creators = [Creator.from_dict(c) for c in raw_list]
                    msg_obj["results"] = creators
                except Exception:
                    msg_obj["results"] = []
            messages.append(msg_obj)
            
        return messages

    @classmethod
    def delete_conversation(cls, conversation_id: str) -> None:
        """Bir sohbeti ve içindeki tüm mesajları siler."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM chat_conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()
