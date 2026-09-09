from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

class AppLogger:
    """Uygulama genelinde kullanılacak loglama sınıfı."""
    def __init__(self) -> None:
        self.console = Console()
    def bilgi(self, message: str) -> None:
        """Bilgi mesajı kaydeder (Info)."""
        self.console.print(f"[cyan]ℹ️ {message}[/cyan]")

    def info(self, message: str) -> None:
        self.bilgi(message)

    def debug(self, message: str) -> None:
        self.console.print(f"[dim]🔍 {message}[/dim]")

    def uyari(self, message: str) -> None:
        """Uyarı mesajı kaydeder (Warning)."""
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")

    def warning(self, message: str) -> None:
        self.uyari(message)

    def hata(self, message: str) -> None:
        """Hata mesajı kaydeder (Error)."""
        self.console.print(f"[red]❌ {message}[/red]")

    def error(self, message: str) -> None:
        self.hata(message)

    def basari(self, message: str) -> None:
        """Başarı mesajı kaydeder (Success)."""
        self.console.print(f"[green]✅ {message}[/green]")

    def success(self, message: str) -> None:
        self.basari(message)
        
    def ilerleme(self, message: str) -> None:
        """İlerleme mesajı kaydeder (Progress)."""
        self.console.print(f"[blue]⏳ {message}[/blue]")

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
