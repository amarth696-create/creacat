from typing import Dict, Any, Tuple

def extract_search_params(gemini_response: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini yanıtından arama parametrelerini çıkarır."""
    params = gemini_response.get("params") or {}
    return {
        "keyword": params.get("keyword", ""),
        "platforms": params.get("platforms", []),
        "min_followers": params.get("min_followers", 0)
    }

def validate_params(params: Dict[str, Any]) -> Tuple[bool, str]:
    """Çıkarılan parametreleri doğrular."""
    if not params.get("keyword"):
        return False, "Arama kelimesi bulunamadı."
    return True, ""
