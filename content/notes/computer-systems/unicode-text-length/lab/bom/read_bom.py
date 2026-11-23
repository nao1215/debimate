import csv, io

data = b"\xef\xbb\xbfid,name\n1,alice\n"  # 先頭に UTF-8 の BOM
for enc in ["utf-8", "utf-8-sig"]:
    row = next(csv.DictReader(io.StringIO(data.decode(enc))))
    print(f"{enc:9} keys={list(row)}  row.get('id')={row.get('id')!r}")
