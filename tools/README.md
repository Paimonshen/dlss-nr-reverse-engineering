# 工具说明（tools/）

本目录包含三个**通用、只读、可参数化**的二进制分析工具。它们是从本项目的分析脚本中提炼出的可复用部分：**所有路径均为命令行参数，无硬编码路径**。

## 依赖与环境

- **Python 3.11+**
- `pefile`（PE 解析；若缺失或加 `--no-pefile`，`pe_parser.py` 会使用内置 `struct` 手工解析路径）
- `msgpack`（AMDGPU 内核元数据解码）

```bash
pip install pefile msgpack
```

## 重要约定

- **三个工具均为只读**：除用户通过参数显式指定的输出路径（`--out` / `--hex-out`）外，**不写入任何文件**。
- **每次检索/统计都会输出汇总行**（含命中总数或区间长度 + 熵）—— 因此"命中 0"是一次**显式、可复现**的结果，便于写进结论。
- **不要依赖第三方库的 `rva` 语义**：`pe_parser.py` 的重定位解析为**手工实现**（某些库会把 PageRVA 重复计入，导致目标 RVA 错误）。

---

## 1. `pe_parser.py` — PE 文件解析器

**子命令式接口**：`info` / `reloc` / `pdata` / `dump`。

```bash
# 概览：头部、节表、数据目录、导入表、导出表
python tools/pe_parser.py info <file.dll>
python tools/pe_parser.py info <file.dll> --limit 0        # 不截断明细
python tools/pe_parser.py info <file.dll> --no-pefile      # 强制用内置手工解析

# 重定位表（手工解析）：块数、条目总数、类型直方图
python tools/pe_parser.py reloc <file.dll>
python tools/pe_parser.py reloc <file.dll> --entries                    # 逐条列出
python tools/pe_parser.py reloc <file.dll> --range 0x56170:0x562E0      # 只看落入该 RVA 区间的条目

# 异常表（.pdata）：(StartRVA, EndRVA, UnwindInfoRVA) 三元组
python tools/pe_parser.py pdata <file.dll>
python tools/pe_parser.py pdata <file.dll> --pdata-limit 0              # 全部条目
python tools/pe_parser.py pdata <file.dll> --range 0x18000:0x19000      # 只显示 StartRVA 落入区间者

# 按节名 + 节内文件偏移做十六进制转储
python tools/pe_parser.py dump <file.dll> --section .rdata --hex 0x370 --len 64
python tools/pe_parser.py dump <file.dll> --section .text --hex 0x100 --len 64 --hex-out out/bytes.bin
```

**重定位解析规则（手工实现）**：每个块 = `u32 PageRVA` + `u32 SizeOfBlock` + `(SizeOfBlock-8)/2` 个 `u16` 条目；条目高 4 位为类型，低 12 位为页内偏移；**目标 RVA = PageRVA + 页内偏移**。类型 0（`ABSOLUTE`）为填充项，**不含偏移语义**。

**实测输出（对仓库内 `binaries/dlssnr_amd_pass1.dll`）**：节数量 **12**；导出条目 **17**（DLL 名 `version.dll`）；导入 DLL 数 **10**、条目总数 **194**（序号导入 0）；重定位 **19 块 / 2044 条目**（DIR64 2040 + ABSOLUTE 4）；`.pdata` **1167** 条目（每项 12 字节）。

## 2. `msgpack_extract.py` — AMDGPU 内核元数据提取

从 HIP fat binary（`__CLANG_OFFLOAD_BUNDLE__` 容器）中提取每个 device 目标的 `amdhsa.kernels` 元数据。

```bash
# 概览：每个 bundle 的 triple 与内核数
python tools/msgpack_extract.py <file.dll>

# 只看某个内核（子串匹配）
python tools/msgpack_extract.py <file.dll> --kernel k_swin

# 全量结构化导出
python tools/msgpack_extract.py <file.dll> --json out/kernels.json

# 容器不在文件起始处时手动指定偏移
python tools/msgpack_extract.py <file.dll> --offset 0x78200
```

**解析链（供复现）**：
1. 定位魔数 `__CLANG_OFFLOAD_BUNDLE__`（24 字节），其后为 `uint64` bundle 数；
2. 逐 bundle 读取 `{offset, size, tripleSize}`，triple 与表项交错排列；
3. 对每个 device bundle，在 `bundle+0x238` 处读 ELF note：`namesz`@+0x238、`descsz`@+0x23C、`type`@+0x240、名称 `"AMDGPU"`@+0x244（按 8 字节对齐填充）、**msgpack 文档 @+0x24C，长度为 `descsz`**；
4. 用 `msgpack.unpackb(blob, raw=False, strict_map_key=False)` 解码（键名带前导点，如 `.name`、`.kernarg_segment_size`、`.args`）。

> **注意**：读取 msgpack 文档时**必须以 `descsz` 为上界**，不可越界扫描。

**实测输出（对仓库内 `binaries/dlssnr_amd_pass1.dll`）**：bundle 总数 **9**（1 个 host 占位 + **8** 个设备目标）；每个设备目标 **34 个内核**；triple 依次为 `generic` / `generic` / `gfx1100` / `gfx1101` / `gfx1102` / `gfx1200` / `gfx1201` / `generic`。

## 3. `byte_scanner.py` — 通用字节扫描器

**选项式接口**，可一次传入多个文件。

```bash
# 十六进制模式（?? 为单字节通配）
python tools/byte_scanner.py <file> --hex "48 8D 15 ?? ?? ?? ??"
python tools/byte_scanner.py <file> --hex "44 4C 53 53 4E 52 57 31" --context 16

# ASCII 字符串
python tools/byte_scanner.py <file> --ascii "DLSSNRW1"

# 限定区间（START:END；START: 表示到文件末尾）与命中上限
python tools/byte_scanner.py <file> --hex "FF 25" --range 0x55200:0x72400 --count 50

# 字符串提取（长度 >= MINLEN）
python tools/byte_scanner.py <file> --strings 16

# 字节直方图 + Shannon 熵（bits/byte）
python tools/byte_scanner.py <file> --byte-histogram --range 0x1629: --top 0

# 命中清单写出（唯一允许的写出）
python tools/byte_scanner.py <file> --hex "FF 25" --out out/hits.txt
```

`--range` 支持十六进制（`0x...`）与十进制；`START:` 表示从 `START` 到文件末尾。检索一律输出 `汇总: 命中数=N`。

**实测输出（对仓库内 `binaries/dlssnr_on_amd_weights.bin`）**：
- 魔数 `44 4C 53 53 4E 52 57 31`（`DLSSNRW1`）→ **命中数 = 1**（文件起始处）；
- 载荷区（`--range 0x1629:`，长度 147,683,778 字节）→ **非零桶 256/256**、`0x00` 计数 3,632,122（**2.4594%**）、**Shannon 熵 5.902444 bits/byte**。

---

## 4. `link_audit.py` — Markdown link / anchor / pattern auditor

A general-purpose **read-only** documentation checker. It answers four questions:

1. Do all in-page anchors (`](#heading)`) resolve, using **GitHub's heading-slug rules**?
2. Do all relative file links point at files that exist?
3. Do any configured **leak patterns** appear (internal paths, internal file names, scratch names, …)?
4. Do any configured **banned phrasing** patterns appear, with optional per-file exemptions?

```bash
# audit a tree (default: current directory)
python tools/link_audit.py .

# per-file detail
python tools/link_audit.py . --verbose

# machine-readable
python tools/link_audit.py . --json

# add your own patterns and exempt a file that legitimately defines them
python tools/link_audit.py . --leak '_internal' --banned 'we should probably' \
    --exempt docs/glossary.md

# also scan inside fenced code blocks (default: skipped)
python tools/link_audit.py . --scan-code-blocks
```

**Exit codes**: `0` clean, `1` findings reported, `2` bad invocation. Useful in CI:

```yaml
- run: python tools/link_audit.py . --exempt team-methodology/04-禁用措辞检查的校准.md
```

### Why a tool instead of review

Anchor slugs and relative-depth links are **conventions**: one mistake gets copied into every translation and every sibling page. Machine re-derivation against the target platform's real rules catches that class of error, which manual review reliably misses.

### Design notes

- **Slug rules**: drops the `#` markers, removes emoji/symbol runs (they leave **no** hyphen), removes punctuation, lowercases, collapses whitespace to `-`. This matters: a leading `-` (e.g. `#-title`) is a **broken** anchor.
- **BOM tolerance**: a UTF-8 BOM is stripped before parsing, so the first heading of a file is not silently missed.
- **Code fences are skipped** by default, so sample paths and commands do not create noise. Use `--scan-code-blocks` to include them.
- **Leak patterns are caller-supplied** and replace the built-in defaults when given — so a project can tune them to its own notion of "internal". Note that naive substrings can **false-positive** (e.g. `_work` inside a field name like `max_flat_workgroup_size`); always confirm a hit's context before "fixing" it.
- **Nothing is ever written.** The tool only reads.

---

## 示例：用三个工具复现本项目的主要结论

以下示例使用仓库 `binaries/` 下的文件（需先 `git lfs pull`）。

```bash
# ① 模块形态：12 节 / 17 个 version.dll 导出 / 194 条导入（10 个 DLL）
python tools/pe_parser.py info binaries/dlssnr_amd_pass1.dll --limit 0

# ② 重定位：19 个块、2044 条目（DIR64 2040 + ABSOLUTE 4）
python tools/pe_parser.py reloc binaries/dlssnr_amd_pass1.dll

# ③ 异常表：1167 条目
python tools/pe_parser.py pdata binaries/dlssnr_amd_pass1.dll --pdata-limit 0

# ④ 8 个设备目标 × 34 个内核，各内核的 kernarg 大小与 by_value 参数
python tools/msgpack_extract.py binaries/dlssnr_amd_pass1.dll --json out/kernels.json

# ⑤ 权重容器魔数与载荷分布
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --hex "44 4C 53 53 4E 52 57 31"
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --byte-histogram --range 0x1629:
```

上述结论的完整说明见 [`../docs/03-DLL结构分析.md`](../docs/03-DLL结构分析.md)、[`../docs/04-内核参数规格.md`](../docs/04-内核参数规格.md) 与 [`../docs/05-Intel可行性评估.md`](../docs/05-Intel可行性评估.md)。
