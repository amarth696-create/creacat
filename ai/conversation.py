from typing import List, Dict, Any
import json

class ConversationManager:
    """Sohbet geçmişini yönetir."""
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        
    def add_message(self, role: str, content: str) -> None:
        """Yeni bir mesaj ekler."""
        self.history.append({"role": role, "content": content})
        
    def get_history(self) -> List[Dict[str, Any]]:
        """Tüm sohbet geçmişini döner."""
        return self.history
        
    def get_context(self) -> Dict[str, Any]:
        """Mevcut bağlamı döner."""
        return {
            "message_count": len(self.history)
        }
        
    def clear(self) -> None:
        """Geçmişi temizler."""
        self.history = []
        
    def export_conversation(self) -> str:
        """Geçmişi JSON olarak dışa aktarır."""
        return json.dumps(self.history, ensure_ascii=False)
