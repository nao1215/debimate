from .kaggle import KaggleDataset

DATASETS = [
    KaggleDataset(
        name="credit-card-fraud",
        dataset_id="mlg-ulb/creditcardfraud",
        output_dir="datasets/credit-card-fraud/kaggle/raw",
    ),
]
