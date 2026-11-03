ECDSA message verification experiment
Python 3 and cryptography==46.0.5.
Create a virtual environment and install requirements.txt, for example:
  python3 -m venv /tmp/debimate-signature-venv
  /tmp/debimate-signature-venv/bin/pip install -r requirements.txt
  /tmp/debimate-signature-venv/bin/python verify_changes.py
From the repository root, use the full paths to requirements.txt and the script.
No network is used by the experiment itself. Keys are generated in memory and
never saved or printed; no cryptocurrency address or transaction is created.
output.txt is actual output; versions.txt records the library version.
