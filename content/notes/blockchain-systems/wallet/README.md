# Wallet note assets

The article is `index.md`. Only images referenced by the article are included.

## Original diagrams

From the repository root:

```sh
python3 content/notes/blockchain-systems/wallet/figures.py
```

This uses the Python standard library and regenerates `gui-input.svg`,
`cli-input.svg`, and `local-transfer.svg`. The last diagram reads the captured
balances in `lab/output/`; it does not connect to a blockchain.
Other diagrams are Mermaid code embedded in `index.md`.

## Quoted screenshots

Install Pillow in a virtual environment. Download the originals into a separate
directory, using the filenames and source URLs documented in `screenshots.py`,
then run:

```sh
python3 content/notes/blockchain-systems/wallet/screenshots.py /path/to/originals
```

The script preserves UI pixels, trims only specified exterior margins, and
writes lossless WebP files. Some sources are screenshots within official guides;
the relevant guides and download filenames are documented next to each conversion.
For Gods Unchained, decode the source AVIF with ImageMagick as described in the
script before conversion. Sources can change: verify crop coordinates and the
Safe animation frame against the downloaded originals before regenerating.

## Local transfer evidence

`lab/README.txt` describes the isolated transfer experiment and its prerequisites.
The scripts, pinned tool configuration, and captured outputs are included so the
article's numbers and diagram can be checked without public RPCs or real funds.
