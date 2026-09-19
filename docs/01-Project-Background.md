# Project Background

## 1. What This Project Is

This project is a reverse-engineering and feasibility study of the **DLSS NR (Neural Rendering)** module.

The direct subject of the study is an **AMD-side DLSS-NR runtime module**:

| Item | Value |
|---|---|
| File name | `dlssnr_amd_pass1.dll` |
| Size | 7,156,224 bytes (`0x6D3200`) |
| SHA256 | `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| Format | PE32+, ImageBase `0x180000000`, 12 sections in total |
| Module identity | The module name (pointed to by the export directory Name RVA) is `version.dll`, i.e. a **proxy DLL** named `version.dll` |
| Source availability | The original device-side source **is not in the workspace** (see the next section) |

The device-side code of this DLL is wrapped inside the `.hip_fat` section; it is 8 AMDGPU device bundles running on top of the **AMD HIP** runtime (`amdgcn-amd-amdhsa` architecture), and it uses the `amdhip64_7.dll` HIP runtime interface for device enumeration, memory allocation and kernel launch.

## 2. Why This Was Done

### 2.0 The larger goal (and where this analysis fits)

The analysis in this repository is **one stage of a longer effort**, not an end in itself. The direction we are working toward:

> **Recover the source → get it running portably → accelerate it per vendor → unify it into one cross-GPU codebase.**

| Stage | What it means | Status |
|---|---|---|
| **1. Recover the source** | Decompile the main program and reconstruct a readable, rebuildable source tree | **Next stage.** This repository's analysis is the input to it |
| **2. A common-instruction build** | A build using **no vendor-proprietary instruction set** — a plain portable compute path, so the thing **runs at all** and every later backend has a known-good reference | Direction |
| **3. Vendor-accelerated builds** | Add acceleration as separate backends: **Intel** (Xe / XMX), **AMD** (RDNA / CDNA, HIP and matrix cores), and **NVIDIA** (the vendor's own NGX / DLSS implementation) | Direction |
| **4. One codebase, every GPU** | Integrate the backends into a **single source tree with backend selection** — the portable path as the universal fallback | Direction |

Two constraints that follow directly from what this analysis established, and that must not be glossed over:

1. **Stage 1 hits the same unsolved gap.** Reconstructing a *usable* source tree requires the **`71 block → kernel` dispatch binding**. That binding is **unobtainable under the available conditions** (all four avenues closed — see [`06-Open-Gaps-and-Limits.md`](06-Open-Gaps-and-Limits.md)). Most of the tree can be recovered; the dispatch layer cannot, by decompilation alone.
2. **The NVIDIA path is reference-only.** This repository **does not contain NVIDIA copyrighted binaries** (see [`../LEGAL.md`](../LEGAL.md) §8), and the publicly available copy of the NVIDIA component is an **interface layer with no analysable kernel metadata**. It can be used to **cross-check interface behaviour and results**; it is **not** a source of decompilable kernels.

**None of stages 2–4 is completed work.** What this repository currently contains is analysis and tooling, at the **static byte level**.

### 2.1 The concrete question this analysis answers

The analysis was scoped to answer one concrete engineering question:

> **Can this DLSS NR module be recompiled / ported so that it runs on Intel Arc (Xe / XMX) hardware?**

"Recompile / port" here does not mean "make the AMD binary run directly on Intel" — that is not a feasible goal. It means assessing all the structural conditions that **re-implementing the module's compute kernels under the Intel-side execution model** would have to face:

- What are the parameter layout and resource requirements of each of the 34 device kernels?
- What is the operator semantics of these kernels, and which class of Intel-side primitives can they map to?
- How much of the host-side runtime interface must be replaced, and with what?
- What is the format of the 147 MB of weight data, and what conversion does it need?
- Which questions simply cannot be answered under the current conditions?

This project's positioning is therefore **interoperability research**: what it produces is a **traceable specification and assessment**, not a directly runnable port.

### 2.1 Hardware Targets

| Item | Value |
|---|---|
| Target platform | Intel Arc B580 (Xe2 / Battlemage architecture, including the XMX matrix engine) |
| Source platform | AMD HIP / `amdgcn-amd-amdhsa` (8 device targets) |
| Target execution model | SYCL / oneAPI Level Zero (with two candidate paths: the XMX path and the generic SPIR-V path) |

### 2.2 Environment Constraints (three hard constraints that directly determine the boundary of the conclusions)

| # | Constraint | Consequence |
|---|---|---|
| **E-1** | **No AMD hardware** | Any "runtime verification" work is not executable: we can neither run the original on AMD, nor obtain the original's runtime behavior (such as block scheduling, symbol write points) |
| **E-2** | **No AMDGPU disassembler** | `llvm-objdump` returns 0 hits when searched in the workspace; `capstone` 5.0.7 does not support AMDGPU. The `.text` of the 34 kernels totals **6,081,960 bytes** (the sum over the 8 device ELFs), and **the number of disassembled instructions = 0** |
| **E-3** | **No Intel / SYCL / HIP toolchain** | `Get-Command` for `icx` / `icpx` / `dpcpp` / `clang` / `cl` / `hipcc` / `g++` gives **0 hits each**; no `.sycl` / `.hip` source file in the workspace could be compiled |

These three constraints mean: **the verification ceiling for all conclusions in this project is the "static byte level"**. Anything that is a runtime, instruction-level or compile-level judgment is uniformly marked by this project as "requires external conditions" or "needs external documentation", with no conclusion given.

## 3. What Is Available of the Analysis Subject

### 3.1 Device Side: 8 AMDGPU Bundles, No Intel / Xe / SPIR-V Target Whatsoever

The `__CLANG_OFFLOAD_BUNDLE__` container inside the `.hip_fat` section has 9 bundle entries in total:

- **1 host placeholder** (entry `#0`, triple `host-x86_64-unknown-linux-gnu-`, **size = 0**, an empty-range placeholder);
- **8 device bundles**, all with the triple `hipv4-amdgcn-amd-amdhsa--<target>`.

The 8 device targets are, in order:

| No. | triple |
|---|---|
| `#1` | `hipv4-amdgcn-amd-amdhsa--gfx10-3-generic` |
| `#2` | `hipv4-amdgcn-amd-amdhsa--gfx11-generic` |
| `#3` | `hipv4-amdgcn-amd-amdhsa--gfx1100` |
| `#4` | `hipv4-amdgcn-amd-amdhsa--gfx1101` |
| `#5` | `hipv4-amdgcn-amd-amdhsa--gfx1102` |
| `#6` | `hipv4-amdgcn-amd-amdhsa--gfx1200` |
| `#7` | `hipv4-amdgcn-amd-amdhsa--gfx1201` |
| `#8` | `hipv4-amdgcn-amd-amdhsa--gfx9-generic` |

**No Intel / Xe / SPIR-V target exists inside this fat binary**: across the full set of 9 triples there is no architecture identifier containing `spirv`, `intel` or `xe`.

The 8 device ELFs have `e_machine = 0xE0` (224 = **EM_AMDGPU**), 8/8 hits; their `e_ident` all contain `EI_OSABI = 0x40` (ELFOSABI_AMDGPU_HSA) and `EI_ABIVERSION = 4`, consistent with the `hipv4-` prefix.

### 3.2 Kernel and Parameter Metadata

The `.note` section of each device bundle carries a msgpack metadata document of type `NT_AMDGPU_METADATA`, which contains:

- the complete parameter specification of **34 kernels** (per-parameter `.offset` / `.size` / `.value_kind`, plus `.kernarg_segment_size`);
- **16 resource fields** (`.group_segment_fixed_size`, `.private_segment_fixed_size`, `.sgpr_count`, `.vgpr_count`, spill counts, `.wavefront_size`, `.max_flat_workgroup_size`, `.workgroup_processor_mode`, etc.).

8 targets × 34 kernels = **272 kernel entries**, with **440 parameters** per target (3,520 parameter entries in total).

### 3.3 Host Side

- 17 exports, all of them `FF 25` jump stubs (VERSION.dll API names);
- **194 imports**, distributed across 10 DLLs, of which **`amdhip64_7.dll` accounts for 29** (HIP runtime APIs);
- two 8-byte-stride function pointer tables (the wrapper registry);
- 34 `__hipRegisterFunction` registration calls, in one-to-one correspondence with 272 ÷ 8 = 34 kernels.

### 3.4 Weights

The entity of the 147 MB order of magnitude of weights is an **external file** (not embedded in the DLL):

| Item | Value |
|---|---|
| Size | 147,689,451 bytes (`0x8CD8FEB`) |
| SHA256 | `6BF8DC931EF3CCFFE18C82DE26AB374156E7F19539FFCF8EABAA25DCA5CF15AB` |
| First 8 bytes | `44 4C 53 53 4E 52 57 31` = ASCII `DLSSNRW1` |

This container format **has been fully decoded** within this project (see `05-Intel可行性评估.md` (in Chinese) chapter 6 and `06-未解缺口与限制.md` (in Chinese)).

## 4. Is There "Source Code" in the Workspace

This is the question the assessment work must answer first, because the answer directly determines the usable material for everything that follows. The conclusion is: **partially present, but it is not the source of this DLL.**

The workspace does contain a self-developed pass-side project tree (`Engine/`, 28 files), which includes:

- a **re-implementation** of the Swin attention algorithm (including the `SwinParams` struct, `windowSize` / `shiftSize` cyclic shift, the `relPosBias` relative position bias and its point of use in the score computation, online softmax);
- a **re-implementation** of block scheduling (`NUM_BLOCKS = 71`, `BlockConfig`, segmented constants, `GetNumLayers()`);
- an Intel-side SYCL attempt (including a `joint_matrix` GEMM template);
- a weight parser.

But this tree is **non-isomorphic** to the DLL; the collision evidence is as follows:

| # | Basis | Evidence |
|---|---|---|
| N1 | **Kernel base-name collision 2/30** | `Engine/` has 6 deduplicated base names; the DLL's 34 kernels have **30** deduplicated base names; **the intersection is only 2** (`k_swin_1h_32_fp8`, `k_swin_var`) ⇒ **28/30 DLL base names do not exist in that tree** |
| N2 | **4 base names present in the tree but absent from the DLL** | `blend_output` / `dlssnr_imgenc` / `mlp_projection` / `residual_add` — none of these four names exists among the DLL's 34 kernels |
| N3 | **The 34 kernel names get zero hits outside that tree** | Across the 2,996 non-`Engine/` source files in the whole workspace, the 10 named base names each get **0 hits** |
| N4 | **Full Git history has no equivalent either** | 5,951 historical source file paths; path substring `engine/` **0**, `swin` **0**, `runtime_intel` **0**; `Engine/` is **untracked** in the workspace |
| N5 | **The AMD SDK it depends on is not in the workspace** | `hip/hip_runtime.h` itself gets **0 hits**; the `rocm` directory **0**; `hipcc` **0**; `*.a` / `*.so` **0** |

⇒ **The two sides are two different implementations of the same network**: `Engine/` is a **re-implementation project** of the same network, and **is not** the source of this DLL.

**One correction that must be carried forward**: the DLL's 12 sections **do not include `.rsrc`**; the entity of the 147 MB order of magnitude is an **external package weight file**, measured **separately** from the packed region inside the DLL (`.hip_fat`, 6,649,000 bytes).

## 5. Overview of the Analysis Content

The analysis work completed by this project falls into five areas:

### 5.1 Container and Format Layer

- field-by-field PE structure parsing (the 12-section section table, export table, import table, `.reloc`, the `.data` file image boundary);
- `__CLANG_OFFLOAD_BUNDLE__` header parsing and integrity verification of the 9 bundle entries;
- section table, symbol table and `.kd` descriptor parsing for the 8 device ELFs;
- decoding of the AMDGPU msgpack metadata inside the md-snapshot `.note` section.

### 5.2 Parameter and Resource Specification Layer

- the per-parameter layout (`offset` / `size` / `value_kind`) and `kernarg_segment_size` of the 34 kernels;
- the value sets, frequencies and per-cell consistency across the 8 targets of the 16 resource fields;
- the composition identity (`kernarg = by_value + 66 + 190`) and the three exception kernels.

### 5.3 Host-Side Structural Layer

- the `version.dll` proxy export surface (17 `FF 25` stubs);
- the 194-entry import surface classified DLL by DLL;
- the `hipLaunchKernel` thunk ladder and its item-by-item mapping to IAT slots;
- the full slot semantics of the two 8-byte-stride function pointer tables (table A / table B);
- the kernel registration mechanism (pairing of the 34 registration calls to table slots).

### 5.4 Operator and Weight Layer

- operator-type inference and structural characteristics of the 34 kernels;
- byte-by-byte decoding of the weight container (header, 153 index entries, payload region, three identities).

### 5.5 Feasibility Assessment Layer

- the A / B / C three-way kernel classification (whether the resource side and the parameter side need rewriting);
- resource adaptation (SLM / private segment / wavefront / workgroup);
- the host-side import surface to be replaced (29 / 194 entries);
- the S0–S7 roadmap with 23 verifiable milestones;
- unclosed gaps and the external documentation checklist.

## 6. Deliverables

The public document set produced by this project is as follows:

| File | Content |
|---|---|
| `01-Project-Background.md` | This document. Project motivation, analysis subject, overview of the analysis content and deliverables |
| `02-Analysis-Methodology.md` | Analysis methods: PE / ELF parsing, bundle unpacking, device ELF extraction, msgpack metadata decoding, byte-pattern scanning, independently re-derived cross-validation |
| `03-DLL-Structure-Analysis.md` | DLL structure: the 12-section section table, the proxy export surface, the 194-entry import surface, the thunk ladder, the two function pointer tables, the kernel registration mechanism |
| `04-内核参数规格.md` (in Chinese) | Full parameter and resource specification tables for the 34 kernels, including the three exception kernels and the cross-target consistency conclusions |
| `05-Intel可行性评估.md` (in Chinese) | The complete feasibility assessment: A/B/C classification, resource adaptation, operator mapping, host replacement, weight format, the S0–S7 roadmap with 23 milestones, unclosed gaps, external documentation checklist |
| `06-未解缺口与限制.md` (in Chinese) | An honest statement of limits: which questions are unanswerable under this project's conditions, why, and which need external documentation |

## 7. Reading Conventions

### 7.1 Evidence Strength Grading

This document set marks the evidence level of every conclusion. Readers must state the level when citing:

| Marker | Meaning |
|---|---|
| **proven** | Raw bytes, PE / ELF structure or recomputable arithmetic serves as the criterion |
| **leaning** | Sampling evidence points to one interpretation, but no full-population check was done; **not upgraded to proven** |
| **needs external documentation** | The judgment depends on documentation or a specification outside the workspace; **this project gives no conclusion**, only the direction to be looked up |
| **unresolved** | No criterion within the workspace can adjudicate |

### 7.2 Caliber Discipline

Several values have **multiple calibers**, and citing one must state which was taken, otherwise wrong conclusions result. The registered caliber pairs include:

- the **272-entry caliber** (34 kernels × 8 targets) versus the **34-kernel caliber** (counted per single target);
- **the three counting calibers for cross-target inconsistency** (field × kernel pairs **163** / cells compared against `#1` **605** / cells compared pairwise across 8 targets **2183**) — the three cannot be mixed; estimates of the form "163 × 7" or "163 × 28" are both wrong;
- the **value + occurrence-count caliber** versus the **single-point attribution caliber** (e.g. 64,640 B occurs 8 times; one must not write "some kernel = 64,640" without attaching the caliber);
- the **count of non-zero entries** caliber versus the **count of distinct values** caliber for the spill fields.

### 7.3 Terminology

- **kernel**: an executable function on the GPU device side; in this project it specifically means the 34 kernels inside the `.hip_fat` metadata.
- **bundle / bundle entry**: one target entry inside the `__CLANG_OFFLOAD_BUNDLE__` container.
- **kernarg**: the kernel parameter segment.
- **wrapper**: a thin host-side function wrapping one kernel launch flow.
- **handle table**: i.e. the two 8-byte-stride function pointer tables, carrying wrapper addresses.
- **block**: a block of the network structure (71 in total), in a many-to-one relationship with the kernels.
