# DLSS NR Reverse Engineering: AMD Module → Cross-GPU Source Recovery

> **In one line**: A thorough static reverse-engineering study of the AMD-side DLSS NR module — the foundation for **recovering a rebuildable source tree** and, from it, a **single cross-GPU codebase** with portable, Intel-accelerated, AMD-accelerated and NVIDIA-reference backends. The study is complete and honest about where it got stuck; **the recovery work is the next stage**.

**Languages / 语言 / 言語 / 언어 / Idioma / Langue:**
[**English**](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

> Translations are community-maintained. If a translation lags behind, **English is authoritative**. Corrections welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🎯 Where This Is Going (project goals)

This repository began as a static analysis — but the analysis was only ever **a means to an end**. The goal we are now working toward, in order:

### Stage 1 — Recover the source: decompile the main program

Move from *understanding bytes* to **a maintainable source tree**: decompile the main program and recover readable, rebuildable source. The kernel parameter specification ([`docs/04`](docs/04-Kernel-Parameter-Spec.md)), the weight container format, and the registration mechanism are the **reference material** that make a faithful reconstruction checkable — which is why they were produced first.

> ⚠️ **Known blocker, stated up front.** Recovering a *usable* source tree requires the **`71 block → kernel` dispatch binding**; without it, the reconstructed scheduling layer is still a stub with a hole in the middle. That binding is currently **unobtainable under the available conditions** (all four avenues closed — see [Help Wanted](#-help-wanted-three-specific-gaps-we-could-not-close) and [`docs/06`](docs/06-Open-Gaps-and-Limits.md)). The decompilation effort will therefore **hit the same gap**. The work is still worth doing — most of the tree can be recovered — but the dispatch layer cannot be closed by decompilation alone.

### Stage 2 — A common-instruction build that runs anywhere

Before optimizing, make it **run at all**. Produce a build that uses **no vendor-proprietary instruction set** — a plain, portable compute path. This establishes correctness, and gives every later backend a **known-good reference to compare against**.

### Stage 3 — Vendor-accelerated builds

With the portable build working, add **vendor-specific acceleration** as separate backends:

| Backend | Target | Acceleration path |
|---|---|---|
| **Intel acceleration** | Intel Arc (Xe) | Xe Matrix Extensions (XMX) |
| **AMD acceleration** | AMD RDNA / CDNA | HIP and matrix cores |
| **NVIDIA original** | NVIDIA | the vendor's own NGX / DLSS implementation |

> ⚠️ **Constraint specific to the NVIDIA path.** This repository **does not contain NVIDIA copyrighted binaries** ([`LEGAL.md`](LEGAL.md) §8), and the publicly available copy of the NVIDIA component has been confirmed to be an **interface layer carrying no analysable kernel metadata** (see [`EXTERNAL_BINARIES.md`](EXTERNAL_BINARIES.md) and [`docs/03`](docs/03-DLL-Structure-Analysis.md)). The NVIDIA path is therefore usable **as a reference for interface behaviour and for cross-checking results** — it is **not** a source of decompilable kernels. Any NVIDIA-side work here stays at the interface / documentation level.

### Stage 4 — One codebase, every GPU

**Integrate the backends into a single source tree** with a backend-selection mechanism, so that **one codebase targets all supported GPUs** — the portable path as the universal fallback, vendor acceleration wherever it is available.

> **In one sentence:** *recover the source → get it running portably → accelerate it per vendor → unify it into one cross-GPU codebase.*

> **Status of these stages.** Stages 2–4 describe the **intended direction, not completed work**. This repository currently contains **analysis and tooling only** — no decompiled source tree and no backend implementation. Everything published here is at the **static byte level**. We would rather state that plainly than imply progress we cannot evidence.

---

## 🙏 Help Wanted: Three Specific Gaps We Could Not Close

This is **not a "finished" study**. We pinned down everything that can be determined statically — **all 34 kernel names, the kernel parameter layouts, the weight container format, and the 194-entry import surface are closed** — but **three gaps** remain impossible to close under the original author's available conditions. We are asking for help explicitly.

### Gap 1: The `71 block → kernel` binding (**most critical**)

**What we need**: which layer (`blockN.layerM`) dispatches to which of the 34 kernels.

**Why we cannot get it** (all four avenues are closed, each with evidence):
1. **DLL static analysis is at its boundary** — the dispatch function's body has no intersection with the kernel-launch functions.
2. **The in-workspace source is a stub** — a re-implementation project exists, but its dispatch function bodies are just `return true;`, and it is **non-isomorphic** to this DLL (only 2 of the 34 kernel names overlap).
3. **The weight file is exhausted** — we searched with **140 byte patterns** over the **entire file including the payload**: `shape` / `dtype` / operator type / `block` index / `kernel` name all returned **0 hits**, and the index region's byte accounting shows **unattributed bytes = 0** (no second table, no hidden metadata region).
4. **Runtime observation is unavailable** — we have no AMD hardware.

**If you can provide**: ① the upstream network definition (`.onnx` / `.safetensors` / export script); ② the upstream pass-side source; ③ or a dump of the actual dispatch sequence from a run on AMD hardware — please open an Issue. **This directly determines whether the porting roadmap can land.**

### Gap 2: Internal field layouts of two parameter structs

**`VarParams` (168 bytes, the user-parameter struct for the 5 `k_swin_var` kernels)** and **`SwinParams` (40 bytes, `k_swin_1h_32_fp8`)** have unresolved internal field composition.

**What we know**: the DLL metadata declares only the **total byte count** of the `by_value` parameter (168 / 40); it carries **no field names and no field boundaries**. We read same-named structs in a re-implementation source tree (92 bytes assuming 64-bit pointers), but those **match neither 168 nor 40** — so the source structs **cannot** be used as the DLL-side layout.

**If you can provide**: the struct definitions from the upstream source, or the `by_value` struct layout rules of the AMD toolchain (including implicit padding) — please open an Issue.

### Gap 3: Confirming Intel Xe / XMX capabilities (a **51-item checklist**)

We built a 34-kernel × operator mapping table, but **the table's "XMX direct support" and "recommended path" columns are marked "needs external documentation" for 34/34 rows — we deliberately gave no capability conclusion**, because we have neither an Intel toolchain nor Xe hardware to verify.

**If you are familiar with Intel Arc / oneAPI / Level Zero / SPIR-V**, please help confirm the specific items (highest priority: XMX primitive support and precision modes for matrix multiply/convolution; whether split-K reduction ordering is constrained by spec; Swin window/shift primitives; and the feasibility boundary of the generic SPIR-V path). The checklist is in [docs/05-Intel可行性评估.md](docs/05-Intel可行性评估.md), chapter 8.

> **Project methodology**: anything we are not certain about is marked "needs external documentation" and **we never speculate**. Those blanks in the table are **deliberate, not omissions**.

---

## What This Project Did

A complete static analysis of the AMD-side `dlssnr_amd_pass1.dll` (a `version.dll` proxy module containing HIP `amdgcn` device code), to answer:

> **Can DLSS NR be recompiled/ported from AMD HIP to Intel Arc (Xe / XMX)?**

### Main results (all reproducible)

| Result | Content | Doc |
|---|---|---|
| **Module shape** | 12 sections; 17 exports, **all `version.dll` API names** (each a 16-byte `FF 25` jump stub); import surface of **194 entries / 10 DLLs**, of which `amdhip64_7.dll` contributes **29** HIP APIs | `docs/03` |
| **Device code** | `.hip_fat` is a clang offload bundle: **9 bundles = 1 host placeholder + 8 device targets**, all `amdgcn-amd-amdhsa`; **34 kernels** per target | `docs/03` |
| **Kernel parameter spec** | For all 34 kernels: `kernarg_segment_size`, `by_value` sizes, full `.args` tables, resource fields; **3 exception kernels** (`k_flag_wait`=16 / `k_align_probe`=8 / `k_flag_set`=12) | `docs/04` |
| **34/34 registration pairing** | Two **8-byte-stride** function-pointer tables + **34 registration calls paired to table slots 34/34** ⇒ "kernel name ↔ wrapper ↔ slot" closed statically | `docs/03` |
| **Weight container decoded** | `8B magic "DLSSNRW1"` + `uint32` entry count (153) + `uint32` index-end offset (0x1629) + 153 variable-length descriptors + contiguous payload (147,683,778 B); **three identities close to 0** | `docs/05` |
| **Intel feasibility** | Kernel classes **A=7 / B=20 / C=7**; resource adaptation (max `group_segment_fixed_size` **64,640 B**, **896 B** under the 64 KiB limit); host side needs **29/194 = 14.9%** replaced; **S0–S7 roadmap with 23 milestones** | `docs/05` |
| **Analysis tools** | Three general-purpose read-only tools: PE parser, AMDGPU msgpack metadata extractor, byte scanner | `tools/` |
| **Collaboration methodology** | Multi-agent workflow, quality gates and acceptance chain, **24 rules derived from real incidents** | `team-methodology/` |

> **Documents are available in both English and Chinese.** See the [document index](docs/README.md). The **Chinese originals are the analysis of record** (written directly against byte evidence); the English files are faithful translations.

### Hard conclusions (including our own corrections)

We **kept the correction trail**, including reversals of our own earlier conclusions:

- ✅ **The 34/34 registration pairing is direct byte evidence** (it was once written as "elimination-based inference").
- ✅ **Weight measurements overturn source-code constants**: the real layer structure is **1×47 / 4×15 (23–29, 40–47) / 5×9 (30–38)**, contradicting the source's "bottleneck uniformly 4 layers" (**inconsistent blocks: 10 = 30–39**); on conflict, **the data file wins**.
- ✅ **The `descsz` delta was corrected from 1,410 to 938** (an arithmetic error), and there are **6 distinct values** after dedup.
- ✅ **The "no upstream source" constraint was overturned**: the workspace **does** contain a pass-side source tree (though non-isomorphic to the DLL); the earlier "it does not exist" was a **false negative** caused by too narrow a search scope.
- ✅ **The `71 block` enum upper bound is undetermined**: that number appears only in documentation transcriptions; there is no corresponding immediate in the DLL.

> One hard rule in our methodology: **any "X does not exist" claim must give range + pattern + hit count.** That is why you will see many reproducible "0 hits" records in the docs — it is deliberate.

---

## Repository Layout

```
.
├── README.md                  This file (English, authoritative)
├── README.zh-CN.md            简体中文
├── README.ja.md               日本語
├── README.ko.md               한국어
├── README.es.md               Español
├── README.fr.md               Français
├── LEGAL.md                   Legal notice (nature of project, rights, takedown)
├── EXTERNAL_BINARIES.md       Third-party binaries (origin / size / SHA256 / license / use)
├── LICENSE                    MIT (original work) + explicit exclusion of third-party binaries
├── CONTRIBUTING.md            Contribution guide (evidence requirements)
├── .gitattributes             Git LFS configuration
├── .gitignore
├── docs/
│   ├── README.md                 Document index (both languages)
│   ├── 01-Project-Background.md    Project goal, analysis target, three environment constraints
│   ├── 02-Analysis-Methodology.md  Method chain and analysis discipline
│   ├── 03-DLL-Structure-Analysis.md Module shape, device code, the two pointer tables, registration
│   ├── 04-Kernel-Parameter-Spec.md Full parameter and resource tables for all 34 kernels
│   ├── 05-Intel-Feasibility-Assessment.md Classification / resources / operators / host replacement / weights / roadmap / checklist
│   ├── 06-Open-Gaps-and-Limits.md  Honest limits: what could not be produced, and why
│   └── 0N-*.md                     Chinese originals of the above (analysis of record)
├── tools/
│   ├── pe_parser.py         PE32/PE32+ parsing (manual .reloc, .pdata)
│   ├── msgpack_extract.py   AMDGPU kernel metadata extraction
│   ├── byte_scanner.py      Generic byte-pattern scan / histogram / entropy / strings
│   └── README.md
├── team-methodology/
│   ├── 01-多智能体协作流程.md
│   ├── 02-质量门禁与验收链.md
│   ├── 03-已确立的定规.md     24 rules, each from a real mistake
│   └── 04-禁用措辞检查的校准.md
├── .github/ISSUE_TEMPLATE/    Issue forms for the three gaps + corrections
├── SECURITY.md                Security policy
└── binaries/                 Third-party binaries (Git LFS)
    ├── dlssnr_amd_pass1.dll
    ├── dlssnr_amd_pass2.dll
    ├── dlssnr_amd_pass3.dll
    ├── dlssnr_on_amd_weights.bin
    └── OptiScaler/
        └── OptiScaler.dll
```

> Note: the three `pass1/2/3` DLLs are **byte-identical** (same SHA256). That is the real structure of the release package, not three processing stages.

> **Note on documentation language**: the six analysis documents under `docs/` and the four methodology documents under `team-methodology/` are currently written in **Chinese**.

---

## Quick Start

```bash
git clone https://github.com/Paimonshen/dlss-nr-reverse-engineering.git
cd dlss-nr-reverse-engineering

# Binaries are tracked by Git LFS; pull real content after cloning (~186 MB)
git lfs install
git lfs pull
```

### Dependencies

```bash
pip install pefile msgpack    # Python 3.11+
```

### Reproduce the main results

```bash
# 1) Module shape: 12 sections / 17 version.dll exports / 194 imports (10 DLLs)
python tools/pe_parser.py info binaries/dlssnr_amd_pass1.dll --limit 0

# 2) Relocations: 19 blocks, 2044 entries (DIR64 2040 + ABSOLUTE 4)
python tools/pe_parser.py reloc binaries/dlssnr_amd_pass1.dll

# 3) Exception table: 1167 entries
python tools/pe_parser.py pdata binaries/dlssnr_amd_pass1.dll --pdata-limit 0

# 4) 8 device targets x 34 kernels, with kernarg size and by_value args
python tools/msgpack_extract.py binaries/dlssnr_amd_pass1.dll --json out/kernels.json

# 5) Weight container magic (1 hit) and payload byte distribution (entropy 5.902444 bits/byte)
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --hex "44 4C 53 53 4E 52 57 31"
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --byte-histogram --range 0x1629:
```

All three tools are **read-only** (they write nothing except to explicit `--out` / `--json` / `--hex-out` paths). See [tools/README.md](tools/README.md).

---

## Three Environment Constraints (please note)

Every conclusion is bounded by these three constraints, and the docs mark them throughout:

1. **No AMD hardware** ⇒ no runtime observation (the most critical of the three gaps).
2. **No AMDGPU disassembler** (`llvm-objdump` unavailable) ⇒ no device-side disassembly; call relationships of symbols such as `swin_layer` are unproven.
3. **No Intel toolchain / Xe hardware** ⇒ everything about specific Xe / SPIR-V / XMX capabilities is **marked "needs external documentation" and left without conclusion**.

**Therefore the level of our conclusions is "static byte level"**: whatever can be given is given with byte evidence; whatever cannot is marked "unresolved" with a request for external documentation.

---

## How to Contribute

- **Close the three gaps** (see "Help Wanted" above) — the most valuable contribution.
- **Correct a conclusion**: if a documented conclusion disagrees with the byte evidence, please attach **file + offset + raw bytes + reproduction command**.
- **Supply external documentation** for items marked "needs external documentation".
- **Improve the tools or docs.**

See [CONTRIBUTING.md](CONTRIBUTING.md). This project has high evidence standards (universal negatives must give range + pattern + hit count), but **a PR with a correct conclusion and insufficient evidence will only be asked to add evidence, never rejected outright**.

## License and Legal

- **Original work** (docs, scripts) is under the **MIT License** — see [LICENSE](LICENSE).
- **Third-party binaries** (under `binaries/`) are **not** covered by that license; copyright belongs to their respective owners. Origins and SHA256 are in [EXTERNAL_BINARIES.md](EXTERNAL_BINARIES.md).
- This is **interoperability research**. It contains no DRM-circumvention code and no NVIDIA copyrighted binaries. If a rights holder requests removal, we will comply immediately — see [LEGAL.md](LEGAL.md).

## Disclaimer

This is independent static research, provided **"as is", without warranty of any kind**. Users **assume all risk and legal responsibility** for any use of this repository's contents.
