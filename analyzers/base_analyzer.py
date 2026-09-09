from abc import ABC, abstractmethod
import logging

from models.creator import Creator

class BaseAnalyzer(ABC):
    """
    Analizörler için temel soyut sınıf.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def analyze(self, creator: Creator, keyword: str) -> Creator:
        """
        İçerik analizi gerçekleştirir ve güncellenmiş Creator nesnesini döndürür.
        """
        pass

    @property
    @abstractmethod
    def level(self) -> int:
        """
        Analizörün derinlik seviyesini döndürür (1, 2 veya 3).
        """
        pass
