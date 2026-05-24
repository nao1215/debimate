from pathlib import Path
from datasets.registry import DATASETS


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    for dataset in DATASETS:
        print(f"Downloading dataset: {dataset.name}")
        dataset.download(root)

    print("All datasets downloaded.")


if __name__ == "__main__":
    main()
