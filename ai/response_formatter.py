from typing import List, Any

def format_search_results(creators: List[Any], keyword: str, hashtags: List[str] = None, related_keywords: List[str] = None) -> str:
    """Arama sonuçlarını özetleyen ve doğrudan tam sayfa liste görünümüne yönlendiren temiz Türkçe metin oluşturur."""
    if not creators:
        return f"🔍 **'{keyword}'** konusu için kriterlere uygun içerik üreticisi bulunamadı. Lütfen filtreleri genişleterek tekrar deneyin."
    
    info_blocks = []
    if related_keywords:
        info_blocks.append(f"💡 **Otomatik Türetilen İlgili Arama Kelimeleri:** {', '.join([f'`{k}`' for k in related_keywords[:6]])}")
    if hashtags:
        info_blocks.append(f"🏷️ **Taranan Hashtag & Nişler:** {' '.join([f'`{t}`' for t in hashtags[:8]])}")
        
    header_extra = "\n\n".join(info_blocks) + "\n\n" if info_blocks else ""
    
    return (
        f"🎯 **'{keyword.title()}'** konusu için kriterlere uygun **{len(creators)} içerik üreticisi** bulundu ve performansları analiz edildi.\n\n"
        f"{header_extra}"
        f"👉 **<Listen burada: [Tam Ekran Liste Sayfasını Aç](?view=list)>**\n\n"
        f"*Detaylı metrik tablosu, etkileşim/izlenme oranları ve Excel indirme seçenekleri liste sayfasında sunulmaktadır.*"
    )


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
