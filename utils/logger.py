from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

class AppLogger:
    """Uygulama genelinde kullanılacak loglama sınıfı."""
    def __init__(self) -> None:
        self.console = Console()
    def _safe_print(self, styled: str, plain: str) -> None:
        try:
            self.console.print(styled)
        except Exception:
            try:
                import sys
                clean_plain = plain.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
                print(clean_plain)
            except Exception:
                pass

    def bilgi(self, message: str) -> None:
        """Bilgi mesajı kaydeder (Info)."""
        self._safe_print(f"[cyan]ℹ️ {message}[/cyan]", f"[INFO] {message}")

    def info(self, message: str) -> None:
        self.bilgi(message)

    def debug(self, message: str) -> None:
        self._safe_print(f"[dim]🔍 {message}[/dim]", f"[DEBUG] {message}")

    def uyari(self, message: str) -> None:
        """Uyarı mesajı kaydeder (Warning)."""
        self._safe_print(f"[yellow]⚠️ {message}[/yellow]", f"[WARNING] {message}")

    def warning(self, message: str) -> None:
        self.uyari(message)

    def hata(self, message: str) -> None:
        """Hata mesajı kaydeder (Error)."""
        self._safe_print(f"[red]❌ {message}[/red]", f"[ERROR] {message}")

    def error(self, message: str) -> None:
        self.hata(message)

    def basari(self, message: str) -> None:
        """Başarı mesajı kaydeder (Success)."""
        self._safe_print(f"[green]✅ {message}[/green]", f"[SUCCESS] {message}")

    def success(self, message: str) -> None:
        self.basari(message)
        
    def ilerleme(self, message: str) -> None:
        """İlerleme mesajı kaydeder (Progress)."""
        self._safe_print(f"[blue]⏳ {message}[/blue]", f"[PROGRESS] {message}")

_logger_instance = AppLogger()
Logger = AppLogger

def get_logger(name: str = "") -> AppLogger:
    """Uygulama loglayıcısını döndürür."""
    return _logger_instance

def setup_logger(name: str = "") -> AppLogger:
    """Uygulama loglayıcısını döndürür (setup_logger uyumluluğu için)."""
    return _logger_instance

def create_progress_bar() -> Progress:
    """Konsol için ilerleme çubuğu oluşturur."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=Console()
    )
