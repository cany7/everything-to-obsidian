#!/usr/bin/env python3
"""扫描 CSV 链接列表，取第一条未处理行，输出 LINE= 和 CONTENT=。

用法：python pick-next-url.py <csv_path>
CSV 格式：三列（序号,处理情况,链接），第一行表头。
"""
import csv
import sys

if len(sys.argv) < 2:
    print("ERROR: 请指定 CSV 文件路径", file=sys.stderr)
    print("用法：python pick-next-url.py <csv_path>", file=sys.stderr)
    sys.exit(1)

csv_path = sys.argv[1]

with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i == 0:
            continue
        if len(row) < 3:
            continue
        num, status, content = row[0].strip(), row[1].strip(), row[2].strip()
        if status:
            continue
        if not content:
            continue
        try:
            int(num)
        except ValueError:
            continue
        print(f"LINE={num}")
        print(f"CONTENT={content}")
        break
