#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""msgpack_extract.py —— 从 HIP fat binary（clang offload bundle）中提取
AMDGPU 内核元数据（只读）。

用途
----
很多 HIP/ROCm 产物会把多个 GPU 目标的 ELF 打包进一个容器节
（如 Windows DLL 中的 ``.hip_fat`` 节）。本工具解析该容器，逐目标解出
ELF 里的 ``AMDGPU`` 元数据 note，并把 ``amdhsa.kernels`` 表格整理成可读输出：

  * 每个目标：triple 字符串、``amdhsa.kernels`` 内核个数；
  * 每个内核：``.name``、``.kernarg_segment_size``、``.kernarg_segment_align``，
    以及完整的 ``.args`` 列表（``value_kind`` / ``size`` / ``offset`` / ``name``）；
  * ``--json OUT`` 输出结构化 JSON；``--kernel SUBSTR`` 按子串过滤内核。

容器布局
--------
::

    "__CLANG_OFFLOAD_BUNDLE__"     ; 24 字节魔数
    uint64  numBundles             ; 后续 bundle 数量
    repeat numBundles times:
        uint64 offset              ; 相对容器起始（= 节起始）的偏移
        uint64 size                ; bundle 字节数（可为 0 = 占位）
        uint64 tripleSize          ; 该 bundle 的 triple 字符串长度
        char   triple[tripleSize]  ; 非 NUL 结尾
    ; 头部结束处按 8 字节对齐

注意：**host 占位 bundle 的 size 为 0**（例如 triple 形如
``host-x86_64-...``），它没有可解析载荷，必须显式跳过而不是当作错误。

设备 bundle 的 note 定位
------------------------
对每个设备 bundle，从 bundle 起始按固定偏移读取 ELF 的 note（自行核对
ELF 头中的 e_phoff 亦可，但本工具按该容器约定使用固定偏移）：

::

    +0x238  uint32 namesz
    +0x23C  uint32 descsz      ; msgpack 文档的字节长度
    +0x240  uint32 type
    +0x244  char   name[namesz padded to 4]
    +0x24C  ...    msgpack document (descsz bytes)

**关键约束**：读取 note 的 msgpack 长度必须以 ``descsz`` 为硬上界。
绝不能"向后扫描"寻找看起来像 msgpack 的字节——那样会把相邻 note 或
字符串表误解析进来，产生看似合理实则错误的结果。本工具严格
``blob = buf[desc_off : desc_off + descsz]``，并在解码器内部再次以
blob 长度设限。

依赖
----
  * Python 3.11+
  * ``msgpack``（必需）：``msgpack.unpackb(blob, raw=False, strict_map_key=False)``。
    ``raw=False`` 让 str 键解码为 ``str``；``strict_map_key=False`` 允许
    非字符串键（AMDGPU 元数据里存在整数键）。

退出码：0 成功，1 参数/解析错误，2 文件不可读。

本工具**只读**：唯一允许的写出是 ``--json OUT`` 指定的路径。
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from typing import Any, Iterable

try:
    import msgpack  # type: ignore

    HAVE_MSGPACK = True
except Exception:  # pragma: no cover - 环境相关
    msgpack = None  # type: ignore
    HAVE_MSGPACK = False


CONTAINER_MAGIC = b"__CLANG_OFFLOAD_BUNDLE__"

# 设备 bundle 内 ELF note 的固定偏移（容器约定）
NOTE_OFFSET = 0x238
NOTE_NAMESZ_OFF = NOTE_OFFSET + 0x00   # +0x238
NOTE_DESCSZ_OFF = NOTE_OFFSET + 0x04   # +0x23C
NOTE_TYPE_OFF = NOTE_OFFSET + 0x08     # +0x240
NOTE_NAME_OFF = NOTE_OFFSET + 0x0C     # +0x244
NOTE_DESC_OFF = NOTE_OFFSET + 0x14     # +0x24C

ELF_MAGIC = b"\x7fELF"

# 元数据里可能承载内核表的键名（不同 ROCm 版本略有差异）
KERNEL_LIST_KEYS = ("amdhsa.kernels", "amdgpu.kernels", "kernels")


class ExtractError(Exception):
    """容器或 note 结构不合法时抛出。"""


# --------------------------------------------------------------------------
# 容器解析
# --------------------------------------------------------------------------


def find_container(buf: bytes, section_off: int | None = None) -> int:
    """返回容器魔数的文件偏移。

    优先使用调用方给出的节内偏移；未给出时在文件中搜索魔数。
    """
    if section_off is not None:
        if buf[section_off:section_off + 24] != CONTAINER_MAGIC:
            raise ExtractError(
                f"{section_off:#x} 处不是容器魔数 "
                f"{CONTAINER_MAGIC.decode()!r}")
        return section_off
    idx = buf.find(CONTAINER_MAGIC)
    if idx < 0:
        raise ExtractError(
            f"未找到容器魔数 {CONTAINER_MAGIC.decode()!r}；"
            f"该文件可能不是 HIP fat binary（可用 --offset 手动指定容器偏移）")
    return idx


def parse_bundles(buf: bytes, base: int) -> tuple[list[dict[str, Any]], int]:
    """解析容器头，返回 (bundle 列表, 头部结束的文件偏移)。"""
    if base + 32 > len(buf):
        raise ExtractError("容器头越界")
    count = struct.unpack_from("<Q", buf, base + 24)[0]
    if count > 4096:
        raise ExtractError(f"bundle 数量异常：{count}")
    p = base + 32
    out: list[dict[str, Any]] = []
    for i in range(count):
        if p + 24 > len(buf):
            raise ExtractError(f"第 {i} 个 bundle 头越界")
        offset, size, triple_size = struct.unpack_from("<QQQ", buf, p)
        p += 24
        if p + triple_size > len(buf):
            raise ExtractError(f"第 {i} 个 bundle 的 triple 越界")
        triple = buf[p:p + triple_size].decode("ascii", "replace")
        p += triple_size
        out.append({
            "index": i,
            "offset": offset,
            "size": size,
            "triple_size": triple_size,
            "triple": triple,
            # 容器内偏移是相对容器起始（节起始）的
            "file_offset": base + offset,
        })
    # 头部按 8 字节对齐
    aligned = p + ((-p) % 8)
    return out, aligned


def parse_note(buf: bytes, elf_off: int, note_off: int = NOTE_OFFSET
               ) -> dict[str, Any]:
    """在 bundle 内固定偏移处读取 ELF note 并解码其中的 msgpack 文档。

    强制以 ``descsz`` 为上界，绝不越过它向后扫描。
    """
    note = elf_off + note_off
    if note + 16 > len(buf):
        raise ExtractError(f"note 头越界（file {note:#x}）")
    namesz, descsz, ntype = struct.unpack_from("<III", buf, note)
    if namesz > 256:
        raise ExtractError(f"namesz 异常：{namesz}")
    name_raw = buf[note + 12:note + 12 + namesz]
    name = name_raw.split(b"\x00", 1)[0].decode("ascii", "replace")
    # name 按 4 字节对齐
    desc_off = note + 12 + ((namesz + 3) // 4) * 4
    if descsz == 0:
        raise ExtractError("descsz 为 0，note 中无元数据")
    if desc_off + descsz > len(buf):
        raise ExtractError(
            f"msgpack 文档越界：descsz={descsz} 需要 file "
            f"[{desc_off:#x}, {desc_off + descsz:#x})，但文件只有 {len(buf):#x} 字节")
    # 严格按 descsz 截断 —— 这是唯一的长度来源
    blob = buf[desc_off:desc_off + descsz]
    if len(blob) != descsz:
        raise ExtractError("msgpack 文档长度不足")

    doc = decode_msgpack(blob)
    return {
        "note_file_offset": note,
        "note_offset_in_bundle": note_off,
        "namesz": namesz,
        "descsz": descsz,
        "type": ntype,
        "name": name,
        "desc_file_offset": desc_off,
        "desc_offset_in_bundle": desc_off - elf_off,
        "document": doc,
    }


def decode_msgpack(blob: bytes) -> Any:
    """解码 msgpack 文档。

    使用 ``raw=False``（解出 str 而非 bytes）与 ``strict_map_key=False``
    （允许整数键）。
    """
    if not HAVE_MSGPACK:
        raise ExtractError(
            "需要 msgpack 库：pip install msgpack")
    try:
        return msgpack.unpackb(blob, raw=False, strict_map_key=False)
    except Exception as exc:
        raise ExtractError(f"msgpack 解码失败: {exc}") from exc


def is_device_triple(triple: str) -> bool:
    return "amdgcn" in triple or "amdhsa" in triple


def short_target(triple: str) -> str:
    """从 triple 中提取紧凑目标名，例如 hipv4-amdgcn-amd-amdhsa--gfx1100 -> gfx1100。"""
    parts = [p for p in triple.split("-") if p]
    if not parts:
        return triple
    # 形如 ...--gfx1100 时最后一个 '-' 分段为空，取末段
    return parts[-1]


def find_kernel_list(doc: Any) -> tuple[list[Any] | None, str | None]:
    """在顶层字典中查找内核表。"""
    if not isinstance(doc, dict):
        return None, None
    for key in KERNEL_LIST_KEYS:
        v = doc.get(key)
        if isinstance(v, list):
            return v, key
    return None, None


# --------------------------------------------------------------------------
# 内核信息提取
# --------------------------------------------------------------------------


def normalize_kernel(k: Any, index: int) -> dict[str, Any]:
    """把单个内核记录整理为扁平字典；缺失字段保留 None。"""
    if not isinstance(k, dict):
        return {"index": index, "raw": repr(k)}
    args_out: list[dict[str, Any]] = []
    raw_args = k.get(".args")
    if isinstance(raw_args, list):
        for j, a in enumerate(raw_args):
            if not isinstance(a, dict):
                args_out.append({"index": j, "raw": repr(a)})
                continue
            args_out.append({
                "index": j,
                "name": a.get(".name"),
                "value_kind": a.get(".value_kind"),
                "size": a.get(".size"),
                "offset": a.get(".offset"),
                "address_space": a.get(".address_space"),
                "actual_access": a.get(".actual_access"),
                "is_const": a.get(".is_const"),
                "is_restrict": a.get(".is_restrict"),
                "is_volatile": a.get(".is_volatile"),
                "is_pipe": a.get(".is_pipe"),
            })
    return {
        "index": index,
        "name": k.get(".name"),
        "symbol": k.get(".symbol"),
        "kernarg_segment_size": k.get(".kernarg_segment_size"),
        "kernarg_segment_align": k.get(".kernarg_segment_align"),
        "group_segment_fixed_size": k.get(".group_segment_fixed_size"),
        "private_segment_fixed_size": k.get(".private_segment_fixed_size"),
        "max_flat_workgroup_size": k.get(".max_flat_workgroup_size"),
        "sgpr_count": k.get(".sgpr_count"),
        "vgpr_count": k.get(".vgpr_count"),
        "wavefront_size": k.get(".wavefront_size"),
        "language": k.get(".language"),
        "language_version": k.get(".language_version"),
        "args": args_out,
    }


def safe_scalar(v: Any) -> Any:
    """把 msgpack 可能解出的 bytes 等转为可 JSON 序列化 / 可打印的值。"""
    if isinstance(v, bytes):
        return v.hex()
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------


def print_target_summary(targets: list[dict[str, Any]]) -> None:
    print()
    print("=" * 78)
    print("目标汇总")
    print("=" * 78)
    print(f"  {'#':>3}  {'目标':<18} {'内核数':>6}  {'元数据键':<22} triple")
    for t in targets:
        if t.get("skipped"):
            print(f"  {t['index']:>3}  {'(跳过)':<18} {'-':>6}  {'-':<22} "
                  f"{t['triple']}  [{t['skip_reason']}]")
            continue
        keys = t.get("document_keys")
        keys_txt = ",".join(keys) if keys else "-"
        if len(keys_txt) > 20:
            keys_txt = keys_txt[:19] + "…"
        print(f"  {t['index']:>3}  {short_target(t['triple']):<18} "
              f"{t['kernel_count']:>6}  {keys_txt:<22} {t['triple']}")


def print_kernels(target: dict[str, Any], kernel_filter: str | None,
                  limit: int | None, verbose: bool) -> None:
    label = short_target(target["triple"])
    ks = target.get("kernels") or []
    shown = ks
    if kernel_filter:
        needle = kernel_filter.lower()
        shown = [k for k in ks if needle in str(k.get("name") or "").lower()]
    print()
    print("=" * 78)
    print(f"目标 {label} —— {target['triple']}")
    print("=" * 78)
    print(f"  bundle 索引     : {target['index']}")
    print(f"  bundle 文件偏移 : {target['file_offset']:#x}  "
          f"大小 {target['size']:#x} ({target['size']} B)")
    print(f"  note 名称/类型  : {target.get('note_name')!r} / "
          f"{target.get('note_type')}")
    print(f"  namesz/descsz   : {target.get('namesz')} / {target.get('descsz')}  "
          f"(msgpack 文档 file {target.get('desc_file_offset', 0):#x})")
    print(f"  内核总数        : {len(ks)}"
          + (f"   匹配 {kernel_filter!r} 的内核数: {len(shown)}"
             if kernel_filter else ""))
    if not ks:
        print("  (该目标没有内核表)")
        return
    print()
    listed = shown if limit is None else shown[:limit]
    for k in listed:
        kname = k.get("name") or "(无名)"
        print(f"  [{k['index']:>3}] {kname}")
        print(f"        .kernarg_segment_size  = {k.get('kernarg_segment_size')}")
        print(f"        .kernarg_segment_align = {k.get('kernarg_segment_align')}")
        if verbose:
            for extra in ("symbol", "group_segment_fixed_size",
                          "private_segment_fixed_size",
                          "max_flat_workgroup_size", "sgpr_count",
                          "vgpr_count", "wavefront_size", "language",
                          "language_version"):
                if k.get(extra) is not None:
                    print(f"        .{extra:<22} = {k.get(extra)}")
        args = k.get("args") or []
        print(f"        .args ({len(args)}):")
        if not args:
            print("            (无参数)")
        for a in args:
            if "value_kind" not in a:
                print(f"            [{a.get('index')}] {a.get('raw')}")
                continue
            print(f"            [{a['index']:>2}] offset={a['offset']!s:<5} "
                  f"size={a['size']!s:<5} value_kind={a['value_kind']!s:<20} "
                  f"name={a['name']!r}")
            if verbose:
                extras = {kk: safe_scalar(vv) for kk, vv in a.items()
                          if kk not in ("index", "offset", "size",
                                        "value_kind", "name")
                          and vv is not None}
                if extras:
                    print(f"                 其它: {extras}")
    if limit is not None and len(shown) > limit:
        print(f"  ... 其余 {len(shown) - limit} 个内核已省略（--limit 0 显示全部）")


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def build_targets(buf: bytes, bundles: list[dict[str, Any]],
                  keep_host: bool) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for b in bundles:
        entry: dict[str, Any] = {
            "index": b["index"],
            "triple": b["triple"],
            "offset": b["offset"],
            "size": b["size"],
            "file_offset": b["file_offset"],
        }
        # host 占位 bundle：size 为 0，无载荷
        if b["size"] == 0:
            entry.update({
                "skipped": True,
                "skip_reason": "size=0（host 占位 bundle，无可解析载荷）",
            })
            targets.append(entry)
            continue
        if not is_device_triple(b["triple"]) and not keep_host:
            entry.update({
                "skipped": True,
                "skip_reason": "非设备 triple",
            })
            targets.append(entry)
            continue
        elf_off = b["file_offset"]
        if elf_off + 4 > len(buf):
            entry.update({"skipped": True, "skip_reason": "bundle 偏移越界"})
            targets.append(entry)
            continue
        if buf[elf_off:elf_off + 4] != ELF_MAGIC:
            entry.update({
                "skipped": True,
                "skip_reason": f"bundle 起始不是 ELF（{buf[elf_off:elf_off + 4]!r}）",
            })
            targets.append(entry)
            continue
        entry["is_elf"] = True
        try:
            note = parse_note(buf, elf_off)
        except ExtractError as exc:
            entry.update({"skipped": True, "skip_reason": f"note 解析失败: {exc}"})
            targets.append(entry)
            continue

        doc = note.pop("document")
        entry.update({
            "skipped": False,
            "note_name": note["name"],
            "note_type": note["type"],
            "namesz": note["namesz"],
            "descsz": note["descsz"],
            "desc_file_offset": note["desc_file_offset"],
            "desc_offset_in_bundle": note["desc_offset_in_bundle"],
            "note_file_offset": note["note_file_offset"],
        })
        if note["name"] != "AMDGPU":
            entry["note_name_warning"] = (
                f"note 名称为 {note['name']!r}，非 'AMDGPU'")
        klist, kkey = find_kernel_list(doc)
        entry["document_keys"] = (
            sorted(str(k) for k in doc.keys())
            if isinstance(doc, dict) else None)
        entry["kernel_list_key"] = kkey
        if klist is None:
            entry["kernel_count"] = 0
            entry["kernels"] = []
            entry["document"] = doc if isinstance(doc, (dict, list)) else str(doc)
        else:
            kernels = [normalize_kernel(k, i) for i, k in enumerate(klist)]
            entry["kernel_count"] = len(kernels)
            entry["kernels"] = kernels
            # 完整文档可能很大：JSON 里保留（用户显式要求结构化转储）
            entry["document"] = doc if isinstance(doc, (dict, list)) else str(doc)
        targets.append(entry)
    return targets


def json_safe(obj: Any) -> Any:
    """递归把 bytes 等不可序列化对象转为字符串。"""
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "示例（路径均为占位符，请替换为本地实际文件）：\n"
        "  python tools/msgpack_extract.py <target.dll> --offset 0x78200\n"
        "  python tools/msgpack_extract.py <target.dll> --offset 0x78200 "
        "--kernel accumulate\n"
        "  python tools/msgpack_extract.py <target.dll> --offset 0x78200 "
        "--json out.json\n"
    )
    ap = argparse.ArgumentParser(
        prog="msgpack_extract.py",
        description="从 HIP fat binary（__CLANG_OFFLOAD_BUNDLE__ 容器）中提取 "
                    "AMDGPU 内核元数据（amdhsa.kernels）。只读。",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version",
                    version="msgpack_extract.py 1.0.0")
    ap.add_argument("file", help="待解析文件路径（只读）")
    ap.add_argument("--offset", type=lambda s: int(s, 0), default=None,
                    metavar="OFF",
                    help="容器魔数的文件偏移（十六进制或十进制）。"
                         "省略时在整个文件中搜索魔数")
    ap.add_argument("--json", dest="json_out", default=None, metavar="OUT",
                    help="把结构化结果写入该 JSON 文件（唯一允许的写出）")
    ap.add_argument("--kernel", default=None, metavar="SUBSTR",
                    help="只显示名称包含该子串（不区分大小写）的内核")
    ap.add_argument("--limit", type=int, default=64,
                    help="每个目标最多打印的内核数（默认 64；0 = 不限制）")
    ap.add_argument("--verbose", action="store_true",
                    help="打印内核与参数的其余字段")
    ap.add_argument("--keep-host", action="store_true",
                    help="不因 triple 非设备而跳过（size=0 的占位仍会跳过）")
    return ap


def main(argv: Iterable[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(list(argv) if argv is not None else None)

    if not HAVE_MSGPACK:
        print("错误: 本工具需要 msgpack 库：pip install msgpack", file=sys.stderr)
        return 1

    try:
        with open(args.file, "rb") as fh:
            buf = fh.read()
    except OSError as exc:
        print(f"错误: 无法读取文件 {args.file!r}: {exc}", file=sys.stderr)
        return 2

    try:
        base = find_container(buf, args.offset)
        bundles, header_end = parse_bundles(buf, base)
    except ExtractError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    targets = build_targets(buf, bundles, args.keep_host)
    device = [t for t in targets if not t.get("skipped")]
    skipped = [t for t in targets if t.get("skipped")]

    print("=" * 78)
    print("HIP fat binary 容器")
    print("=" * 78)
    print(f"  文件            : {args.file}")
    print(f"  文件大小        : {len(buf)} B ({len(buf):#x})")
    print(f"  容器魔数        : {CONTAINER_MAGIC.decode()!r} @ {base:#x}")
    print(f"  bundle 数量     : {len(bundles)}")
    print(f"  头部结束偏移    : {header_end:#x}  (自容器 +{header_end - base:#x})")
    print(f"  host 占位 bundle: {sum(1 for b in bundles if b['size'] == 0)} 个")
    print(f"  msgpack 版本    : {getattr(msgpack, 'version', 'unknown')}")

    print_target_summary(targets)

    limit = None if args.limit == 0 else args.limit
    for t in device:
        print_kernels(t, args.kernel, limit, args.verbose)

    # 一致性观察：跨目标的内核名序列是否相同
    if len(device) >= 2:
        base_names = [k.get("name") for k in (device[0].get("kernels") or [])]
        print()
        print("=" * 78)
        print("跨目标一致性（以第一个设备目标为基准）")
        print("=" * 78)
        for t in device:
            names = [k.get("name") for k in (t.get("kernels") or [])]
            print(f"  {short_target(t['triple']):<18} 内核数={len(names):<4} "
                  f"名称序列一致={names == base_names}")

    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    print(f"  bundle 总数        : {len(bundles)}")
    print(f"  设备目标数         : {len(device)}")
    print(f"  跳过的 bundle 数   : {len(skipped)}")
    for t in skipped:
        print(f"      #{t['index']} {t['triple']}  <- {t.get('skip_reason')}")
    for t in device:
        print(f"  目标 {short_target(t['triple']):<18} 内核数 = {t.get('kernel_count')}")

    if args.json_out:
        payload = {
            "source": args.file,
            "file_size": len(buf),
            "container_offset": base,
            "container_magic": CONTAINER_MAGIC.decode(),
            "bundle_count": len(bundles),
            "header_end": header_end,
            "targets": targets,
            "summary": {
                "bundles": len(bundles),
                "device_targets": len(device),
                "skipped_bundles": len(skipped),
                "kernels_per_target": {
                    short_target(t["triple"]): t.get("kernel_count")
                    for t in device
                },
            },
        }
        try:
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump(json_safe(payload), fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            print(f"错误: 无法写出 JSON {args.json_out!r}: {exc}", file=sys.stderr)
            return 1
        print()
        print(f"  已写出 JSON: {args.json_out}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
