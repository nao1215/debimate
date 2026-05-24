from abc import ABC, abstractmethod
from pathlib import Path


class DatasetDownloader(ABC):
    name: str

    @abstractmethod
    def download(self, root_dir: Path) -> None:
        pass
