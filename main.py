"""
Main CLI entry point for the Influencer Discovery System.
"""
import argparse
import sys
from typing import List

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

from config import Config
from searchers.youtube_searcher import YouTubeSearcher
from searchers.tiktok_searcher import TikTokSearcher
from searchers.instagram_searcher import InstagramSearcher
from searchers.google_enricher import GoogleEnricher
from processors.normalizer import Normalizer
from processors.scorer import Scorer
from processors.deduplicator import Deduplicator
from processors.filterer import Filterer
from analyzers.analysis_orchestrator import AnalysisOrchestrator
from exporters.excel_exporter import ExcelExporter
from exporters.json_exporter import JsonExporter
from utils.logger import get_logger

logger = get_logger(__name__)
console = Console()

def parse_args() -> argparse.Namespace:
    """Argümanları ayrıştırır (Parses arguments)."""
    parser = argparse.ArgumentParser(
        description="Etkileyici (Influencer) Keşif Sistemi",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--konu", type=str, required=True, help="Aranacak anahtar kelime veya konu")
    parser.add_argument("--platformlar", type=str, default="youtube,tiktok,instagram", help="Aranacak platformlar (virgülle ayrılmış)")
    parser.add_argument("--derinlik", type=int, default=1, choices=[1, 2, 3], help="Analiz derinliği (1: Temel, 2: Gelişmiş, 3: LLM Destekli)")
    parser.add_argument("--min-takipci", type=int, default=1000, help="Minimum takipçi sayısı filtresi")
    parser.add_argument("--ulke", type=str, default=None, help="Ülke kodu filtresi (ör. TR, ABD)")
    parser.add_argument("--dil", type=str, default=None, help="Dil kodu filtresi (ör. tr, en)")
    parser.add_argument("--limit", type=int, default=50, help="Maksimum sonuç sayısı")
    parser.add_argument("--cikti", type=str, default="excel,json", help="Çıktı formatları (virgülle ayrılmış)")
    parser.add_argument("--llm", type=str, default="gemini", choices=["gemini", "ollama"], help="Derinlik 3 için LLM sağlayıcısı")
    parser.add_argument("--ollama-model", type=str, default="llama3.1:8b", help="Ollama model adı")
    
    return parser.parse_args()

def show_banner(args: argparse.Namespace, config: Config) -> None:
    """Hoşgeldin mesajını ve ayar özetini gösterir."""
    banner_text = (
        f"[bold blue]Etkileyici (Influencer) Keşif Sistemi[/bold blue]\n\n"
        f"[green]Konu:[/green] {args.konu}\n"
        f"[green]Platformlar:[/green] {args.platformlar}\n"
        f"[green]Analiz Derinliği:[/green] {args.derinlik}\n"
        f"[green]Min Takipçi:[/green] {args.min_takipci}\n"
        f"[green]Hedef Limit:[/green] {args.limit}\n"
    )
    if args.derinlik == 3:
        banner_text += f"[green]LLM Sağlayıcı:[/green] {args.llm}"
        if args.llm == "ollama":
            banner_text += f" ({args.ollama_model})"
        banner_text += "\n"
        
    console.print(Panel(banner_text, title="🚀 Sistem Başlatılıyor", expand=False))

def main() -> None:
    args = parse_args()
    config = Config()
    
    show_banner(args, config)
    
    platforms = [p.strip().lower() for p in args.platformlar.split(",")]
    output_formats = [f.strip().lower() for f in args.cikti.split(",")]
    
    # Araçları başlat (Initialize components)
    searchers = {}
    if "youtube" in platforms:
        searchers["youtube"] = YouTubeSearcher(config)
    if "tiktok" in platforms:
        searchers["tiktok"] = TikTokSearcher(config)
    if "instagram" in platforms:
        searchers["instagram"] = InstagramSearcher(config)
        
    google_enricher = GoogleEnricher(config)
    normalizer = Normalizer()
    analysis_orchestrator = AnalysisOrchestrator(
        config=config,
        depth=args.derinlik,
        llm_provider=args.llm,
        ollama_model=args.ollama_model
    )
    scorer = Scorer()
    deduplicator = Deduplicator()
    filterer = Filterer(min_followers=args.min_takipci, country=args.ulke, language=args.dil)
    
    raw_results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        # Arama (Searching)
        search_task = progress.add_task("[cyan]Platformlarda aranıyor...", total=len(searchers))
        
        for platform_name, searcher in searchers.items():
            progress.update(search_task, description=f"[cyan]{platform_name.capitalize()} üzerinde aranıyor...")
            try:
                platform_results = searcher.search(query=args.konu, limit=args.limit)
                raw_results.extend(platform_results)
                logger.info(f"{platform_name.capitalize()} platformundan {len(platform_results)} sonuç bulundu.")
            except Exception as e:
                logger.error(f"{platform_name.capitalize()} araması sırasında hata oluştu: {str(e)}")
                console.print(f"\n[bold red]Hata ({platform_name}):[/bold red] Aramaya devam ediliyor...")
            progress.advance(search_task)
            
        progress.update(search_task, description="[green]Arama tamamlandı.")
        
        if not raw_results:
            console.print("\n[bold yellow]Uyarı:[/bold yellow] Hiç sonuç bulunamadı. Program sonlandırılıyor.")
            sys.exit(0)
            
        # Standartlaştırma (Normalization)
        norm_task = progress.add_task("[magenta]Sonuçlar standartlaştırılıyor...", total=1)
        normalized_creators = normalizer.normalize(raw_results)
        progress.advance(norm_task)
        
        # Zenginleştirme (Enrichment)
        enrich_task = progress.add_task("[yellow]Google zenginleştirmesi yapılıyor...", total=len(normalized_creators))
        enriched_creators = []
        for creator in normalized_creators:
            try:
                enriched = google_enricher.enrich(creator)
                enriched_creators.append(enriched)
            except Exception as e:
                logger.error(f"Zenginleştirme hatası ({creator.username}): {str(e)}")
                enriched_creators.append(creator)
            progress.advance(enrich_task)
            
        # Tekrarları temizleme (Deduplication)
        dedup_task = progress.add_task("[blue]Tekrarlar temizleniyor...", total=1)
        unique_creators = deduplicator.deduplicate(enriched_creators)
        progress.advance(dedup_task)
        
        # Filtreleme (Filtering)
        filter_task = progress.add_task("[red]Filtreler uygulanıyor...", total=1)
        filtered_creators = filterer.filter(unique_creators)
        progress.advance(filter_task)
        
        # Analiz (Analysis)
        analysis_task = progress.add_task("[cyan]Profil analizi yapılıyor...", total=len(filtered_creators))
        analyzed_creators = []
        for creator in filtered_creators:
            try:
                analyzed = analysis_orchestrator.analyze(creator, keyword=args.konu)
                analyzed_creators.append(analyzed)
            except Exception as e:
                logger.error(f"Analiz hatası ({creator.username}): {str(e)}")
                analyzed_creators.append(creator)
            progress.advance(analysis_task)
            
        # Puanlama (Scoring)
        score_task = progress.add_task("[green]Puanlama yapılıyor...", total=1)
        scored_creators = scorer.score(analyzed_creators, keyword=args.konu)
        progress.advance(score_task)
        
    # Sınıflandırma ve limitleme (Sorting and limiting)
    sorted_creators = sorted(scored_creators, key=lambda c: getattr(c, "final_score", 0.0) or 0.0, reverse=True)
    final_creators = sorted_creators[:args.limit]
    
    # Sonuçları tabloda gösterme (Display table)
    console.print("\n[bold]En İyi Sonuçlar (İlk 10)[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("İçerik Üretici")
    table.add_column("Platform")
    table.add_column("Takipçi", justify="right")
    table.add_column("Etkileşim (%)", justify="right")
    table.add_column("Skor", justify="right")
    if args.derinlik >= 3:
        table.add_column("LLM Özet")
        
    for i, creator in enumerate(final_creators[:10], 1):
        followers = f"{creator.followers:,}" if creator.followers else "Bilinmiyor"
        engagement = f"{creator.engagement_rate:.2f}%" if creator.engagement_rate else "Bilinmiyor"
        score = f"{getattr(creator, 'final_score', 0.0):.2f}"
        
        row = [str(i), creator.username, str(creator.platform).capitalize(), followers, engagement, score]
        
        if args.derinlik >= 3:
            summary = "Özet yok"
            if creator.content_analysis and creator.content_analysis.llm_ozet:
                summary = creator.content_analysis.llm_ozet
            if len(summary) > 50:
                summary = summary[:47] + "..."
            row.append(summary)
            
        table.add_row(*row)
        
    console.print(table)
    
    # Dışa aktarma (Exporting)
    export_prefix = f"sonuclar_{args.konu.replace(' ', '_')}"
    if "excel" in output_formats:
        excel_exporter = ExcelExporter()
        try:
            excel_path = excel_exporter.export(final_creators, f"{export_prefix}.xlsx")
            console.print(f"[green]Excel dosyası oluşturuldu:[/green] {excel_path}")
        except Exception as e:
            logger.error(f"Excel dışa aktarım hatası: {str(e)}")
            console.print("[bold red]Excel oluşturulurken hata oluştu.[/bold red]")
            
    if "json" in output_formats:
        json_exporter = JsonExporter()
        try:
            json_path = json_exporter.export(final_creators, f"{export_prefix}.json")
            console.print(f"[green]JSON dosyası oluşturuldu:[/green] {json_path}")
        except Exception as e:
            logger.error(f"JSON dışa aktarım hatası: {str(e)}")
            console.print("[bold red]JSON oluşturulurken hata oluştu.[/bold red]")
            
    # Özet (Summary)
    console.print(f"\n[bold green]İşlem Tamamlandı![/bold green] Toplam {len(final_creators)} içerik üretici analiz edildi ve kaydedildi.")

if __name__ == "__main__":
    main()
