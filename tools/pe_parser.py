#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pe_parser.py —— 通用只读 PE32/PE32+ 结构解析器（命令行工具）。

用途
----
对任意 PE 文件做结构勘察，无需依赖特定分析框架：
  * DOS 头 / NT 头（COFF File Header + Optional Header）字段；
  * 节表（节名、虚拟地址 VA、虚拟大小、原始偏移、原始大小、节属性）；
  * 数据目录（16 项，RVA / Size）；
  * 导出表（序号、提示名、RVA、前向字符串）；
  * 导入表（按 DLL 分组；支持 hint/name 与 **序号导入** 两种形式）；
  * .reloc 重定位块的**手工**解析（见下方 "重定位语义" 说明）；
  * .pdata 异常表转储为 (StartRVA, EndRVA, UnwindInfoRVA) 三元组；
  * 按节名 + 节内文件偏移做十六进制转储。

依赖
----
  * Python 3.11+
  * pefile（**可选**，非必需）。若已安装则默认用它读取头部/节表/数据目录/导入导出，
    以交叉印证；若未安装，或显式传入 ``--no-pefile``，本工具自动回退到内置的
    ``struct`` 手工解析路径。因此**任何子命令在无 pefile 环境下依然可用**。

重定位语义（实现说明）
----------------------
本工具的 .reloc 解析**完全手工**完成，不依赖任何库的 ``rva`` 派生语义：

    IMAGE_BASE_RELOCATION {
        uint32 PageRVA;      // 本块覆盖的页基址 RVA
        uint32 SizeOfBlock;  // 含本 8 字节头的整块字节数
        uint16 TypeOffset[(SizeOfBlock - 8) / 2];
    }

每个 u16 条目拆分：**高 4 位为类型，低 12 位为页内偏移**，
目标 RVA = ``PageRVA + (entry & 0x0FFF)``。
注意：低 12 位是**绝对页内偏移**，不是相对上一项、也不是已重定位后的地址；
不要把它当作库返回的 ``rva`` 直接使用。类型 0（``IMAGE_REL_BASED_ABSOLUTE``）
是纯填充项，其偏移位无意义，默认从统计与过滤中剔除。

退出码：0 成功，1 参数/解析错误，2 文件不可读。

本工具**只读**：除用户用 ``--hex-out`` 显式指定的输出文件外，不写入任何路径。
"""

from __future__ import annotations

import argparse
import collections
import struct
import sys
from typing import Any, Iterable

try:  # pefile 是可选依赖，缺失时走手工解析路径
    import pefile  # type: ignore

    HAVE_PEFILE = True
except Exception:  # pragma: no cover - 环境相关
    pefile = None  # type: ignore
    HAVE_PEFILE = False


# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

IMAGE_FILE_MACHINE = {
    0x014C: "i386",
    0x8664: "AMD64",
    0x01C0: "ARM",
    0x01C4: "ARMv7 (THUMB)",
    0xAA64: "ARM64",
    0x0200: "IA64",
}

IMAGE_SUBSYSTEM = {
    0: "UNKNOWN",
    1: "NATIVE",
    2: "WINDOWS_GUI",
    3: "WINDOWS_CUI",
    5: "OS2_CUI",
    7: "POSIX_CUI",
    9: "WINDOWS_CE_GUI",
    10: "EFI_APPLICATION",
    11: "EFI_BOOT_SERVICE_DRIVER",
    12: "EFI_RUNTIME_DRIVER",
    13: "EFI_ROM",
    14: "XBOX",
    16: "WINDOWS_BOOT_APPLICATION",
}

SECTION_CHARACTERISTICS = [
    (0x00000020, "CNT_CODE"),
    (0x00000040, "CNT_INITIALIZED_DATA"),
    (0x00000080, "CNT_UNINITIALIZED_DATA"),
    (0x00000200, "LNK_INFO"),
    (0x00000800, "LNK_REMOVE"),
    (0x00001000, "LNK_COMDAT"),
    (0x00008000, "GPREL"),
    (0x00020000, "MEM_PURGEABLE"),
    (0x00040000, "MEM_LOCKED"),
    (0x00080000, "MEM_PRELOAD"),
    (0x00100000, "ALIGN_1BYTES"),
    (0x00200000, "ALIGN_2BYTES"),
    (0x00300000, "ALIGN_4BYTES"),
    (0x00400000, "ALIGN_8BYTES"),
    (0x00500000, "ALIGN_16BYTES"),
    (0x00600000, "ALIGN_32BYTES"),
    (0x00700000, "ALIGN_64BYTES"),
    (0x00800000, "ALIGN_128BYTES"),
    (0x00900000, "ALIGN_256BYTES"),
    (0x00A00000, "ALIGN_512BYTES"),
    (0x00B00000, "ALIGN_1024BYTES"),
    (0x00C00000, "ALIGN_2048BYTES"),
    (0x00D00000, "ALIGN_4096BYTES"),
    (0x00E00000, "ALIGN_8192BYTES"),
    (0x01000000, "LNK_NRELOC_OVFL"),
    (0x02000000, "MEM_DISCARDABLE"),
    (0x04000000, "MEM_NOT_CACHED"),
    (0x08000000, "MEM_NOT_PAGED"),
    (0x10000000, "MEM_SHARED"),
    (0x20000000, "MEM_EXECUTE"),
    (0x40000000, "MEM_READ"),
    (0x80000000, "MEM_WRITE"),
]

DATA_DIRECTORY_NAMES = [
    "EXPORT",
    "IMPORT",
    "RESOURCE",
    "EXCEPTION",
    "SECURITY",
    "BASERELOC",
    "DEBUG",
    "ARCHITECTURE",
    "GLOBALPTR",
    "TLS",
    "LOAD_CONFIG",
    "BOUND_IMPORT",
    "IAT",
    "DELAY_IMPORT",
    "COM_DESCRIPTOR",
    "RESERVED",
]

# 重定位类型 -> 该类型条目占用的“被修补字段”宽度（字节）。
# 宽度用于 --range 区间相交判断；语义未知的类型按 4 字节保守处理。
RELOC_TYPE_WIDTH = {
    1: 4,   # HIGH
    2: 4,   # LOW
    3: 4,   # HIGHLOW
    4: 4,   # HIGHADJ
    5: 2,   # MIPS_JMPADDR / ARM_MOV32
    7: 4,   # ARM_MOV32T / THUMB_MOV32
    9: 2,   # MIPS_JMPADDR16
    10: 8,  # DIR64
}

RELOC_TYPE_NAMES = {
    0: "ABSOLUTE",
    1: "HIGH",
    2: "LOW",
    3: "HIGHLOW",
    4: "HIGHADJ",
    5: "MIPS_JMPADDR",
    7: "THUMB_MOV32",
    9: "MIPS_JMPADDR16",
    10: "DIR64",
}

# 已知节名 -> 何时可被视为可执行代码，用于概览提示（不做任何语义裁剪）。
CODE_SECTIONS = (".text", "CODE", "PAGE")


# --------------------------------------------------------------------------
# 底层读取helper
# --------------------------------------------------------------------------


class PeFormatError(Exception):
    """PE 结构无法解析（偏移越界 / 魔数不符）时抛出。"""


def _u8(buf: bytes, off: int) -> int:
    return buf[off]


def _u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def _cstr(buf: bytes, off: int, limit: int = 4096) -> str:
    """读取以 NUL 结尾的 ASCII 字符串，越界则截断。"""
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\x00", off, min(len(buf), off + limit))
    if end < 0:
        end = min(len(buf), off + limit)
    return buf[off:end].decode("latin1")


# --------------------------------------------------------------------------
# 解析结果数据结构
# --------------------------------------------------------------------------


class Section:
    __slots__ = ("index", "name", "virtual_size", "virtual_address",
                 "raw_size", "raw_offset", "characteristics")

    def __init__(self, index: int, name: str, virtual_size: int,
                 virtual_address: int, raw_size: int, raw_offset: int,
                 characteristics: int):
        self.index = index
        self.name = name
        self.virtual_size = virtual_size
        self.virtual_address = virtual_address
        self.raw_size = raw_size
        self.raw_offset = raw_offset
        self.characteristics = characteristics

    @property
    def span_end(self) -> int:
        """节在文件中的原始数据终点（不含对齐填充外区域）。"""
        return self.raw_offset + self.raw_size

    def rva_limit(self) -> int:
        return self.virtual_address + max(self.virtual_size, self.raw_size)

    def contains_rva(self, rva: int) -> bool:
        return self.virtual_address <= rva < self.rva_limit()

    def char_flags(self) -> list[str]:
        return [n for bit, n in SECTION_CHARACTERISTICS
                if self.characteristics & bit]

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Section {self.name} VA={self.virtual_address:#x}>"


class PeFile:
    """手工 struct 解析的 PE 视图（pefile 不可用时的完整回退路径）。"""

    def __init__(self, buf: bytes, path: str = "<mem>"):
        self.buf = buf
        self.path = path
        self.sections: list[Section] = []
        self.data_directories: list[tuple[int, int]] = []
        self.is_pe32_plus = False
        self.image_base = 0
        self._parse()

    # ---- 头部 ----
    def _parse(self) -> None:
        buf = self.buf
        if len(buf) < 0x40:
            raise PeFormatError("文件过小，不足以容纳 DOS 头")
        if buf[:2] != b"MZ":
            raise PeFormatError("缺少 DOS 魔数 'MZ'")
        self.dos_magic = buf[:2]
        self.e_lfanew = _u32(buf, 0x3C)
        if self.e_lfanew + 24 > len(buf):
            raise PeFormatError(f"e_lfanew={self.e_lfanew:#x} 越界")
        if buf[self.e_lfanew:self.e_lfanew + 4] != b"PE\x00\x00":
            raise PeFormatError("缺少 NT 签名 'PE\\0\\0'")

        coff = self.e_lfanew + 4
        self.machine = _u16(buf, coff)
        self.number_of_sections = _u16(buf, coff + 2)
        self.time_date_stamp = _u32(buf, coff + 4)
        self.pointer_to_symbol_table = _u32(buf, coff + 8)
        self.number_of_symbols = _u32(buf, coff + 12)
        self.size_of_optional_header = _u16(buf, coff + 16)
        self.characteristics = _u16(buf, coff + 18)

        opt = coff + 20
        self.optional_header_offset = opt
        if self.size_of_optional_header == 0:
            # 目标文件（OBJ）允许没有可选头；此时没有节表 RVA 语义。
            self.magic = 0
            self.subsystem = 0
            self.dll_characteristics = 0
            return
        self.magic = _u16(buf, opt)
        self.is_pe32_plus = self.magic == 0x20B
        pe32 = self.magic == 0x10B
        if not (self.is_pe32_plus or pe32):
            raise PeFormatError(f"未知可选头魔数 {self.magic:#x}")

        self.major_linker_version = _u8(buf, opt + 2)
        self.minor_linker_version = _u8(buf, opt + 3)
        self.size_of_code = _u32(buf, opt + 4)
        self.size_of_initialized_data = _u32(buf, opt + 8)
        self.size_of_uninitialized_data = _u32(buf, opt + 12)
        self.address_of_entry_point = _u32(buf, opt + 16)
        self.base_of_code = _u32(buf, opt + 20)
        if pe32:
            self.base_of_data = _u32(buf, opt + 24)
            self.image_base = _u32(buf, opt + 28)
            self.section_alignment = _u32(buf, opt + 32)
            self.file_alignment = _u32(buf, opt + 36)
            dir_off = opt + 96
            self.dll_characteristics = _u16(buf, opt + 70)
        else:
            self.base_of_data = 0
            self.image_base = _u64(buf, opt + 24)
            self.section_alignment = _u32(buf, opt + 32)
            self.file_alignment = _u32(buf, opt + 36)
            dir_off = opt + 112
            self.dll_characteristics = _u16(buf, opt + 70)

        self.subsystem = _u16(buf, opt + 68)
        self.size_of_image = _u32(buf, opt + 56)
        self.size_of_headers = _u32(buf, opt + 60)
        self.checksum = _u32(buf, opt + 64)

        # 数据目录
        ndd_off = opt + (92 if pe32 else 108)
        ndd = _u32(buf, ndd_off) if opt + ndd_off - opt + 4 <= len(buf) else 16
        if ndd > 64:  # 防御：异常大的数量视为损坏
            ndd = 16
        for i in range(ndd):
            o = dir_off + 8 * i
            if o + 8 > len(buf):
                break
            self.data_directories.append((_u32(buf, o), _u32(buf, o + 4)))

        # 节表
        sec_off = opt + self.size_of_optional_header
        for i in range(self.number_of_sections):
            o = sec_off + 40 * i
            if o + 40 > len(buf):
                raise PeFormatError(f"节表第 {i} 项越界")
            name = buf[o:o + 8].rstrip(b"\x00").decode("latin1")
            virtual_size = _u32(buf, o + 8)
            virtual_address = _u32(buf, o + 12)
            raw_size = _u32(buf, o + 16)
            raw_offset = _u32(buf, o + 20)
            chars = _u32(buf, o + 36)
            self.sections.append(Section(i, name, virtual_size,
                                         virtual_address, raw_size,
                                         raw_offset, chars))
        self.section_table_offset = sec_off

    # ---- 地址换算 ----
    def rva_to_offset(self, rva: int) -> int | None:
        for s in self.sections:
            if s.contains_rva(rva):
                delta = rva - s.virtual_address
                if delta < s.raw_size:
                    return s.raw_offset + delta
                return None  # 落在虚拟填充区，无文件映射
        return None

    def offset_to_rva(self, offset: int) -> int | None:
        for s in self.sections:
            if s.raw_offset <= offset < s.span_end:
                return s.virtual_address + (offset - s.raw_offset)
        return None

    def section_by_name(self, name: str) -> Section | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def section_of_rva(self, rva: int) -> Section | None:
        for s in self.sections:
            if s.contains_rva(rva):
                return s
        return None

    def read_rva(self, rva: int, size: int) -> bytes:
        off = self.rva_to_offset(rva)
        if off is None:
            return b""
        return self.buf[off:off + size]

    # ---- 数据目录访问 ----
    def directory(self, index: int) -> tuple[int, int]:
        if 0 <= index < len(self.data_directories):
            return self.data_directories[index]
        return (0, 0)

    # ---- 导出 ----
    def exports(self) -> list[dict[str, Any]]:
        rva, size = self.directory(0)
        if not rva or not size:
            return []
        off = self.rva_to_offset(rva)
        if off is None:
            return []
        buf = self.buf
        try:
            characteristics = _u32(buf, off + 0)
            time_date = _u32(buf, off + 4)
            major = _u16(buf, off + 8)
            minor = _u16(buf, off + 10)
            name_rva = _u32(buf, off + 12)
            base = _u32(buf, off + 16)
            nfunc = _u32(buf, off + 20)
            nname = _u32(buf, off + 24)
            afunc = _u32(buf, off + 28)
            aname = _u32(buf, off + 32)
            aord = _u32(buf, off + 36)
        except struct.error:
            return []

        dll_name = _cstr(buf, self.rva_to_offset(name_rva) or 0)
        # ordinal -> 函数 RVA
        func_off = self.rva_to_offset(afunc)
        funcs: list[int] = []
        if func_off is not None:
            for i in range(min(nfunc, 1 << 20)):
                p = func_off + 4 * i
                if p + 4 > len(buf):
                    break
                funcs.append(_u32(buf, p))

        # 名称表：每个 u32 指向 IMAGE_EXPORT_DIRECTORY.Name 字符串
        names: dict[int, str] = {}
        name_off = self.rva_to_offset(aname)
        ord_off = self.rva_to_offset(aord)
        if name_off is not None and ord_off is not None:
            for i in range(min(nname, 1 << 20)):
                pn = name_off + 4 * i
                po = ord_off + 2 * i
                if pn + 4 > len(buf) or po + 2 > len(buf):
                    break
                str_off = self.rva_to_offset(_u32(buf, pn))
                ordi = _u16(buf, po)
                if str_off is None:
                    continue
                names[ordi] = _cstr(buf, str_off)

        out: list[dict[str, Any]] = []
        for idx, frva in enumerate(funcs):
            # 前向导出：RVA 落在导出目录自身范围内
            forwarder = None
            if rva <= frva < rva + size:
                foff = self.rva_to_offset(frva)
                if foff is not None:
                    forwarder = _cstr(buf, foff)
            out.append({
                "index": idx,
                "ordinal": base + idx,
                "rva": frva & 0xFFFFFFFF,
                "name": names.get(idx),
                "forwarder": forwarder,
            })
        return out

    def export_meta(self) -> dict[str, Any]:
        rva, size = self.directory(0)
        if not rva or not size:
            return {}
        off = self.rva_to_offset(rva)
        if off is None:
            return {}
        buf = self.buf
        return {
            "dll_name": _cstr(buf, self.rva_to_offset(_u32(buf, off + 12)) or 0),
            "ordinal_base": _u32(buf, off + 16),
            "number_of_functions": _u32(buf, off + 20),
            "number_of_names": _u32(buf, off + 24),
        }

    # ---- 导入 ----
    def imports(self) -> list[dict[str, Any]]:
        rva, size = self.directory(1)
        if not rva or not size:
            return []
        buf = self.buf
        ptr_size = 8 if self.is_pe32_plus else 4
        ordinal_flag = (1 << 63) if self.is_pe32_plus else (1 << 31)
        out: list[dict[str, Any]] = []
        off = self.rva_to_offset(rva)
        if off is None:
            return []
        index = 0
        while True:
            o = off + 20 * index
            if o + 20 > len(buf):
                break
            try:
                oft, timestamp, forwarder, name_rva, first_thunk = struct.unpack_from(
                    "<IIIII", buf, o)
            except struct.error:
                break
            if not any((oft, timestamp, forwarder, name_rva, first_thunk)):
                break  # 全零项 = 结束
            noff = self.rva_to_offset(name_rva)
            dll = _cstr(buf, noff) if noff is not None else ""
            lookup_rva = oft or first_thunk
            entries: list[dict[str, Any]] = []
            loff = self.rva_to_offset(lookup_rva)
            if loff is not None:
                j = 0
                while j < (1 << 20):
                    p = loff + ptr_size * j
                    if p + ptr_size > len(buf):
                        break
                    value = (_u64(buf, p) if self.is_pe32_plus
                             else _u32(buf, p))
                    if value == 0:
                        break
                    if value & ordinal_flag:
                        entries.append({
                            "kind": "ordinal",
                            "ordinal": value & 0xFFFF,
                            "hint": None,
                            "name": None,
                            "iat_rva": first_thunk + ptr_size * j,
                        })
                    else:
                        # IMAGE_IMPORT_BY_NAME: u16 hint + ASCIIZ name
                        hoff = self.rva_to_offset(value)
                        hint = None
                        fname = None
                        if hoff is not None:
                            hint = _u16(buf, hoff)
                            fname = _cstr(buf, hoff + 2)
                        entries.append({
                            "kind": "name",
                            "ordinal": None,
                            "hint": hint,
                            "name": fname,
                            "iat_rva": first_thunk + ptr_size * j,
                        })
                    j += 1
            out.append({
                "index": index,
                "dll": dll,
                "original_first_thunk": oft,
                "first_thunk": first_thunk,
                "entries": entries,
            })
            index += 1
        return out

    # ---- 重定位（手工语义） ----
    def relocations(self) -> list[dict[str, Any]]:
        rva, size = self.directory(5)
        return self.relocations_from(rva, size)

    def relocations_from(self, rva: int, size: int) -> list[dict[str, Any]]:
        """手工解析 .reloc。

        块结构：u32 PageRVA + u32 SizeOfBlock + (SizeOfBlock-8)/2 × u16。
        条目：高 4 位类型、低 12 位页内偏移，目标 RVA = PageRVA + 低 12 位。
        """
        buf = self.buf
        if not rva or not size:
            return []
        off = self.rva_to_offset(rva)
        if off is None:
            return []
        blocks: list[dict[str, Any]] = []
        cur = off
        end = off + size
        while cur + 8 <= end and cur + 8 <= len(buf):
            page_rva, block_size = struct.unpack_from("<II", buf, cur)
            if block_size < 8:
                # 损坏或结束哨兵；显式记录后停止，避免死循环
                blocks.append({
                    "index": len(blocks),
                    "file_offset": cur,
                    "page_rva": page_rva,
                    "size_of_block": block_size,
                    "entries": [],
                    "truncated": True,
                })
                break
            if cur + block_size > end:
                # 块声明长度越过目录范围：按可用范围截断处理
                block_size = end - cur
            n = (block_size - 8) // 2
            entries: list[dict[str, Any]] = []
            for i in range(n):
                p = cur + 8 + 2 * i
                if p + 2 > len(buf):
                    break
                raw = _u16(buf, p)
                etype = raw >> 12
                page_off = raw & 0x0FFF
                entries.append({
                    "entry_index": i,
                    "file_offset": p,
                    "raw": raw,
                    "type": etype,
                    "type_name": RELOC_TYPE_NAMES.get(etype, f"TYPE_{etype}"),
                    "page_offset": page_off,
                    # 目标 RVA —— 手工计算，不使用任何库的 rva 语义
                    "target_rva": page_rva + page_off,
                })
            blocks.append({
                "index": len(blocks),
                "file_offset": cur,
                "page_rva": page_rva,
                "size_of_block": block_size,
                "entries": entries,
                "truncated": False,
            })
            cur += block_size
        return blocks

    # ---- 异常表 ----
    def pdata_entries(self) -> list[tuple[int, int, int]]:
        """返回 [(StartRVA, EndRVA, UnwindInfoRVA), ...]；仅 PE32+ 有该表。"""
        rva, size = self.directory(3)
        if not rva or not size:
            return []
        off = self.rva_to_offset(rva)
        if off is None:
            return []
        buf = self.buf
        count = size // 12
        out: list[tuple[int, int, int]] = []
        for i in range(count):
            p = off + 12 * i
            if p + 12 > len(buf):
                break
            out.append(struct.unpack_from("<III", buf, p))
        return out


# --------------------------------------------------------------------------
# pefile 交叉印证层（可选）
# --------------------------------------------------------------------------


def pefile_report(path: str) -> dict[str, Any] | None:
    """用 pefile 读取头部/节表/数据目录等，用于与手工解析结果对照。

    任一步失败都返回 None（说明只有手工路径可用），**不抛异常**。
    """
    if not HAVE_PEFILE:
        return None
    try:
        pe = pefile.PE(path, fast_load=True)
    except Exception:
        return None
    try:
        info: dict[str, Any] = {
            "machine": hex(pe.FILE_HEADER.Machine),
            "number_of_sections": pe.FILE_HEADER.NumberOfSections,
            "time_date_stamp": pe.FILE_HEADER.TimeDateStamp,
            "characteristics": hex(pe.FILE_HEADER.Characteristics),
            "is_pe32_plus": bool(pe.PE_TYPE == 0x20B or
                                 getattr(pe.OPTIONAL_HEADER, "Magic", 0) == 0x20B),
            "image_base": getattr(pe.OPTIONAL_HEADER, "ImageBase", 0),
            "entry_point": getattr(pe.OPTIONAL_HEADER, "AddressOfEntryPoint", 0),
            "subsystem": pe.OPTIONAL_HEADER.Subsystem,
        }
        dirs = []
        for i, d in enumerate(getattr(pe.OPTIONAL_HEADER, "DATA_DIRECTORY", []) or []):
            dirs.append((i, getattr(d, "VirtualAddress", 0), getattr(d, "Size", 0)))
        info["data_directories"] = dirs
        info["sections"] = [
            {
                "name": s.Name.rstrip(b"\x00").decode("latin1"),
                "virtual_address": s.VirtualAddress,
                "virtual_size": s.Misc_VirtualSize,
                "raw_offset": s.PointerToRawData,
                "raw_size": s.SizeOfRawData,
                "characteristics": hex(s.Characteristics),
            }
            for s in pe.sections
        ]
        return info
    except Exception:
        return None
    finally:
        try:
            pe.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# 输出helper
# --------------------------------------------------------------------------


def human_bytes(n: int) -> str:
    return f"{n} B ({n:#x})"


def print_header_summary(pe: PeFile, path: str, size: int) -> None:
    print("=" * 78)
    print("文件信息")
    print("=" * 78)
    print(f"  路径            : {path}")
    print(f"  文件大小        : {human_bytes(size)}")
    print(f"  DOS 魔数        : {pe.dos_magic!r}  e_lfanew = {pe.e_lfanew:#x}")
    nt_sig = "PE\\0\\0" if pe.e_lfanew else "(缺失)"
    print(f"  NT 签名         : {nt_sig}")
    print(f"  格式            : {'PE32+ (0x20B)' if pe.is_pe32_plus else 'PE32 (0x10B)'}"
          f"  magic={pe.magic:#x}")
    machine = IMAGE_FILE_MACHINE.get(pe.machine, "unknown")
    print(f"  Machine         : {pe.machine:#06x} ({machine})")
    print(f"  节数量          : {pe.number_of_sections}")
    print(f"  TimeDateStamp   : {pe.time_date_stamp:#010x} "
          f"({pe.time_date_stamp})")
    print(f"  符号表指针/数量 : {pe.pointer_to_symbol_table:#x} / "
          f"{pe.number_of_symbols}")
    print(f"  可选头大小      : {pe.size_of_optional_header:#x}")
    print(f"  Characteristics : {pe.characteristics:#06x}")
    print(f"  链接器版本      : {pe.major_linker_version}.{pe.minor_linker_version}")
    print(f"  ImageBase       : {pe.image_base:#018x}")
    print(f"  EntryPoint (RVA): {pe.address_of_entry_point:#010x} "
          f"=> VA {pe.image_base + pe.address_of_entry_point:#018x}")
    print(f"  SectionAlign    : {pe.section_alignment:#x}")
    print(f"  FileAlign       : {pe.file_alignment:#x}")
    print(f"  SizeOfImage     : {pe.size_of_image:#x}")
    print(f"  SizeOfHeaders   : {pe.size_of_headers:#x}")
    print(f"  Checksum        : {pe.checksum:#010x}")
    subsystem = IMAGE_SUBSYSTEM.get(pe.subsystem, "unknown")
    print(f"  Subsystem       : {pe.subsystem} ({subsystem})")
    print(f"  DllCharacteristics: {pe.dll_characteristics:#06x}")
    print(f"  代码量/初始化数据/未初始化数据: {pe.size_of_code:#x} / "
          f"{pe.size_of_initialized_data:#x} / {pe.size_of_uninitialized_data:#x}")


def print_sections(pe: PeFile) -> None:
    print()
    print("=" * 78)
    print("节表")
    print("=" * 78)
    print(f"  {'#':>2}  {'name':<10} {'VA':>10} {'VSize':>10} {'RawOff':>10} "
          f"{'RawSize':>10}  characteristics")
    for s in pe.sections:
        print(f"  {s.index:>2}  {s.name:<10} {s.virtual_address:#010x} "
              f"{s.virtual_size:#010x} {s.raw_offset:#010x} {s.raw_size:#010x}  "
              f"{s.characteristics:#010x} {','.join(s.char_flags())}")


def print_data_directories(pe: PeFile) -> None:
    print()
    print("=" * 78)
    print("数据目录")
    print("=" * 78)
    print(f"  {'#':>2}  {'名称':<16} {'RVA':>10} {'Size':>10}  映射文件偏移")
    for i, (rva, size) in enumerate(pe.data_directories):
        name = DATA_DIRECTORY_NAMES[i] if i < len(DATA_DIRECTORY_NAMES) else f"DIR{i}"
        if not rva and not size:
            print(f"  {i:>2}  {name:<16} {'-':>10} {'-':>10}  (空)")
            continue
        off = pe.rva_to_offset(rva)
        mapped = f"{off:#x}" if off is not None else "(未映射)"
        print(f"  {i:>2}  {name:<16} {rva:#010x} {size:#010x}  {mapped}")


def print_exports(pe: PeFile) -> None:
    print()
    print("=" * 78)
    print("导出表")
    print("=" * 78)
    rva, size = pe.directory(0)
    if not rva or not size:
        print("  (无导出目录)")
        return
    meta = pe.export_meta()
    if meta:
        print(f"  DLL 名称        : {meta.get('dll_name')!r}")
        print(f"  序号基值        : {meta.get('ordinal_base')}")
        print(f"  函数数 / 名称数 : {meta.get('number_of_functions')} / "
              f"{meta.get('number_of_names')}")
    exps = pe.exports()
    print(f"  导出条目数      : {len(exps)}")
    print()
    print(f"  {'idx':>4} {'ord':>5}  {'RVA':>10}  {'VA':>18}  name")
    for e in exps:
        va = pe.image_base + e["rva"]
        nm = e["name"] or "(仅序号)"
        fwd = f"  -> {e['forwarder']}" if e.get("forwarder") else ""
        print(f"  {e['index']:>4} {e['ordinal']:>5}  {e['rva']:#010x}  "
              f"{va:#018x}  {nm}{fwd}")


def print_imports(pe: PeFile) -> None:
    print()
    print("=" * 78)
    print("导入表")
    print("=" * 78)
    rva, size = pe.directory(1)
    if not rva or not size:
        print("  (无导入目录)")
        return
    dlls = pe.imports()
    total = sum(len(d["entries"]) for d in dlls)
    ordinals = sum(1 for d in dlls for e in d["entries"]
                   if e["kind"] == "ordinal")
    print(f"  导入 DLL 数     : {len(dlls)}")
    print(f"  导入条目总数    : {total}  (其中序号导入 {ordinals})")
    for d in dlls:
        print()
        print(f"  [{d['index']:>2}] {d['dll']}  —— {len(d['entries'])} 项"
              f"  (OriginalFirstThunk={d['original_first_thunk']:#x},"
              f" FirstThunk={d['first_thunk']:#x})")
        for e in d["entries"]:
            if e["kind"] == "ordinal":
                print(f"        IAT {e['iat_rva']:#010x}  "
                      f"ordinal #{e['ordinal']} (按序号导入)")
            else:
                hint = f"{e['hint']:>4}" if e["hint"] is not None else "   ?"
                print(f"        IAT {e['iat_rva']:#010x}  hint {hint}  "
                      f"{e['name']}")


def print_pdata(pe: PeFile, limit: int | None) -> int:
    entries = pe.pdata_entries()
    print()
    print("=" * 78)
    print("异常表 (.pdata / RUNTIME_FUNCTION)")
    print("=" * 78)
    rva, size = pe.directory(3)
    if not entries:
        print("  (无异常表)")
        return 0
    print(f"  目录 RVA {rva:#010x}  大小 {size:#x}  条目数 {len(entries)} "
          f"(每项 12 字节)")
    print()
    print(f"  {'idx':>5}  {'StartRVA':>10}  {'EndRVA':>10}  {'长度':>7}  "
          f"{'UnwindRVA':>10}  所属节")
    shown = entries if limit is None else entries[:limit]
    for i, (start, end, unwind) in enumerate(shown):
        sec = pe.section_of_rva(start)
        secname = sec.name if sec else "<none>"
        print(f"  {i:>5}  {start:#010x}  {end:#010x}  {end - start:>7}  "
              f"{unwind:#010x}  {secname}")
    if limit is not None and len(entries) > limit:
        print(f"  ... 其余 {len(entries) - limit} 项已省略（用 --pdata-limit 0 显示全部）")
    return len(entries)


def print_reloc(pe: PeFile, rng: tuple[int, int] | None,
                limit: int | None) -> tuple[int, int]:
    print()
    print("=" * 78)
    print(".reloc 重定位块（手工解析）")
    print("=" * 78)
    rva, size = pe.directory(5)
    if not rva or not size:
        # 回退：某些文件的 .reloc 未登记到目录；按节名找
        sec = pe.section_by_name(".reloc")
        if sec is None:
            print("  (无重定位目录，且未找到 .reloc 节)")
            return 0, 0
        rva, size = sec.virtual_address, sec.virtual_size
        print(f"  (目录项为空，改用 .reloc 节: RVA {rva:#x} 大小 {size:#x})")

    blocks = pe.relocations_from(rva, size)
    total_entries = sum(len(b["entries"]) for b in blocks)
    hist: collections.Counter[int] = collections.Counter()
    for b in blocks:
        for e in b["entries"]:
            hist[e["type"]] += 1

    print(f"  目录 RVA {rva:#010x}  大小 {size:#x}")
    print(f"  块数            : {len(blocks)}")
    print(f"  条目总数        : {total_entries}")
    if hist:
        print(f"  类型直方图      :")
        for t in sorted(hist):
            width = RELOC_TYPE_WIDTH.get(t, 4)
            print(f"      type {t:>2} ({RELOC_TYPE_NAMES.get(t, 'UNKNOWN'):<16}) "
                  f"宽度 {width} 字节  条目 {hist[t]}")
    real = sum(v for k, v in hist.items() if k != 0)
    print(f"  非填充条目      : {real}  (type 0 = ABSOLUTE 为填充，不含偏移语义)")

    # 按 RVA 区间过滤
    if rng is not None:
        lo, hi = rng
        matched: list[tuple[int, dict[str, Any]]] = []
        for b in blocks:
            for e in b["entries"]:
                if e["type"] == 0:
                    continue
                t = e["target_rva"]
                width = RELOC_TYPE_WIDTH.get(e["type"], 4)
                # 相交判定：条目覆盖 [t, t+width)
                if t + width > lo and t < hi:
                    matched.append((b["index"], e))
        print()
        print(f"  区间过滤 [{lo:#010x}, {hi:#010x}) —— 命中 {len(matched)} 条")
        print(f"  {'block':>5} {'entry':>5}  {'目标 RVA':>10}  {'type':>4}  "
              f"{'页内偏移':>8}  条目文件偏移")
        shown = matched if limit is None else matched[:limit]
        for bidx, e in shown:
            print(f"  {bidx:>5} {e['entry_index']:>5}  {e['target_rva']:#010x}  "
                  f"{e['type']:>4}  {e['page_offset']:#06x}  "
                  f"{e['file_offset']:#010x}")
        if limit is not None and len(matched) > limit:
            print(f"  ... 其余 {len(matched) - limit} 条已省略")

    print()
    print("  块明细：")
    print(f"  {'#':>3}  {'块文件偏移':>12}  {'PageRVA':>10}  {'SizeOfBlock':>11}  "
          f"{'条目数':>6}  目标 RVA 范围")
    shown_blocks = blocks if limit is None else blocks[:limit]
    for b in shown_blocks:
        ents = b["entries"]
        if ents and any(e["type"] != 0 or True for e in ents):
            lo = min(e["target_rva"] for e in ents)
            hi = max(e["target_rva"] for e in ents)
            rngtxt = f"{lo:#010x} .. {hi:#010x}"
        else:
            rngtxt = "-"
        flag = "  [截断]" if b.get("truncated") else ""
        print(f"  {b['index']:>3}  {b['file_offset']:>12}  {b['page_rva']:#010x}  "
              f"{b['size_of_block']:>11}  {len(ents):>6}  {rngtxt}{flag}")
    if limit is not None and len(blocks) > limit:
        print(f"  ... 其余 {len(blocks) - limit} 个块已省略")
    return len(blocks), total_entries


def print_hex_dump(pe: PeFile, secname: str, offset: int, length: int,
                   base_note: str = "节内相对偏移") -> bytes:
    sec = pe.section_by_name(secname)
    if sec is None:
        names = ", ".join(s.name for s in pe.sections)
        raise PeFormatError(f"未找到节 {secname!r}；现有节：{names}")
    start = sec.raw_offset + offset
    if offset < 0 or offset >= max(sec.raw_size, 1):
        raise PeFormatError(
            f"{base_note} {offset:#x} 超出节 {secname} 的原始大小 {sec.raw_size:#x}")
    avail = min(length, sec.raw_size - offset, len(pe.buf) - start)
    if avail < 0:
        avail = 0
    data = pe.buf[start:start + avail]
    rva = sec.virtual_address + offset
    va = pe.image_base + rva
    print("=" * 78)
    print(f"十六进制转储：节 {secname} + {offset:#x}")
    print("=" * 78)
    print(f"  节原始范围      : {sec.raw_offset:#x} .. {sec.span_end:#x}")
    print(f"  起始文件偏移    : {start:#x}")
    print(f"  起始 RVA        : {rva:#010x}")
    print(f"  起始 VA         : {va:#018x}")
    print(f"  请求/实际长度   : {length:#x} / {avail:#x}")
    print()
    # 16 字节一行，附带可打印字符列
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hexpart = " ".join(f"{b:02X}" for b in chunk)
        hexpart = f"{hexpart:<47}"
        text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        print(f"  {start + i:#010x}  {hexpart}  |{text}|")
    return data


def print_pefile_crosscheck(path: str, pe: PeFile) -> None:
    print()
    print("=" * 78)
    print("pefile 交叉印证")
    print("=" * 78)
    if not HAVE_PEFILE:
        print("  未安装 pefile —— 本次全部结果均来自内置 struct 手工解析。")
        print("  (pip install pefile 可获得交叉印证；工具在无该依赖时功能完整。)")
        return
    info = pefile_report(path)
    if info is None:
        print("  pefile 已安装但读取失败 —— 回退结果仍由手工解析给出。")
        return
    print(f"  pefile 版本     : {getattr(pefile, '__version__', 'unknown')}")
    print(f"  Machine         : {info['machine']}  "
          f"(手工: {pe.machine:#06x})")
    print(f"  节数量          : {info['number_of_sections']}  "
          f"(手工: {pe.number_of_sections})")
    print(f"  PE32+           : {info['is_pe32_plus']}  (手工: {pe.is_pe32_plus})")
    print(f"  ImageBase       : {info['image_base']:#x}  (手工: {pe.image_base:#x})")
    print(f"  EntryPoint      : {info['entry_point']:#x}  "
          f"(手工: {pe.address_of_entry_point:#x})")
    mism = []
    for a, b in zip(info["sections"], pe.sections):
        if (a["virtual_address"] != b.virtual_address or
                a["raw_offset"] != b.raw_offset or
                a["virtual_size"] != b.virtual_size or
                a["raw_size"] != b.raw_size):
            mism.append(a["name"])
    print(f"  节表一致性      : "
          f"{'全部一致' if not mism else '不一致: ' + ','.join(mism)}")


# --------------------------------------------------------------------------
# 区间解析
# --------------------------------------------------------------------------


def parse_range(text: str) -> tuple[int, int]:
    """解析 START:END，两端均接受 0x 前缀或十进制。"""
    if ":" not in text:
        raise argparse.ArgumentTypeError("区间格式应为 START:END，例如 0x1000:0x2000")
    a, b = text.split(":", 1)
    try:
        start = int(a.strip(), 0)
        end = int(b.strip(), 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析区间 {text!r}: {exc}") from exc
    if start < 0 or end < 0:
        raise argparse.ArgumentTypeError("区间端点不能为负")
    if end <= start:
        raise argparse.ArgumentTypeError("区间终点必须大于起点")
    return start, end


def parse_int(text: str) -> int:
    try:
        return int(text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析整数 {text!r}") from exc


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("file", help="待解析的 PE 文件路径（只读）")
    p.add_argument("--no-pefile", action="store_true",
                   help="即使已安装 pefile 也强制使用内置手工解析路径")
    p.add_argument("--limit", type=int, default=64,
                   help="明细行最大打印条数（默认 64；0 表示不限制）")


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "示例（路径均为占位符，请替换为本地实际文件）：\n"
        "  python tools/pe_parser.py info   <target.dll>\n"
        "  python tools/pe_parser.py reloc  <target.dll> --range 0x1000:0x2000\n"
        "  python tools/pe_parser.py pdata  <target.dll>\n"
        "  python tools/pe_parser.py dump   <target.dll> --section .text --hex 0x100 --len 64\n"
    )
    ap = argparse.ArgumentParser(
        prog="pe_parser.py",
        description="通用只读 PE32/PE32+ 结构解析器：头部、节表、数据目录、"
                    "导入导出、.reloc（手工）、.pdata、按节十六进制转储。",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version="pe_parser.py 1.0.0")
    sub = ap.add_subparsers(dest="command", metavar="<子命令>")

    # info
    p_info = sub.add_parser("info", help="打印头部/节表/数据目录/导入/导出概览")
    add_common(p_info)
    p_info.add_argument("--no-imports", action="store_true",
                        help="跳过导入表明细")

    # reloc
    p_reloc = sub.add_parser("reloc", help="手工解析 .reloc 块，打印类型直方图")
    add_common(p_reloc)
    p_reloc.add_argument("--range", dest="rng", type=parse_range, default=None,
                         metavar="START:END",
                         help="只显示目标 RVA 落入该区间的条目（十六进制或十进制）")
    p_reloc.add_argument("--entries", action="store_true",
                         help="即使未指定 --range 也逐条列出全部重定位条目")

    # pdata
    p_pdata = sub.add_parser("pdata", help="转储异常表 (StartRVA, EndRVA, UnwindRVA)")
    add_common(p_pdata)
    p_pdata.add_argument("--range", dest="rng", type=parse_range, default=None,
                         metavar="START:END",
                         help="只显示 StartRVA 落入该区间的条目")
    p_pdata.add_argument("--pdata-limit", type=int, default=64,
                         help="最多打印的 .pdata 条目数（默认 64；0 = 不限制）")

    # dump
    p_dump = sub.add_parser("dump", help="按节名 + 节内文件偏移做十六进制转储")
    add_common(p_dump)
    p_dump.add_argument("--section", required=True, help="节名，例如 .text")
    p_dump.add_argument("--hex", dest="hex_off", type=parse_int, required=True,
                        metavar="OFFSET",
                        help="节内相对文件偏移（十六进制或十进制）")
    p_dump.add_argument("--len", dest="length", type=parse_int, default=256,
                        metavar="N", help="转储字节数（默认 256）")
    p_dump.add_argument("--hex-out", default=None, metavar="PATH",
                        help="可选：把转储的原始字节写入该文件（唯一允许的写出）")

    return ap


def cmd_info(args: argparse.Namespace, pe: PeFile, size: int) -> int:
    print_header_summary(pe, args.file, size)
    print_sections(pe)
    print_data_directories(pe)
    print_exports(pe)
    if not args.no_imports:
        print_imports(pe)
    print_pefile_crosscheck(args.file, pe)
    return 0


def cmd_reloc(args: argparse.Namespace, pe: PeFile, size: int) -> int:
    limit = None if args.limit == 0 else args.limit
    if args.rng is None and args.entries:
        # 未指定区间但要求逐条：退化为全量区间
        args.rng = (0, 0xFFFFFFFF)
    blocks, entries = print_reloc(pe, args.rng, limit)
    print()
    print(f"汇总: 块数={blocks} 条目总数={entries}")
    return 0


def cmd_pdata(args: argparse.Namespace, pe: PeFile, size: int) -> int:
    entries = pe.pdata_entries()
    if args.rng is not None:
        lo, hi = args.rng
        entries = [e for e in entries if lo <= e[0] < hi]
        print("=" * 78)
        print("异常表 (.pdata) —— 区间过滤")
        print("=" * 78)
        print(f"  区间 [{lo:#010x}, {hi:#010x}) 命中 {len(entries)} 条")
        print()
        print(f"  {'idx':>5}  {'StartRVA':>10}  {'EndRVA':>10}  {'长度':>7}  "
              f"{'UnwindRVA':>10}  所属节")
        shown = entries if args.pdata_limit == 0 else entries[:args.pdata_limit]
        for i, (start, end, unwind) in enumerate(shown):
            sec = pe.section_of_rva(start)
            print(f"  {i:>5}  {start:#010x}  {end:#010x}  {end - start:>7}  "
                  f"{unwind:#010x}  {sec.name if sec else '<none>'}")
        print()
        print(f"汇总: .pdata 条目数={len(entries)}")
        return 0
    limit = None if args.pdata_limit == 0 else args.pdata_limit
    count = print_pdata(pe, limit)
    print()
    print(f"汇总: .pdata 条目数={count}")
    return 0


def cmd_dump(args: argparse.Namespace, pe: PeFile, size: int) -> int:
    data = print_hex_dump(pe, args.section, args.hex_off, args.length)
    if args.hex_out:
        with open(args.hex_out, "wb") as fh:
            fh.write(data)
        print()
        print(f"  已写出 {len(data)} 字节到 {args.hex_out}")
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------


def main(argv: Iterable[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(list(argv) if argv is not None else None)
    if not args.command:
        ap.print_help()
        return 1

    try:
        with open(args.file, "rb") as fh:
            buf = fh.read()
    except OSError as exc:
        print(f"错误: 无法读取文件 {args.file!r}: {exc}", file=sys.stderr)
        return 2

    try:
        pe = PeFile(buf, args.file)
    except PeFormatError as exc:
        print(f"错误: PE 解析失败: {exc}", file=sys.stderr)
        return 1

    if args.no_pefile:
        global HAVE_PEFILE
        HAVE_PEFILE = False

    try:
        if args.command == "info":
            return cmd_info(args, pe, len(buf))
        if args.command == "reloc":
            return cmd_reloc(args, pe, len(buf))
        if args.command == "pdata":
            return cmd_pdata(args, pe, len(buf))
        if args.command == "dump":
            return cmd_dump(args, pe, len(buf))
    except PeFormatError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
