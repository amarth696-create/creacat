from typing import List, Any

def format_search_results(creators: List[Any], keyword: str) -> str:
    """Arama sonuçlarını özetleyen Türkçe metin oluşturur."""
    if not creators:
        return f"'{keyword}' için sonuç bulunamadı."
    return f"'{keyword}' araması için {len(creators)} sonuç bulundu."

def format_creator_detail(creator: Any) -> str:
    """İçerik üreticinin detaylarını Türkçe özetler."""
    plat = getattr(creator, "platform", "")
    if hasattr(plat, "value"):
        plat = plat.value
    return f"{creator.username} adlı yayıncı {str(plat).capitalize()} platformunda içerik üretiyor."

def format_comparison(creators: List[Any]) -> str:
    """Üreticilerin karşılaştırmasını döner."""
    names = ", ".join(c.username for c in creators)
    return f"Seçilen yayıncılar karşılaştırılıyor: {names}"

def format_error(error_type: str, details: str) -> str:
    """Hata mesajlarını formatlar."""
    return f"Hata ({error_type}): {details}. Lütfen tekrar deneyin."
