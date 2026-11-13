"""Start is_on() in two fresh Python processes and count users whose answer differs.

Run: FLAG_RULE=builtin python check.py ; FLAG_RULE=crc32 python check.py
"""

import subprocess
import sys

CODE = "from app import is_on; print(''.join('1' if is_on(f'u-{i:05d}') else '0' for i in range(3000)))"
a, b = (subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, check=True).stdout
        for _ in range(2))
print(sum(x != y for x, y in zip(a, b)), "of 3000 users differ")
