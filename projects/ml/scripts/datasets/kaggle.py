import shutil
import subprocess
from pathlib import Path
from .base import DatasetDownloader


class KaggleDataset(DatasetDownloader):
    def __init__(self, name: str, dataset_id: str, output_dir: str):
        self.name = name
        self.dataset_id = dataset_id
        self.output_dir = output_dir

    def download(self, root_dir: Path) -> None:
        if shutil.which("kaggle") is None:
            raise RuntimeError(
                "kaggle CLI not found.\nRun `uv sync` and ensure kaggle is installed."
            )

        out = root_dir / self.output_dir
        out.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["kaggle", "datasets", "download", "-d", self.dataset_id, "-p", str(out)],
            check=True,
        )

        zip_files = list(out.glob("*.zip"))
        if not zip_files:
            raise RuntimeError("No zip file found after kaggle download.")

        for zip_path in zip_files:
            subprocess.run(
                ["unzip", "-o", zip_path.name, "-d", str(out)],
                cwd=out,
                check=True,
            )
            zip_path.unlink()
