#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""byte_scanner.py —— 通用二进制模式扫描 / 字符串提取 / 字节直方图（只读）。

用途
----
对一个或多个二进制文件做无需反汇编的快速勘察：

  * **模式搜索**：``--hex "48 8D 15 ?? 00"``，``??`` 为单字节通配；
    也可用 ``--ascii "literal"`` 搜索字面 ASCII 串；
  * **范围限定**：``--range START:END``（十六进制或十进制）；
  * **命中控制**：``--count N`` 限制最大命中数，``--context N`` 打印命中
    前后的十六进制上下文；
  * **字符串提取**：``--strings MINLEN`` 列出文件中长度 >= MINLEN 的
    可打印 ASCII 串及其文件偏移；
  * **字节直方图**：``--byte-histogram`` 打印 256 桶频率表 + Shannon 熵
    （bits/byte），同样支持 ``--range`` 限定区间。

模式语法
--------
``--hex`` 接受以空格（或逗号）分隔的 token：

  * ``48``、``0x48`` —— 单字节匹配；
  * ``??``、``?``、``**`` —— 单字节通配（任意值）；
  * 也接受连续写法 ``488D15`` 与 ``48 8D 15`` 混用。

**通配字节不参与匹配**，但仍占位，因此模式长度恒定；报告的是模式
**起始**位置的文件偏移。

可复现性
--------
只要执行了搜索（模式或字符串），结尾必定打印一行 ``汇总:``，
包含命中总数——**零命中也显式输出**，例如 ``汇总: 命中数=0 ...``，
便于脚本断言与结果复述。

依赖
----
  * Python 3.11+（仅标准库，无第三方依赖）

退出码：0 成功，1 参数错误，2 文件不可读。

本工具**只读**：只读取被扫描的文件；唯一允许的写出是 ``--out`` 指定的
命中清单路径。
"""

from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from typing import Any, Iterable, Sequence

PRINTABLE_LO = 0x20
PRINTABLE_HI = 0x7F  # 不含 0x7F

# 跳过整片零字节的优化阈值：超过该长度的纯零区间不可能包含非通配模式起始
ZERO_RUN_SKIP_MIN = 4096

# --range 的开放上界哨兵：写作 "START:" 表示到文件末尾
RANGE_END_EOF = -1


# --------------------------------------------------------------------------
# 参数解析
# --------------------------------------------------------------------------


def parse_range(text: str) -> tuple[int, int]:
    """解析 START:END，两端接受 0x 前缀或十进制。

    END 可省略（写作 ``START:``），表示"从 START 到文件末尾"；此时以
    哨兵值 ``RANGE_END_EOF`` 占位，在读取文件后按实际长度收紧。
    """
    if ":" not in text:
        raise argparse.ArgumentTypeError("区间格式应为 START:END，例如 0x1000:0x2000")
    a, b = text.split(":", 1)
    try:
        start = int(a.strip(), 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析区间起点 {a!r}: {exc}") from exc
    if start < 0:
        raise argparse.ArgumentTypeError("区间起点不能为负")
    b = b.strip()
    if not b:
        # 开放上界：到文件末尾
        return start, RANGE_END_EOF
    try:
        end = int(b, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析区间终点 {b!r}: {exc}") from exc
    if end <= start:
        raise argparse.ArgumentTypeError("区间终点必须大于起点")
    return start, end


def resolve_range(rng: tuple[int, int] | None,
                  size: int) -> tuple[int, int] | None:
    """把可能含 RANGE_END_EOF 的区间按实际文件长度收紧。"""
    if rng is None:
        return None
    lo, hi = rng
    if hi == RANGE_END_EOF or hi > size:
        hi = size
    return lo, hi


def parse_int(text: str) -> int:
    try:
        return int(text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析整数 {text!r}") from exc


_HEX_TOKEN = re.compile(r"^(?:0x)?([0-9a-fA-F]{1,2})$")


def parse_hex_pattern(text: str) -> tuple[bytes, bytes]:
    """把 ``--hex`` 文本编译为 (掩码, 期望值)。

    mask 中 1 表示"该字节参与匹配"，0 表示通配。
    返回的两个 bytes 等长 = 模式长度。
    """
    raw = text.replace(",", " ").strip()
    if not raw:
        raise argparse.ArgumentTypeError("--hex 模式不能为空")

    tokens: list[str] = []
    if " " in raw or "," in text:
        tokens = [t for t in raw.split() if t]
    else:
        # 无分隔符：两两切分（允许 0x 前缀只在整体出现一次）
        body = raw
        if body.lower().startswith("0x"):
            body = body[2:]
        if len(body) % 2 != 0:
            raise argparse.ArgumentTypeError(
                f"--hex 连续写法需要偶数个十六进制字符，得到 {len(body)} 个: {text!r}")
        tokens = [body[i:i + 2] for i in range(0, len(body), 2)]

    mask = bytearray()
    value = bytearray()
    for tok in tokens:
        t = tok.strip()
        if t in ("?", "??", "*", "**"):
            mask.append(0)
            value.append(0)
            continue
        m = _HEX_TOKEN.match(t)
        if not m:
            raise argparse.ArgumentTypeError(
                f"无法解析模式 token {tok!r}；应为 1-2 位十六进制或 ?? 通配")
        mask.append(0xFF)
        value.append(int(m.group(1), 16))

    if not mask:
        raise argparse.ArgumentTypeError("--hex 模式解析后为空")
    return bytes(mask), bytes(value)


def printable_mask(pattern: bytes) -> bool:
    return all(PRINTABLE_LO <= b < PRINTABLE_HI for b in pattern)


# --------------------------------------------------------------------------
# 模式搜索
# --------------------------------------------------------------------------


def find_pattern(buf: bytes, mask: bytes, value: bytes, start: int, end: int,
                 limit: int | None) -> tuple[list[int], bool]:
    """在 ``buf[start:end)`` 中搜索模式。

    返回 (命中偏移列表, 是否因 limit 截断)。
    实现说明：匹配窗口逐字节滑动；``mask`` 中为 0 的位置一律视为命中，
    因此全通配模式会逐字节命中（这是刻意行为，便于观察范围）。
    """
    plen = len(mask)
    hits: list[int] = []
    truncated = False
    if plen == 0 or end - start < plen:
        return hits, False
    last = end - plen

    # 全通配模式：无需逐字节比较，直接按位置枚举
    if not any(mask):
        for p in range(start, last + 1):
            if limit is not None and len(hits) >= limit:
                truncated = True
                break
            hits.append(p)
        return hits, truncated

    # 取第一个非通配位置作为快查锚点，用 bytes.find 跳过低效比较
    anchors = [i for i, m in enumerate(mask) if m]
    reach = plen - 1 - anchors[-1]          # 锚点之后仍需覆盖的字节数
    off_lo, off_hi = anchors[0], anchors[-1]

    # 逐锚点尝试：取最左侧非通配字节做 find，命中后再全量校验
    anchor_off = off_lo
    anchor_byte = value[anchor_off]

    p = start
    while p <= last:
        if limit is not None and len(hits) >= limit:
            truncated = True
            break
        idx = buf.find(anchor_byte, p + anchor_off, end)
        if idx < 0:
            break
        cand = idx - anchor_off
        if cand < start:
            # 锚点出现太靠前，无法构成完整匹配；从下一个位置继续
            p = cand + 1
            continue
        if cand > last:
            break
        # 全量校验（含所有非通配字节）
        if all(buf[cand + i] == value[i]
               for i, m in enumerate(mask) if m):
            hits.append(cand)
            p = cand + 1
        else:
            p = cand + 1
    return hits, truncated


# --------------------------------------------------------------------------
# 字符串提取
# --------------------------------------------------------------------------


def extract_strings(buf: bytes, minlen: int, start: int, end: int,
                    limit: int | None) -> tuple[list[tuple[int, bytes]], bool]:
    """提取长度 >= minlen 的连续可打印 ASCII 串。"""
    out: list[tuple[int, bytes]] = []
    truncated = False
    seg_start = -1
    for i in range(start, end):
        b = buf[i]
        if PRINTABLE_LO <= b < PRINTABLE_HI:
            if seg_start < 0:
                seg_start = i
        else:
            if seg_start >= 0:
                if i - seg_start >= minlen:
                    out.append((seg_start, buf[seg_start:i]))
                    if limit is not None and len(out) >= limit:
                        truncated = True
                        return out, truncated
                seg_start = -1
    if seg_start >= 0 and end - seg_start >= minlen:
        out.append((seg_start, buf[seg_start:end]))
        if limit is not None and len(out) >= limit:
            truncated = True
    return out, truncated


# --------------------------------------------------------------------------
# 字节直方图与熵
# --------------------------------------------------------------------------


def byte_histogram(buf: bytes, start: int, end: int) -> list[int]:
    hist = [0] * 256
    for b in buf[start:end]:
        hist[b] += 1
    return hist


def shannon_entropy(hist: Sequence[int], total: int) -> float:
    """Shannon 熵（bits/byte）：H = -Σ p·log2(p)。"""
    if total <= 0:
        return 0.0
    h = 0.0
    for c in hist:
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h


def print_histogram(hist: Sequence[int], total: int, start: int, end: int,
                    top: int) -> None:
    print()
    print("=" * 78)
    print("字节直方图 (256 桶)")
    print("=" * 78)
    print(f"  区间            : [{start:#x}, {end:#x})   长度 {total} B")
    if total == 0:
        print("  (区间为空)")
        return

    print()
    print("  桶布局（每行 16 个字节值；单元格为百分比，按该行最大值归一化）:")
    hdr = "        " + "".join(f"{c:>6X}" for c in range(16))
    print(hdr)
    for row in range(16):
        cells = []
        for col in range(16):
            v = hist[row * 16 + col]
            cells.append(f"{100.0 * v / total:>6.2f}")
        print(f"  {row * 16:02X}    " + "".join(cells))

    print()
    print("  计数明细（非零桶，按计数降序）:")
    pairs = sorted(((c, i) for i, c in enumerate(hist) if c),
                   key=lambda t: (-t[0], t[1]))
    shown = pairs if top == 0 else pairs[:top]
    print(f"  {'字节':>4}  {'计数':>14}  {'占比':>9}  可打印")
    for c, i in shown:
        ch = chr(i) if PRINTABLE_LO <= i < PRINTABLE_HI else "."
        print(f"  {i:#04x}  {c:>14}  {100.0 * c / total:>8.4f}%  {ch}")
    if top and len(pairs) > top:
        print(f"  ... 其余 {len(pairs) - top} 个非零桶已省略（--top 0 显示全部）")

    zeros = hist[0]
    distinct = sum(1 for c in hist if c)
    print()
    print(f"  非零桶数        : {distinct} / 256")
    print(f"  0x00 计数       : {zeros} ({100.0 * zeros / total:.4f}%)")
    entropy = shannon_entropy(hist, total)
    print(f"  Shannon 熵      : {entropy:.6f} bits/byte  "
          f"(理论上限 8.000000)")
    print(f"  汇总: 区间长度={total} 非零桶={distinct} 熵={entropy:.6f}")


# --------------------------------------------------------------------------
# 输出辅助
# --------------------------------------------------------------------------


def hex_context(buf: bytes, pos: int, length: int, ctx: int) -> str:
    lo = max(0, pos - ctx)
    hi = min(len(buf), pos + length + ctx)
    parts = []
    for i in range(lo, hi):
        tag = "<<" if pos <= i < pos + length else "  "
        parts.append(f"{buf[i]:02X}{tag}" if False else
                     (f"[{buf[i]:02X}]" if pos <= i < pos + length
                      else f"{buf[i]:02X}"))
    return f"{lo:#x}: " + " ".join(parts)


def ascii_preview(data: bytes, width: int = 16) -> str:
    return "".join(chr(b) if PRINTABLE_LO <= b < PRINTABLE_HI else "."
                   for b in data[:width])


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------


def do_search(args: argparse.Namespace, files: list[str]) -> int:
    mask, value = parse_hex_pattern(args.hex_pattern) if args.hex_pattern else (b"", b"")
    ascii_pat = args.ascii.encode("latin1") if args.ascii else b""
    if not mask and not ascii_pat:
        print("错误: 搜索模式需要 --hex 或 --ascii", file=sys.stderr)
        return 1

    limit = None if args.count == 0 else args.count
    total_hits = 0
    total_files_hit = 0
    total_bytes = 0
    lines: list[str] = []

    label_hex = args.hex_pattern or ""
    label_ascii = args.ascii or ""

    for path in files:
        try:
            with open(path, "rb") as fh:
                buf = fh.read()
        except OSError as exc:
            print(f"错误: 无法读取 {path!r}: {exc}", file=sys.stderr)
            return 2
        total_bytes += len(buf)
        start, end = 0, len(buf)
        resolved = resolve_range(args.rng, len(buf))
        if resolved is not None:
            rs, re_ = resolved
            if rs > len(buf):
                print(f"警告: 区间起点 {rs:#x} 超出 {path} 长度 {len(buf):#x}，"
                      f"该文件无命中")
                continue
            start = rs
            end = re_
        if end - start <= 0:
            continue

        print("=" * 78)
        print(f"文件: {path}")
        print("=" * 78)
        print(f"  文件大小        : {len(buf)} B ({len(buf):#x})")
        print(f"  搜索区间        : [{start:#x}, {end:#x})  ({end - start} B)")
        if mask:
            pat_txt = " ".join(f"{value[i]:02X}" if mask[i] else "??"
                               for i in range(len(mask)))
            print(f"  十六进制模式    : {pat_txt}   (长度 {len(mask)} B)")

        file_hits: list[tuple[int, bytes, str]] = []
        truncated_any = False

        if mask:
            hits, trunc = find_pattern(buf, mask, value, start, end, limit)
            truncated_any |= trunc
            for h in hits:
                file_hits.append((h, buf[h:h + len(mask)], "hex"))
        if ascii_pat:
            amask = b"\xff" * len(ascii_pat)
            hits, trunc = find_pattern(buf, amask, ascii_pat, start, end, limit)
            truncated_any |= trunc
            print(f"  ASCII 模式      : {args.ascii!r}   (长度 {len(ascii_pat)} B)")
            for h in hits:
                file_hits.append((h, buf[h:h + len(ascii_pat)], "ascii"))

        # 去重（hex 与 ascii 可能命中同一位置）并按偏移排序
        seen: set[tuple[int, str]] = set()
        uniq: list[tuple[int, bytes, str]] = []
        for h, data, kind in file_hits:
            key = (h, kind)
            if key in seen:
                continue
            seen.add(key)
            uniq.append((h, data, kind))
        uniq.sort(key=lambda t: (t[0], t[2]))

        if uniq:
            total_files_hit += 1
        print()
        if not uniq:
            print("  (该文件/区间无命中)")
        else:
            print(f"  {'#':>5}  {'文件偏移':>12}  {'十六进制':>12}  "
                  f"{'匹配字节'}")
            for i, (h, data, kind) in enumerate(uniq):
                ctx = ""
                if args.context > 0:
                    ctx = "  上下文 " + hex_context(buf, h, len(data),
                                                    args.context)
                print(f"  {i:>5}  {h:>12}  {h:#012x}  "
                      f"[{kind}] {data.hex(' ')}")
                if args.context > 0:
                    print(f"         {ctx}")
                if args.printable and printable_mask(data):
                    print(f"         可打印预览: {ascii_preview(data, 32)!r}")
                lines.append(f"{path}\t{h}\t{h:#x}\t{kind}\t{data.hex()}")

        file_hits_n = len(uniq)
        total_hits += file_hits_n
        print()
        print(f"  本文件命中数    : {file_hits_n}"
              + ("  (已达 --count 上限，可能截断)" if truncated_any else ""))
        if limit is not None and truncated_any:
            print(f"  提示: --count {args.count} 限制了每文件命中数；"
                  f"用 --count 0 获取全部")
        print()

    print("=" * 78)
    print("汇总")
    print("=" * 78)
    desc = []
    if label_hex:
        desc.append(f"hex={label_hex!r}")
    if label_ascii:
        desc.append(f"ascii={label_ascii!r}")
    rng_txt = f" range=[{args.rng[0]:#x},{args.rng[1]:#x})" if args.rng else ""
    print(f"  文件数          : {len(files)}  (有命中的文件数 {total_files_hit})")
    print(f"  扫描字节数      : {total_bytes}")
    print(f"  模式            : {' '.join(desc)}{rng_txt}")
    print(f"  汇总: 命中数={total_hits}"
          + ("  (每文件受 --count 限制)" if limit is not None else ""))

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write("file\toffset\toffset_hex\tkind\tbytes_hex\n")
                for ln in lines:
                    fh.write(ln + "\n")
        except OSError as exc:
            print(f"错误: 无法写出 {args.out!r}: {exc}", file=sys.stderr)
            return 1
        print(f"  已写出命中清单: {args.out}")
    return 0


def do_strings(args: argparse.Namespace, files: list[str]) -> int:
    limit = None if args.count == 0 else args.count
    total = 0
    total_bytes = 0
    for path in files:
        try:
            with open(path, "rb") as fh:
                buf = fh.read()
        except OSError as exc:
            print(f"错误: 无法读取 {path!r}: {exc}", file=sys.stderr)
            return 2
        total_bytes += len(buf)
        start, end = 0, len(buf)
        resolved = resolve_range(args.rng, len(buf))
        if resolved is not None:
            rs, re_ = resolved
            if rs > len(buf):
                print(f"警告: 区间起点 {rs:#x} 超出 {path} 长度 {len(buf):#x}")
                continue
            start = rs
            end = re_
        strings, trunc = extract_strings(buf, args.strings, start, end, limit)
        print("=" * 78)
        print(f"文件: {path}   ASCII 串（长度 >= {args.strings}）"
              f"  区间 [{start:#x}, {end:#x})")
        print("=" * 78)
        if not strings:
            print("  (无符合条件的字符串)")
        for off, s in strings:
            txt = s.decode("latin1")
            print(f"  {off:#012x}  ({off:>12})  len={len(s):<5}  {txt!r}")
        if trunc:
            print(f"  ... 已达 --count {args.count} 上限，输出被截断")
        print()
        print(f"  本文件字符串数  : {len(strings)}"
              + ("  (已截断)" if trunc else ""))
        print()
        total += len(strings)

    print("=" * 78)
    print("汇总")
    print("=" * 78)
    print(f"  文件数          : {len(files)}")
    print(f"  扫描字节数      : {total_bytes}")
    print(f"  最小长度        : {args.strings}")
    print(f"  汇总: 命中数={total}"
          + ("  (每文件受 --count 限制)" if limit is not None else ""))
    return 0


def do_histogram(args: argparse.Namespace, files: list[str]) -> int:
    for path in files:
        try:
            with open(path, "rb") as fh:
                buf = fh.read()
        except OSError as exc:
            print(f"错误: 无法读取 {path!r}: {exc}", file=sys.stderr)
            return 2
        start, end = 0, len(buf)
        resolved = resolve_range(args.rng, len(buf))
        if resolved is not None:
            rs, re_ = resolved
            if rs > len(buf):
                print(f"错误: 区间起点 {rs:#x} 超出 {path} 长度 {len(buf):#x}",
                      file=sys.stderr)
                return 1
            start = rs
            end = re_
        print("=" * 78)
        print(f"文件: {path}   (大小 {len(buf)} B / {len(buf):#x})")
        print("=" * 78)
        hist = byte_histogram(buf, start, end)
        print_histogram(hist, end - start, start, end, args.top)
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "示例（路径均为占位符，请替换为本地实际文件）：\n"
        "  python tools/byte_scanner.py <target.bin> --hex \"48 8D 15 ?? ??\" "
        "--context 8\n"
        "  python tools/byte_scanner.py <target.bin> --ascii \"amdhsa\"\n"
        "  python tools/byte_scanner.py <target.bin> --strings 8 --range 0x1000:0x2000\n"
        "  python tools/byte_scanner.py <target.bin> --byte-histogram "
        "--range 0x1629:\n"
    )
    ap = argparse.ArgumentParser(
        prog="byte_scanner.py",
        description="通用只读二进制工具：带通配的十六进制模式搜索、ASCII 串提取、"
                    "字节直方图与 Shannon 熵。",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version",
                    version="byte_scanner.py 1.0.0")
    ap.add_argument("files", nargs="+", help="待扫描文件，一个或多个（只读）")

    mode = ap.add_argument_group("模式")
    mode.add_argument("--hex", dest="hex_pattern", default=None, metavar="PATTERN",
                      help="十六进制模式，空白分隔，?? 为单字节通配，"
                           "例如 \"48 8D 15 ?? 00\"")
    mode.add_argument("--ascii", default=None, metavar="STRING",
                      help="额外搜索该字面 ASCII 串")
    mode.add_argument("--strings", type=int, default=None, metavar="MINLEN",
                      help="字符串提取模式：列出长度 >= MINLEN 的可打印 ASCII 串")
    mode.add_argument("--byte-histogram", action="store_true",
                      help="字节直方图模式：256 桶频率表 + Shannon 熵")

    scope = ap.add_argument_group("范围与输出")
    scope.add_argument("--range", dest="rng", type=parse_range, default=None,
                       metavar="START:END",
                       help="限定搜索/统计区间（十六进制或十进制），"
                            "例如 0x1000:0x2000；写作 START: 表示到文件末尾，"
                            "例如 0x1629:")
    scope.add_argument("--count", type=parse_int, default=0, metavar="N",
                       help="每文件最大命中数（0 = 不限制，默认 0）")
    scope.add_argument("--context", type=parse_int, default=0, metavar="N",
                       help="命中前后各打印 N 字节十六进制上下文（默认 0）")
    scope.add_argument("--printable", action="store_true",
                       help="对全可打印的命中额外打印 ASCII 预览")
    scope.add_argument("--top", type=parse_int, default=32, metavar="N",
                       help="直方图计数明细显示前 N 个非零桶（0 = 全部，默认 32）")
    scope.add_argument("--out", default=None, metavar="PATH",
                       help="把命中清单写出为该文件（唯一允许的写出）")
    return ap


def main(argv: Iterable[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(list(argv) if argv is not None else None)

    modes = sum(bool(x) for x in (args.hex_pattern, args.ascii,
                                  args.strings is not None,
                                  args.byte_histogram))
    if modes == 0:
        print("错误: 需要指定 --hex / --ascii / --strings / --byte-histogram "
              "之一", file=sys.stderr)
        ap.print_usage(sys.stderr)
        return 1
    if args.strings is not None and args.strings < 1:
        print("错误: --strings 的最小长度必须 >= 1", file=sys.stderr)
        return 1

    if args.byte_histogram:
        return do_histogram(args, args.files)
    if args.strings is not None and not (args.hex_pattern or args.ascii):
        return do_strings(args, args.files)
    return do_search(args, args.files)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
