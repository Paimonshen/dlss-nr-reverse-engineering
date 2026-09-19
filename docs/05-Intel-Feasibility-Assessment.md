# Intel Feasibility Assessment

**Assessment target**: recompiling DLSS NR from AMD HIP (the `amdgcn-amdgpu` ecosystem) to Intel Arc B580 (Xe / XMX).

**Assessment discipline**: for any **specific capability** involving Intel Xe / SPIR-V / XMX, the item is always marked "needs external documentation" with the direction to look into, and **no conclusion is given**. For any judgement of the runtime, instruction, or compile class, the item is always marked as requiring external conditions.

---

## 0. Current State and Constraints

### 0.1 Environment Constraints (three hard constraints)

| # | Constraint | Content |
|---|---|---|
| **E-1** | **no AMD hardware** | the runtime observation path is **unavailable** within this environment (neither provided nor planned) |
| **E-2** | **no AMDGPU disassembler** | `llvm-objdump` gets **0** hits when searched for; `capstone` 5.0.7 does not support AMDGPU (searching the module for AMD / GPU related properties gets 0 hits) |
| **E-3** | **no Intel / SYCL / HIP compilation toolchain** | `Get-Command` on `icx` / `icpx` / `dpcpp` / `clang` / `clang++` / `cl` / `hipcc` / `g++` gets **0 hits each** |

**Three direct consequences**:

1. **Any "runtime verification" class of work is not executable within this environment** —— neither running the original on AMD, nor running the ported version on Intel.
2. **Any "instruction-level" criterion is unobtainable within this environment** —— the `.text` of the 34 kernels totals **6,081,960 B** (the sum of the 8 device ELFs), and **the number of disassembled instructions = 0**.
3. **Any verification of "whether the ported version compiles" is not executable within this environment**.

⇒ **The verification ceiling for every conclusion of this project is "static byte level".**

### 0.2 The Confirmed Shape of the Assessed Object

| Item | Confirmed value |
|---|---|
| DLL | `dlssnr_amd_pass1.dll`, 7,156,224 B (`0x6D3200`), SHA256 `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| section table | **12 sections, without `.rsrc`**: `.text` / `.rdata` / `.data` / `.pdata` / `.fptable` / `.hipFatB` / `.hip_fat` / `.retarc` / `.retard` / `.tls` / `_RDATA` / `.reloc` |
| device code container | `.hip_fat`, VirtualSize `0x6574A8` = 6,649,000 B |
| **8 device bundles, all `amdgcn-amd-amdhsa`** | `gfx10-3-generic` / `gfx11-generic` / `gfx1100` / `gfx1101` / `gfx1102` / `gfx1200` / `gfx1201` / `gfx9-generic` (+ 1 empty host placeholder). **No Intel / Xe / SPIR-V target whatsoever** |
| **host-side import surface 194 entries / 10 DLLs** | `KERNEL32` 127 / **`amdhip64_7` 29** / `USER32` 15 / `GDI32` 10 / `bcrypt` 6 / `VERSION` 3 / `d3d12` 1 / `dxgi` 1 / `D3DCOMPILER_47` 1 / `COMDLG32` 1 |
| module identity | module name = `version.dll` (proxy DLL); all 17 exports are pure `FF 25` forwarders |
| the 34 kernel names | statically recoverable; **registration pairing 34/34** (26 → table A slots 0–25, 3 → slots 30–32, 5 → table B slots 0–4) |
| the two 8-byte-stride tables | table A `0x180056170`, table B `0x180058A48`, full slot semantics determined |
| the two builds | the 240 B byte-by-byte difference lies entirely in `.rdata`, semantically just one bound constant; `.text` / `.hip_fat` are byte-identical |

### 0.3 The Actual State of the Three "Suspected Source Trees"

#### (a) The DLSS-NR project tree on the OptiScaler side —— **ruled out (only for that tree)**

| Search class | Range | Pattern | Hit count |
|---|---|---|---|
| 1 | the whole tree (2,942 `.cpp` / `.h` / `.hpp` / `.hlsl` / `.glsl`) | `hipLaunchKernel` | **0** |
| 2 | as above | the 34 kernel names | **0** |
| 3 | as above | `encoder` \| `bottleneck` \| `decoder` \| `num_blocks` \| `block_idx` \| `swin` | **0** |
| 4 | as above | DLL-embedded shader text among the 366 `.hlsl` | **0** |

**Scope limitation (must be given together with any citation)**: this ruling holds **only for** that tree and **does not cover** the other tree in the workspace.

#### (b) The self-developed pass-side project tree in the workspace —— **contains pass-side source, but is non-isomorphic to the DLL**

| Item | Measured |
|---|---|
| scale | **28 files**: text sources **16** (2 `.hip` + 2 `.sycl` + 10 `.cpp` + 1 `.h` + 1 `.hlsl`); `build/` **10** (6 `.exe` + 2 `.obj` + 1 `.lib` + 1 `.exp`); `weights/` 2 |
| self-description | "DLSS 5 Neural Rendering Engine for Intel Arc" / "Re-implementation of … DLSS-NR-on-AMD engine" / "Supports: XMX-native (Intel Arc) and HIP (AMD)" |
| **coverage of the DLL's 34 kernels** | **6 / 34**: k0 (`k_swin_1h_32_fp8`), k29–k33 (the 5 `k_swin_var`); **the other 28 get 0 hits** |
| **determination of non-isomorphism** | of that tree's 11 `__global__` kernel names, **only 2** appear among the DLL's 34 kernel entries; after deduplication **28/30 basenames do not exist in that tree** ⇒ **that tree is a re-implementation project of the same network, not the source code of this DLL** |
| shared memory inside that tree | only **1 occurrence** of the relevant pattern across the whole tree (inside `mlp_projection`, **unrelated to Swin**); `LDS` / `SLM` / `local_accessor` / `group_barrier` get **0 hits each** |
| `joint_matrix` inside that tree | **13 occurrences** (8 type definitions/comments + 5 calls); the **5 calls** are all inside one GEMM template; that template gets **only 1 hit = the definition line, 0 instantiations** |
| the "unimplemented" surface of that tree | the function bodies of `NrBackend_Evaluate` and of each host-side stage **are all `return true;`** |
| has it been compiled / run | **undetermined**: `build/` contains **no `.sycl` compilation artifact**; the mtimes of the 6 exes are concentrated within two days; the exe import tables were not read; and the toolchain is unavailable (E-3) |

**One-sentence conclusion (the decidable part)**: that tree **can serve as** the fact that "a porting project already exists", as a **second source for the weight format**, and as a **sample of a similar implementation corresponding to the host-side API**; it **cannot serve as** a source-code comparison for the DLL's 34 kernels, and **does not constitute** "all 34 kernels already have an XMX implementation".

#### (c) Location of the build files —— **at the project root, not inside that tree**

- `CMakeLists.txt` / `build_*.bat` / `README.md` are at the project root; recursively listing that tree by extension (`.txt` / `.bat` / `.cmake` / `.vcxproj` / `.sln` / `.md` / `.json`) gets **0 hits**;
- `KERNEL_SOURCES` at root-level `CMakeLists.txt:32` **lists only one `.sycl`**; the other `.sycl` file gets **0** hits in the root-level CMake; none of the 7 `build_*.bat` compiles any `.sycl` under `kernels_xmx/`.

### 0.4 Attribution of the Weight Entity (one correction that must be carried forward)

| Item | Confirmed value |
|---|---|
| the 147 MB-scale entity | **external file** `dlssnr_on_amd_weights.bin` = **147,689,451 B** (`0x8CD8FEB`) |
| SHA256 | `6BF8DC931EF3CCFFE18C82DE26AB374156E7F19539FFCF8EABAA25DCA5CF15AB` |
| first 8 bytes | `44 4C 53 53 4E 52 57 31` = ASCII `DLSSNRW1` |
| second copy | same size, same SHA256, byte-identical |
| **the DLL contains no `.rsrc`** | the full set of section names is in §0.2; the 147,696,792 B `.rsrc` **belongs to another module** |
| magic search (whole library) | range = 8,311 files in the workspace / 3,828,060,117 B; pattern `DLSSNRW1`; **137 hits**; among them the **binary entities** are only the installer and the two copies of the aforementioned weights; **no third weights entity with different content was found** |

**Citation discipline**: when citing the 147 MB entity, one **must state that it is the external weights file**, and must **account for it separately** from the in-DLL packed region (`.hip_fat` 6,649,000 B); one **must not** carry forward "the DLL's `.rsrc` 147 MB".

### 0.5 Chapter Summary (6 statements that can be cited directly)

| # | Conclusion |
|---|---|
| 1 | **no AMD hardware / no disassembler / no Intel toolchain** ⇒ all three classes of verification (runtime, instruction-level, compile-level) are not executable within this environment |
| 2 | the DLSS-NR tree on the OptiScaler side is **ruled out** (four search classes, 0 hits each), and **this ruling holds only for that tree** |
| 3 | the self-developed pass-side project tree (28 files) **contains pass-side source**, but is **non-isomorphic to the DLL** (28/30 deduplicated basenames are absent from it; it covers only 6/34 kernels) |
| 4 | that tree **does not constitute** "the 34 kernels already have XMX implementations"; its `joint_matrix` usage is concentrated inside **1 template with 0 instantiations** |
| 5 | the NVIDIA-side module is an **interface layer** (0 hits for real CUDA / PTX / ELF magics), **unusable and not usable as a comparison object** |
| 6 | the 147 MB weight entity = **external file** 147,689,451 B / `DLSSNRW1`; the DLL's 12 sections **contain no `.rsrc`** |

---

## 1. Kernel Classification (A / B / C)

### 1.1 Threshold Declaration (**self-set by this table, not specification values —— must be cited together with the classification**)

| Threshold | Value |
|---|---|
| class A `group_segment_fixed_size` threshold | **≤ 4096** |
| class A `private_segment_fixed_size` threshold | **≤ 64** |
| class C `group_segment_fixed_size` threshold | **≥ 32768** |

> **Ruling on the origin of the thresholds**: `4096` / `32768` / `64` **have no specification source whatsoever** ⇒ "self-set only, not Intel / SPIR-V specification values" holds. Confirmed by a five-way search (R1–R5).

**Recomputation under shifted bands (three bands)**:

| Band | Result |
|---|---|
| the band adopted by this table (A ≤ 4096 / C ≥ 32768) | **A = 7 / B = 20 / C = 7** |
| A threshold 4096 → 8192 | **A = 9 / B = 18 / C = 7** (k4 `k_conv_res`, k19 `k_final_head` move from B into A) |
| C threshold 32768 → 16384 | **A = 7 / B = 10 / C = 17** (k3 / k6 / k8 / k9 / k12 / k14 / k16 / k17 / k18 / k33, 10 in total, move from B into C) |
| both bands changed together (8192 / 16384) | **A = 9 / B = 8 / C = 17** |

**Supplementary**: the threshold cut points fall **inside the gaps** of the value set, so the banding is stable.

### 1.2 The Three-Class Decision Principles (P1–P6)

| Criterion | Condition | Type |
|---|---|---|
| **P1** (necessary condition on the class A resource surface; all three must hold simultaneously) | P1-a `group` ≤ 4096 across all 8 targets; P1-b `priv` ≤ 64 across all 8 targets; P1-c `sgpr_spill_count = 0` **and** `vgpr_spill_count = 0` (0 across all 8 targets) | resource surface |
| **P2** (sufficient condition on the class A parameter surface) | belongs to the **31-kernel unified template**: `.kernarg_segment_size = by_value + 66 + 190`, `.args` count = 14, 13 `hidden_*`, `by_value` at offset 0, `.kernarg_segment_align = 8` (8 targets consistent) | parameter surface |
| **P3-a** (class B · SLM form) | the 8-target maximum of `group` ∈ [1, 32767] | resource surface |
| **P3-b** (class B · private-segment/spill form) | `priv` **not fully identical** across the 8 targets, **or** the spill count > 0 in any target | resource surface |
| **P4-a** (class C · SLM scale band) | the 8-target maximum of `group` ≥ 32768 | resource surface |
| **P4-b** (class C · parameter layout exception) | the parameter layout **does not belong** to the 31-kernel unified template (no `+66` hidden region, no `+190` tail, last parameter end == `kernarg_segment_size`) | parameter surface |
| **P6** (external documentation prerequisite) | any criterion whose conclusion depends on "specific Xe / XMX capabilities" is always marked as needing external documentation, **with no conclusion given** | — |

**Re-verification**: P1–P6 all hold; the P2 template is 248/272 + exceptions 24/272, exactly k26 / k27 / k28 × 8.

### 1.3 The A / B / C Lists

**Total identity: 7 + 20 + 7 = 34** ✅

#### Class A (7) —— "neither the resource surface nor the parameter layout surface needs rewriting"

| # | kernel name | `kernarg` | `group` (8 targets) | `priv` | spill |
|---|---|---|---|---|---|
| 10 | `k_conv_splitk` | 304 | 4096 ×8 | 0 ×8 | (0,0) |
| 13 | `k_expand2` | 280 | 0 ×8 | 0 ×8 | (0,0) |
| 20 | `k_repack` | 288 | 0 ×8 | 0 ×8 | (0,0) |
| 21 | `k_dec_upsample` | 296 | 4096 ×8 | 0 ×8 | (0,0) |
| 22 | `k_mean` | 288 | 1024 ×8 | 0 ×8 | (0,0) |
| 23 | `k_import` | 304 | 0 ×8 | 0 ×8 | (0,0) |
| 24 | `k_export` | 320 | 0 ×8 | 0 ×8 | (0,0) |

**Decision principle**: P1-a ∧ P1-b ∧ P1-c ∧ P2. Measured characteristics: `group` ∈ {0, 1024, 4096} and consistent across the 8 targets; `priv` = 0 ×8; both spills = 0 ×8; `kernarg = by_value + 66 + 190` holds.

> **Precise limitation on the meaning of class A (must not be omitted)**: class A **only means that the resource surface and the parameter layout surface do not need rewriting**; it **does not mean** "that kernel needs zero changes on Xe", and **does not mean** "the operator can be mapped 1:1 to SPIR-V / XMX" —— the latter is marked as needing external documentation for **all 34 kernels**.
>
> **Two points that still need item-by-item verification inside class A (both are global items)**: ① the dual form of `.wavefront_size` 32/64 (§1.5); ② `max_flat_workgroup_size` is **1024** for k20 / k22 / k23 / k24 (4 of the 7 in class A), and 256 for k10 / k13 / k21 —— "whether 1024 can hold on Xe" is marked as needing external documentation.

#### Class B (20) —— "the resource surface needs per-target recomputation and rewriting for Xe; the parameter layout surface does not need rewriting"

| Hit form | Condition | Kernels (# index) | Count |
|---|---|---|---|
| **P3-a only** | `group` maximum ∈ [1, 32767], and `priv` consistent across the 8 targets with spill = 0 | k3, k4, k6, k8, k9, k12, k14, k15, k16, k17, k18, k19, k33 | **13** |
| **P3-a ∧ P3-b** | `group` maximum ∈ [1, 32767], and `priv` not fully identical across targets or spill > 0 | k11, k29, k30, k31, k32 | **5** |
| **P3-b only** | `group` maximum ≤ 4096, but `priv` not fully identical across targets or spill > 0 | k7, k25 | **2** |
| **total** | — | — | **20** ✅ |

**Recomputable detail**:

- k3 / k4 / k6 / k8 / k9 / k12 / k16 / k17 / k18 / k19 / k33: their `group` maxima = 24576 / 8192 / 21504 / 23808 / 16384 / 28928 / 19456 / 24576 / 24576 / 8192 / 19200 respectively; among them the first 10 have `group` **not fully identical across targets** (`#1` / `#8` lower than `#2`–`#7`), while k14 (16384), k15 (12800), k33 (19200) have `group` **consistent across the 8 targets**;
- k11: `group` = 6144 (consistent across the 8 targets) + `sgpr_spill_count` = 29 (`#8`);
- k29–k32: `group` = 15,616–15,632 (consistent across the 8 targets) + `priv` not fully identical across targets (the `#2` / `#5` high band) + `vgpr_spill_count` 20 / 7 / 75 / 88;
- k7: `group` = 0 ×8, but `priv` in `#8` = **404** (the largest private segment in the whole library) and `sgpr_spill_count` = 133, `vgpr_spill_count` = 100 (both are the largest in the whole library);
- k25: `group` = 0 ×8, but `priv` in `#8` = 84 and `vgpr_spill_count` = 23.

> **Relation to "wavefront 32/64" (must be stated)**: the `.wavefront_size` = 32 (`#1`–`#7`) / 64 (`#8`) difference holds for **34/34** kernels and is **not** a distinguishing criterion for class B. Writing it as "some kernels fall into class B because `wavefront_size` = 64" contradicts the bytes (all 34 kernels of `#8` are 64). This item is a **global verification item**.

#### Class C (7) —— "requires redesign"

| Path | Kernels | Object of redesign |
|---|---|---|
| **P4-a (SLM scale band, `group` maximum ≥ 32768): 4** | k1 (**64,640**, the largest in the whole library), k0 (62,592), k2 (62,592), k5 (**58,368**) | **the partitioning and usage of shared memory (SLM)** (the 63.125 / 61.125 / 57.00 KiB bands) |
| **P4-b (parameter layout exception): 3** | k26 `k_flag_wait`, k27 `k_align_probe`, k28 `k_flag_set` | **the kernel parameter-passing form and its device-side semantics** |

`4 + 3 = 7` ✅. Among them, this value is consistent across the 8 targets for k0 / k1 / k2; for k5 this value is **not fully identical across targets** (`#1` / `#8` = 20480, `#2`–`#7` = 58368).

**Three citation disciplines (class C)**:

1. **Must not be phrased as "already exceeds the limit"**: the maximum `group_segment_fixed_size` of 64,640 B is **896 B below the 65,536 B (64 KiB) limit**, and `≥ 65536` gets **0** hits. The class C criterion is "this table's self-set 32768 band + closeness to the limit", **not "exceeding the limit"**.
2. **The availability of that band on Xe** is marked as needing external documentation (see §8 T-06 / A4).
3. **The reason the 3 exception kernels enter class C is P4-b, not the resource surface**: their resource surface (`group` = 0, `priv` = 0, spill = 0, consistent across the 8 targets) **satisfies P1-a/b/c**; the basis for classing them C is the **layout exception** and "the only form carrying raw device pointer parameters". **This determination does not contradict "low resource demand".**

### 1.4 Summary of the Three-Class Decision Principles (one-sentence version)

| Class | One-sentence principle | Criterion | Representative meaning |
|---|---|---|---|
| **A** (7) | **neither the resource surface nor the parameter layout surface needs rewriting** | P1 ∧ P2 | can be moved field by field under the existing parameter template |
| **B** (20) | **the resource surface needs per-target recomputation and rewriting for Xe; the parameter surface does not need rewriting** | P3-a ∨ P3-b | requires handling SLM capacity / private segment / spill |
| **C** (7) | **requires redesign** (SLM partitioning, or the parameter-passing form and its device-side semantics) | P4-a ∨ P4-b | cannot be completed by moving fields one by one |

### 1.5 Facts Uniform Across the 34 Rows (not a classification difference, but affecting the roadmap)

| # | Fact | Value |
|---|---|---|
| 1 | `.wavefront_size` | **32 (`#1`–`#7`, 238 records) / 64 (`#8`, 34 records)** ⇒ for 34/34 kernels this field is **not fully identical** across the 8 targets |
| 2 | `.max_flat_workgroup_size` | **256 × 26 kernels / 1024 × 8 kernels** (34-kernel scope); under the **272-entry scope** it is **256 × 208 / 1024 × 64**. **The two scopes are equivalent, and a citation must state which** |
| 3 | `.kernarg_segment_align` / `.uniform_work_group_size` / `.uses_dynamic_stack` / `.language` / `.language_version` | **8 × 272** / **1 × 272** / **False × 272** / **OpenCL C × 272** / **[2,0] × 272** (8 targets consistent) |
| 4 | `.workgroup_processor_mode` | `#1`–`#7` are all **1**, and **`#8` lacks the key entirely** (`#8` has 17 keys) |
| 5 | the 34 kernel names and registration pairing | **34/34** (26 → table A slots 0–25, 3 → slots 30–32, 5 → table B slots 0–4) |

### 1.6 Sampling Re-Verification Record

**6 kernels** were sampled (exceeding the minimum requirement), and all classification bases hold:

| Sampled kernel | Hit criterion | Result |
|---|---|---|
| k1 `k_pre_block_1h_32_fp8` | C-P4a | holds |
| k26 `k_flag_wait` | C-P4b | holds |
| k7 `k_conv_res2` | B-P3b only | holds |
| k10 `k_conv_splitk` | A-P1 | holds |
| k11 `k_qkv` | B-P3a ∧ P3b | holds |
| k33 `k_swin_var<256,false>` | B-P3a only | holds |

**306 field comparisons**: 303 are identical character by character; the remaining 3 are NFC/NFD equivalences of `é` (**substantive mismatches 0**).

### 1.7 Chapter Summary

| # | Conclusion |
|---|---|
| 1 | **A = 7 / B = 20 / C = 7**, totalling 34; the independent recomputation and the deliverable are **fully equal as per-kernel sets** |
| 2 | the thresholds **4096 / 32768 / 64 are self-set by this table, with no specification source whatsoever** |
| 3 | the recomputation under shifted bands is **item-by-item identical** across the three bands |
| 4 | class A **only** means the resource surface / parameter surface need no rewriting; "the operator can be mapped 1:1 to XMX" is marked as needing external documentation for 34/34 |
| 5 | `.wavefront_size` 32/64 is **not** a class B distinguishing criterion (34/34 hits) |
| 6 | class C's 64,640 B **does not exceed the 64 KiB limit** (896 B margin), **"already exceeds the limit" must not be written** |

---

## 2. Resource Adaptation

### 2.1 `group_segment_fixed_size`: LDS Repartitioning at a Maximum of 64,640 B

#### (a) Facts (272-entry scope)

**Full table of values + occurrence counts (21 deduplicated values, totalling 272)**:

| Value (B) | Hex | KiB | occurrences /272 |
|---|---|---|---|
| 0 | `0x0` | 0 | **84** |
| 15,616 | `0x3D00` | 15.25 | **24** |
| 24,576 | `0x6000` | 24.00 | **18** |
| 62,592 | `0xF480` | 61.125 | **16** |
| 16,384 | `0x4000` | 16.00 | **16** |
| 4,096 | `0x1000` | 4.00 | **16** |
| 8,192 | `0x2000` | 8.00 | **12** |
| **64,640** | **`0xFC80`** | **63.125** | **8** |
| 21,504 | `0x5400` | 21.00 | **8** |
| 19,200 | `0x4B00` | 18.75 | **8** |
| 15,632 | `0x3D10` | 15.265625 | **8** |
| 12,800 | `0x3200` | 12.50 | **8** |
| 6,144 | `0x1800` | 6.00 | **8** |
| 1,024 | `0x400` | 1.00 | **8** |
| 58,368 | `0xE400` | 57.00 | **6** |
| 28,928 | `0x7100` | 28.25 | **6** |
| 23,808 | `0x5D00` | 23.25 | **6** |
| 19,456 | `0x4C00` | 19.00 | **6** |
| 20,480 | `0x5000` | 20.00 | **2** |
| 17,152 | `0x4300` | 16.75 | **2** |
| 16,640 | `0x4100` | 16.25 | **2** |

**Threshold criteria**:

| Criterion | Measured value |
|---|---|
| number of entries with `>= 65536` (64 KiB) | **0** |
| maximum over all 272 entries | **64,640 B (`0xFC80` = 63.125 KiB)** |
| difference between the maximum and 65,536 B | **896 B (0.875 KiB)** |
| values in the `>= 60000` band | 64,640 × 8, 62,592 × 16 (24 entries in total) |

#### (b) Attribution scope for 64,640 (**both scopes hold and are not interchangeable**)

- **"value + occurrence count" scope**: 64,640 occurs **8 times** (one entry each for `#1`…`#8`);
- **matrix evidence**: those 8 entries **all fall at the same kernel position k1** = `_Z21k_pre_block_1h_32_fp89PreParams` (consistent `[64640]×8` across the 8 targets);
- **citation discipline**: because the occurrence count = 8 (≠ 1), one **must not** write "`k_pre_block_1h_32_fp8` = 64,640" without stating the scope.

**Correction of the same kind**: 58,368 occurs **6 times** and 28,928 occurs **6 times**; these are likewise "value + occurrence count" and **must not be attributed to a single point**.

#### (c) Adaptation advice for LDS repartitioning (**every item is a candidate / decision entry point; this document makes no selection**)

| # | Advice | Basis |
|---|---|---|
| A1 | **first establish an Xe-side measured query point for the SLM limit**, then judge whether 64,640 B can land. The criterion **must not** come from this DLL's bytes (there is no Xe criterion inside the DLL) | the fat binary **contains no Intel / Xe / SPIR-V target whatsoever** |
| A2 | that query point **does not yet exist in the existing self-developed project tree**: its runtime queries only `max_compute_units` / `global_mem_size` / `max_work_group_size`, and **does not query local memory (SLM) capacity** | that tree's runtime source file |
| A3 | account for `group_segment_fixed_size` per kernel as a **request amount**, and compare it per kernel against the Xe-side limit using the 34-row table of §3.5; the comparison result decides whether that kernel takes "1:1 recompilation" or "LDS tiled rewriting" | see §2.5 |
| A4 | **needs external documentation**: the **per-Xe-core SLM capacity limit** of Intel Arc B580 (Xe2 / Battlemage), and the name and semantics of the interface through which that limit can be queried in the SYCL runtime | direction in §8 G-06 |
| A5 | candidate repartitioning paths (**every item is a candidate, not a conclusion**): (a) keep the original LDS size and recompile 1:1; (b) split `group_segment_fixed_size` into multiple passes (tiling) according to the Xe SLM limit, moving the over-limit part out of SLM; (c) route part of the LDS content through global memory plus explicit synchronization. **The choice among the three depends on the measured limit from A4; this document makes no selection** | — |
| A6 | when repartitioning, **the semantics of the 66 B implicit parameter span and the 190 B tail must be preserved**: LDS repartitioning and the kernarg layout are two independent matters, and repartitioning LDS **must not** incidentally change kernarg offsets | §5.4 |
| A7 | the margin of **896 B (0.875 KiB)** must be written into the risk assessment: it is **the smallest margin** among all 272 entries, and any Xe-side SLM alignment / reserved overhead will consume it first | §2.1(a) |
| A8 | **must not** use the phrasing "64,640 B exceeds the SLM limit of a single Xe-core on Xe" | contradicts the bytes (`>= 65536` gets 0 hits) |
| A9 | **the first-level criterion for LDS repartitioning has not currently landed**: the **caller of** `swin_layer(SwinLDS&, unsigned char const*, BlobLayout const&, int)` is **not located** (`SwinLDS` is a parameter type name and cannot be mapped directly to a kernel name) ⇒ marked as needing external documentation | §4.6(c) |

### 2.2 Handling of `private_segment_fixed_size`

#### (a) Facts (272-entry scope)

| Value (B) | occurrences /272 | Note |
|---|---|---|
| 0 | **208** | the zero value accounts for 76.5% |
| **24** | **38** | — |
| 64 | **12** | — |
| 40 / 80 / 88 / 100 / 216 / 244 | **2** each | six items, 2 occurrences each |
| 404 | **1** | unique occurrence (k7 in `#8`) |
| 84 | **1** | unique occurrence (k25 in `#8`) |

Non-zero entries total = **64** (= 38 + 12 + 2×6 + 1 + 1).

**Per-target distribution of `= 24` (this quantity varies with target; there is no single set uniform across the 8 targets)**:

| Target | triple | kernels with `= 24` | count |
|---|---|---|---|
| 1 | gfx10-3-generic | k5, k8, k29, k30, k31, k32, k33 | **7** |
| 2 | gfx11-generic | k8, k33 | **2** |
| 3 | gfx1100 | k8, k29, k30, k33 | **4** |
| 4 | gfx1101 | k8, k29, k30, k33 | **4** |
| 5 | gfx1102 | k8, k33 | **2** |
| 6 | gfx1200 | k8, k29, k30, k31, k32, k33 | **6** |
| 7 | gfx1201 | k8, k29, k30, k31, k32, k33 | **6** |
| 8 | gfx9-generic | k5, k8, k29, k30, k31, k32, k33 | **7** |

Total **38 entries** = 7 + 2 + 4 + 4 + 2 + 6 + 6 + 7 ✅

- **kernels that are 24 across all 8 targets = k8 (`k_qkv_attn2`), k33 (`k_swin_var<256,false>`), two in total**;
- **same kernel with different values across targets** (raw byte evidence, bundle `#1`): k5 is 24 in `#1` (value byte `18`), 0 in `#2` (value byte `00`), and 24 in `#8` (value byte `18`);
- **a correction that must be carried forward**: **there is no "6 kernels" uniform across the 8 targets**.

#### (b) Adaptation advice

| # | Advice | Basis |
|---|---|---|
| B1 | when porting, **take the value cell by cell per kernel × target**; a single value must not be used to represent it | §2.2(a) |
| B2 | **the value set must be tabulated per target**: kernels of the k5 kind need 24 B in `#1` / `#8` and 0 B in `#2`–`#7` —— requesting uniformly by the maximum introduces unnecessary occupancy; requesting uniformly by 0 goes out of bounds in `#1` / `#8` | §2.2(a) |
| B3 | the **name of the counterpart and the allocation granularity** of the private segment on the Xe side must first be confirmed, before deciding "whether 24 B is an allocatable granularity" | needs external documentation, direction in B4 |
| B4 | **needs external documentation**: the **corresponding concept, minimum allocation granularity, and whether it shares the same capacity pool with SLM or the register file**, for "per-thread private memory / scratch / spill space" on Xe | direction in §8 G-12 |
| B5 | **do not infer Xe register counts from AMD's 24 B**: AMD's vgpr / sgpr and Xe's register file organization differ, and the two counts cannot be converted directly | §2.4 |
| B6 | the two **unique values** (404 B @ k7 / `#8`, 84 B @ k25 / `#8`) should be listed separately in the risk list: they are extremes that **occur only in `#8`**, showing that "taking parameters from some single target" will miss them | §2.2(a) |

### 2.3 The Impact of `wavefront_size` 32 / 64

#### (a) Facts

| Target | triple | `wavefront_size` distribution (34 kernels) |
|---|---|---|
| 1–7 | gfx10-3-generic / gfx11-generic / gfx1100 / gfx1101 / gfx1102 / gfx1200 / gfx1201 | `{32: 34}` per target |
| 8 | gfx9-generic | `{64: 34}` |

- 272-entry scope frequencies: **32 × 238** (= 7 × 34), **64 × 34** (= 1 × 34);
- **no single-point attribution**: both 32 and 64 are values of **the entire target dimension** ⇒ the difference in this field **lies entirely on the target axis**, with no difference on the kernel axis;
- raw byte evidence: bundle `#1` k0 value byte = `20` (positive fixint = 32); bundle `#8` k0 value byte = `40` (= 64).

#### (b) Impact analysis (**no conclusion is given wherever specific Xe values are involved**)

| # | Analysis item | Content | Label |
|---|---|---|---|
| C1 | the semantics of this field | `wavefront_size` is **AMD's wavefront width** | proven |
| C2 | different dimension | Intel Xe's SIMD width is expressed as **SIMD8 / SIMD16 / SIMD32** —— that expression comes from **external knowledge**, and there is no byte criterion for it in the workspace; according to that expression it is **not the same dimension** as AMD's 32/64; when recompiling one **must recompute the "work-item → thread" mapping according to the Xe target width** and **must not carry over 32 or 64** | needs external documentation |
| C3 | the target-axis difference of 32 vs 64 | 32 appears only in `#1`–`#7`; 64 appears only in `#8 gfx9-generic` ⇒ `#8` has one further systematic difference from `#1`–`#7` beyond the structural parameters | proven |
| C4 | the relation to XMX | **there is no criterion whatsoever in this workspace** that can map AMD's `wavefront_size` to the XMX execution model. The XMX execution unit is related to sub-group, but **that relation is unprovable in this workspace** (`sub_group` gets **0 hits** in the self-developed project tree) | unresolved |
| C5 | the current state of the existing self-developed implementation | the existing SYCL code uses scalar kernels with `item<1>` and **does not use** `nd_item` / `sub_group`; its GEMM part uses `joint_matrix` but **declares no sub-group size** | proven |
| C6 | **needs external documentation (no conclusion given)** | on Xe: **the value range of the sub-group size and how to specify it explicitly**; **the XMX execution model** (DPAS instruction form, required sub-group width, tile size constraints); and "whether XMX requires a specific sub-group width" | needs external documentation |
| C7 | **direction to look into** | see §8 G-05 | — |
| C8 | porting discipline | since C2 has already established "32 or 64 must not be carried over", **any phrasing that treats `wavefront_size` directly as the Xe SIMD width does not hold**; on the Xe side this field should be regarded as **used only to record the AMD original value** and not participating in the derivation of Xe execution parameters | proven |
| C9 | risk | the 64 of `#8 gfx9-generic` is an **isolated value** (34 of 272); if a unified strategy incorrectly takes `#8` as the baseline, it will skew all 34 records | proven |

### 2.4 Unified Strategy for the 8 Cross-Target Inconsistent Fields

#### (a) Quantitative scope of the inconsistency (**do not mix the three scopes**)

| Scope | Definition | Measured value |
|---|---|---|
| **scope 1: field × kernel pair** | among the 16 fields × 34 kernels = 544 (field, kernel) pairs, the number of pairs whose value is not fully identical across the 8 targets | **163** |
| **scope 2: cell count (compared with `#1`)** | taking `#1` as baseline, the number of cells where each non-`#1` target differs from `#1` (7 non-`#1` targets) | **605** |
| **scope 3: cell count (8 targets compared pairwise)** | the sum, per cell, of the number of pairwise-distinct pairs among the 8 targets | **2183** |
| Reference: total number of cells | 34 × 16 × 8 = **4352**; when compared with `#1` it is 34 × 16 × 7 = **3808** | — |

> **Scope discipline**: **163 is not a cell count**. Estimating as "163 × 7" gives 1141 (actual 605) and as "163 × 28" gives 4564 (actual 2183) —— **both are wrong**.

**Per-field breakdown for scope 1 (the 8 inconsistent fields)**:

| Field | kernels not fully identical / 34 |
|---|---|
| `.sgpr_count` | **34** |
| `.wavefront_size` | **34** |
| `.workgroup_processor_mode` | **34** |
| `.vgpr_count` | **31** |
| `.group_segment_fixed_size` | **11** |
| `.private_segment_fixed_size` | **10** |
| `.vgpr_spill_count` | **6** |
| `.sgpr_spill_count` | **3** |
| **total** | **163** |

**The 8 consistent fields (directly reusable on the Xe side)**: `.kernarg_segment_size`, `.kernarg_segment_align`, `.max_flat_workgroup_size`, `.uniform_work_group_size`, `.uses_dynamic_stack`, `.language`, `.language_version`, `.symbol`.

#### (b) Summary of the unified strategy (across the 8 fields)

| Field | Unified strategy class | Can it be retained as an execution parameter on the Xe side |
|---|---|---|
| `.group_segment_fixed_size` | **must be recomputed against the Xe limit** (candidate: take the 8-target maximum) | **yes** (as the SLM request amount), but the value must be re-verified |
| `.private_segment_fixed_size` | **must be recomputed against the Xe granularity** (candidate: take the maximum of the union) | **yes** (as the private-memory request amount), but the value must be re-verified |
| `.sgpr_count` | **discard** (retain as pressure reference) | **no** |
| `.sgpr_spill_count` | **discard** (retain as reference) | **no** |
| `.vgpr_count` | **discard** (retain as pressure reference) | **no** |
| `.vgpr_spill_count` | **discard** (retain as reference) | **no** |
| `.wavefront_size` | **discard** (record the original value only) | **no** |
| `.workgroup_processor_mode` | **discard** (rebuild from Xe's own mode) | **no** |

**Basis for the two classes of strategy**:

- **The six fields are discarded without exception**: ① the four register fields are AMD compiler-output counts and are **themselves mutually different across the 8 AMD targets** (`.sgpr_count` 58 values, `.vgpr_count` 84 values) ⇒ **there is no unique value to take as Xe-side input**; ② the `.wavefront_size` difference **lies only on the target axis** ⇒ it is a **target property**, not a kernel property; ③ `.workgroup_processor_mode` is **entirely absent** in `#8` ⇒ "cross-target common input" does not hold.
- **Two fields must be re-verified against the Xe limit**: ① both fields **have a value distribution** across the 8 targets (21 / 11 deduplicated values) and **no cross-target common value exists**; ② their semantics is a resource request amount (SLM / private segment), **directly coupled** with Xe-side capacity constraints.

**Judgement for this section**: out-of-bounds inference of specific Xe values = **0 occurrences**.

#### (c) Xe-side items to look up for each field

| Field | Items to look up (needs external documentation, no conclusion given) |
|---|---|
| `.group_segment_fixed_size` | the per-Xe-core SLM limit on Xe; the semantics of the value returned by SYCL `info::device::local_mem_size` (whether it includes reserved overhead); the alignment granularity of SLM requests on Xe |
| `.private_segment_fixed_size` | the minimum allocation granularity of per-thread private memory / scratch on Xe; whether it **shares a capacity pool** with SLM / the register file; how spill space is expressed on Xe |
| `.sgpr_count` / `.vgpr_count` | the Xe register file organization and the **number of registers per thread**; the **queryable / observable interface** for register pressure on Xe; whether a **conversion relation exists** between AMD sgpr / vgpr and the Xe register file (**existence is not presupposed**) |
| `.sgpr_spill_count` / `.vgpr_spill_count` | how spill is determined and reported on Xe; the quantitative measure of spill's impact on Xe performance |
| `.wavefront_size` | the Xe sub-group size range and how to specify it; the XMX execution model |
| `.workgroup_processor_mode` | whether a concept corresponding to the semantics of this AMD key exists on Xe; if so, its value space and default value |

**Summary of directions to look into**: the "Register Pressure" / "Spilling" / "Local Memory" / "Work-group Size" chapters of the Intel oneAPI GPU Optimization Guide; IGC (Intel Graphics Compiler) documentation; the SYCL 2020 specification; the oneAPI Level Zero specification; the Intel Arc B-series architecture whitepaper.

#### (d) Additional field-level facts (**the two scopes must be written separately**)

| Field | Fact |
|---|---|
| `.sgpr_count` | **58 deduplicated values** (272 entries), maximum **107** (occurs 7 times); per-target extremes: `#1`–`#7` max = 107 (k7), `#8` max = **104** (k7 / k29 **tied**) |
| `.vgpr_count` | **84 deduplicated values** (272 entries), maximum **202** (occurs 2 times); per-target extremes: `#1` max = 145 (k7), `#2`–`#5` max = **194** (k0 / k1 / k2 **tied**), `#6` / `#7` max = **202** (k7), `#8` max = **122** (k14 only) |
| `.sgpr_spill_count` | 8 deduplicated values: `0×262`, `43×2`, `45×2`, `64×2`, `133×1`, `29×1`, `6×1`, `69×1`. **number of non-zero entries = 10**, **number of distinct values (including 0) = 8**, **number of distinct non-zero values = 7** —— **an older document treated "8" as the entry count** |
| `.vgpr_spill_count` | 8 deduplicated values: `0×258`, `17×4`, `20×2`, `7×2`, `75×2`, `88×2`, `100×1`, `23×1`. **number of non-zero entries = 14**, **number of distinct values (including 0) = 8** |

### 2.5 Per-Kernel Resource Adaptation Advice Table (34 rows)

**Column definitions**: `group` = the 8-target **value set** of `.group_segment_fixed_size`; `priv` = the 8-target **value set** of `.private_segment_fixed_size`; `vgpr_max` / `sgpr_max` = the 8-target **maximum** (reference for pressure only); `maxWG` = `.max_flat_workgroup_size` (8 targets consistent); `wave` = the 8-target value set.

**Class code definitions (each code with its basis)**:

| Code | Definition | Basis |
|---|---|---|
| **α** | `group` maximum ≥ 60,000 B (band close to the 64 KiB limit) | `64,640 × 8 + 62,592 × 16` |
| **β** | `group` maximum ∈ [24,576, 60,000) (mid-to-high band) | §2.1(a) |
| **γ** | `group` maximum ∈ (0, 24,576) (mid-to-low band) | §2.1(a) |
| **δ** | `group` = 0 (no SLM requested in any of the 8 targets) | `0 × 84` |
| **P** | `priv` non-zero and containing ≥ 2 distinct values | §2.2(a) |
| **p** | `priv` non-zero with a **single value** across the 8 targets | §2.2(a) (only k8, k33) |
| **W** | `maxWG` = 1024 (highest work-group bound band) | §2.4(a) |
| **X** | `priv` contains a **uniquely occurring** extreme (404 or 84) | §2.2(a) |

| # | mangled (`.name`) | semantics | kernarg | group | priv | vgpr_max | sgpr_max | maxWG | wave | code | adaptation advice | items to look up |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `_Z16k_swin_1h_32_fp810SwinParams` | `k_swin_1h_32_fp8(SwinParams)` | 296 | 62592 | {0, 64} | 194 | 35 | 256 | 32/64 | **α P** | SLM fixed value 61.125 KiB → verify per target against the Xe limit; `priv` takes the union {0,64} → request uniformly as 64 B; the `vgpr_max` 194 is a tied extreme across `#2`–`#5`, for reference only | A4, B4 |
| 1 | `_Z21k_pre_block_1h_32_fp89PreParams` | `k_pre_block_1h_32_fp8(PreParams)` | 336 | **64640** | {0, 64} | 194 | 79 | 256 | 32/64 | **α P** | **the entry with the smallest margin among all 272** (only 896 B from 65,536 B) → **the first item on the risk list**; LDS repartitioning **should prioritize this kernel**; `priv` union 64 B | A4, B4 |
| 2 | `_Z22k_post_block_1h_32_fp810PostParams` | `k_post_block_1h_32_fp8(PostParams)` | 336 | 62592 | {0, 64} | 194 | 52 | 256 | 32/64 | **α P** | same SLM handling as #0; `priv` union 64 B | A4, B4 |
| 3 | `_Z6k_ffwd10FfwdParams` | `k_ffwd(FfwdParams)` | 288 | {0, 24576} | 0 | 112 | 28 | 256 | 32/64 | **β** | `group` across targets {0, 24576} (0 appears in `#1` / `#8`) → request uniformly as 24576 B, **must not be requested as 0** | A4 |
| 4 | `_Z10k_conv_res10ConvParams` | `k_conv_res(ConvParams)` | 296 | {0, 8192} | 0 | 87 | 29 | 256 | 32/64 | **γ** | `group` {0, 8192} → uniformly 8192 B | A4 |
| 5 | `_Z10k_qkv_attn10AttnParams` | `k_qkv_attn(AttnParams)` | 296 | {20480, 58368} | **{0, 24}** | 102 | 62 | 256 | 32/64 | **β P** | `group` across targets differs by **2.85×** (20480 ↔ 58368) → uniformly 58368 B; `priv` {0,24} → 24 B; **the representative of "largest cross-target value difference for a single kernel"** (raw bytes `18` / `00` / `18`) | A4, B4 |
| 6 | `_Z7k_ffwd211Ffwd2Params` | `k_ffwd2(Ffwd2Params)` | 304 | {0, 21504} | 0 | 90 | 54 | 256 | 32/64 | **γ** | `group` {0, 21504} → 21504 B | A4 |
| 7 | `_Z11k_conv_res211Conv2Params` | `k_conv_res2(Conv2Params)` | 320 | 0 | **{0, 404}** | 202 | 107 | 256 | 32/64 | **δ P X** | `group` = 0 across all 8 targets (no SLM requested); `priv` contains the **unique extreme 404 B (`#8` only)**; `vgpr_max` 202 and `sgpr_max` 107 are both at the whole-library extreme band → highest register pressure, for reference only | B4 |
| 8 | `_Z11k_qkv_attn210AttnParams` | `k_qkv_attn2(AttnParams)` | 296 | {21504, 23808} | **24** | 144 | 49 | 256 | 32/64 | **γ p** | `group` {21504, 23808} → 23808 B; `priv` **a single 24 B across the 8 targets** (only 2 such kernels in the whole library) → can carry over 24 B directly | A4, B4 |
| 9 | `_Z8k_expand12ExpandParams` | `k_expand(ExpandParams)` | 280 | {0, 16384} | 0 | 90 | 21 | 256 | 32/64 | **γ** | `group` {0, 16384} → 16384 B | A4 |
| 10 | `_Z13k_conv_splitk12ConvParams1d` | `k_conv_splitk(ConvParams1d)` | 304 | 4096 | 0 | 82 | 42 | 256 | 32/64 | **γ** | `group` fixed at 4096 B (8 targets consistent) | A4 |
| 11 | `_Z5k_qkv9QkvParams` | `k_qkv(QkvParams)` | 296 | 6144 | 0 | 119 | 106 | 256 | 32/64 | **γ** | `group` fixed at 6144 B; `sgpr_spill_count` in `#8` = 29 (one of the 10 non-zero entries) → for reference only | A4 |
| 12 | `_Z11k_attention12AttnParams1d` | `k_attention(AttnParams1d)` | 296 | {16640, 28928} | 0 | 144 | 48 | 256 | 32/64 | **β** | `group` {16640, 28928} → 28928 B. **Note**: under the 272-entry scope, 28,928 occurs **6 times**, which is in the "value + occurrence count" scope and **must not be written as "`k_attention1` = 28,928"** | A4 |
| 13 | `_Z9k_expand212ExpandParams` | `k_expand2(ExpandParams)` | 280 | 0 | 0 | 93 | 29 | 256 | 32/64 | **δ** | `group` = 0 and `priv` = 0 across all 8 targets ⇒ no local-memory request on the Xe side | — |
| 14 | `_Z11k_contract212ConvParams1d` | `k_contract2(ConvParams1d)` | 304 | 16384 | 0 | 161 | 69 | 256 | 32/64 | **γ** | `group` fixed at 16384 B | A4 |
| 15 | `_Z6k_qkv29QkvParams` | `k_qkv2(QkvParams)` | 296 | 12800 | 0 | 119 | 34 | 256 | 32/64 | **γ** | `group` fixed at 12800 B | A4 |
| 16 | `_Z12k_attention212AttnParams1d` | `k_attention2(AttnParams1d)` | 296 | {17152, 19456} | 0 | 107 | 49 | 256 | 32/64 | **γ** | `group` {17152, 19456} → 19456 B | A4 |
| 17 | `_Z14k_ffwd_inpview12FfwdPlParams` | `k_ffwd_inpview(FfwdPlParams)` | 288 | {0, 24576} | 0 | 112 | 28 | 256 | 32/64 | **β** | `group` {0, 24576} → 24576 B | A4 |
| 18 | `_Z16k_conv_res_views12ConvPlParams` | `k_conv_res_views(ConvPlParams)` | 328 | {16384, 24576} | 0 | 137 | 68 | 256 | 32/64 | **β** | `group` {16384, 24576} → 24576 B; `kernarg` 328 is one of the 12 values | A4 |
| 19 | `_Z12k_final_head10HeadParams` | `k_final_head(HeadParams)` | 280 | {0, 8192} | 0 | 84 | 18 | 256 | 32/64 | **γ** | `group` {0, 8192} → 8192 B | A4 |
| 20 | `_Z8k_repack12RepackParams` | `k_repack(RepackParams)` | 288 | 0 | 0 | 18 | 30 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; **`maxWG` = 1024** (one of the 8 kernels) → the highest work-group bound band, must be verified jointly against the Xe work-group limit | A4, **D1** |
| 21 | `_Z14k_dec_upsample11DecUpParams` | `k_dec_upsample(DecUpParams)` | 296 | 4096 | 0 | 81 | 29 | 256 | 32/64 | **γ** | `group` fixed at 4096 B | A4 |
| 22 | `_Z6k_mean10MeanParams` | `k_mean(MeanParams)` | 288 | 1024 | 0 | 11 | 22 | **1024** | 32/64 | **γ W** | `group` 1024 B; `maxWG` = 1024 | A4, **D1** |
| 23 | `_Z8k_import12ImportParams` | `k_import(ImportParams)` | 304 | 0 | 0 | 21 | 22 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; `maxWG` = 1024 | **D1** |
| 24 | `_Z8k_export12ExportParams` | `k_export(ExportParams)` | 320 | 0 | 0 | 26 | 19 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; `maxWG` = 1024 | **D1** |
| 25 | `_Z11k_reproject12ReprojParams` | `k_reproject(ReprojParams)` | **384** | 0 | **{0, 84}** | 72 | 48 | **1024** | 32/64 | **δ P W X** | `group` all 0; `priv` contains the **unique extreme 84 B (`#8` only)**; `maxWG` = 1024; **`kernarg` = 384 (the existing table's 128 is wrong)** | B4, **D1** |
| 26 | `_Z11k_flag_waitPjjj` | `k_flag_wait(Pjjj)` | **16** | 0 | 0 | 2 | 12 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; `maxWG` = 1024; **one of the 3 exception kernels** (no hidden parameters, no 190 B tail) → the kernarg concatenation rule differs | **D1**, §4.4 |
| 27 | `_Z13k_align_probePh` | `k_align_probe(Ph)` | **8** | 0 | 0 | 3 | 4 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; `maxWG` = 1024; **one of the 3 exception kernels, and the only one with no `by_value` parameter** | **D1**, §4.4 |
| 28 | `_Z10k_flag_setPjj` | `k_flag_set(Pjj)` | **12** | 0 | 0 | 2 | 10 | **1024** | 32/64 | **δ W** | `group` / `priv` all 0; `maxWG` = 1024; **one of the 3 exception kernels**; **`kernarg` = 12 (the existing table's 16 is wrong)**; 12 **is not a multiple of 8** | **D1**, §4.4 |
| 29 | `_Z10k_swin_varILi32ELb1EEv9VarParams` | `k_swin_var<32, true>(VarParams)` | 424 | 15616 | **{24, 100}** | 96 | 104 | 256 | 32/64 | **γ P** | `group` fixed at 15616 B; `priv` {24, 100} → 100 B; `sgpr_max` 104 is the `#8` tied extreme (with #7) | A4, B4 |
| 30 | `_Z10k_swin_varILi32ELb0EEv9VarParams` | `k_swin_var<32, false>(VarParams)` | 424 | 15632 | **{24, 40}** | 91 | 102 | 256 | 32/64 | **γ P** | `group` fixed at 15632 B (**differs from the 15616 of #29 / #31 / #32 by 16 B**); `priv` {24, 40} → 40 B | A4, B4 |
| 31 | `_Z10k_swin_varILi64ELb0EEv9VarParams` | `k_swin_var<64, false>(VarParams)` | 424 | 15616 | **{24, 88, 244}** | 120 | 70 | 256 | 32/64 | **γ P** | `group` fixed at 15616 B; `priv` has **3 values** {24, 88, 244} → 244 B; `vgpr_spill_count` non-zero (`#2` / `#5` = 75, `#3` / `#4` = 17) | A4, B4 |
| 32 | `_Z10k_swin_varILi128ELb0EEv9VarParams` | `k_swin_var<128, false>(VarParams)` | 424 | 15616 | **{24, 80, 216}** | 120 | 69 | 256 | 32/64 | **γ P** | `group` fixed at 15616 B; `priv` has **3 values** {24, 80, 216} → 216 B; `vgpr_spill_count` non-zero (`#2` / `#5` = 88, `#3` / `#4` = 17) | A4, B4 |
| 33 | `_Z10k_swin_varILi256ELb0EEv9VarParams` | `k_swin_var<256, false>(VarParams)` | 424 | 19200 | **24** | 136 | 70 | 256 | 32/64 | **γ p** | `group` fixed at 19200 B (**the largest in the `k_swin_var` series**); `priv` **a single 24 B across the 8 targets** → can be carried over directly | A4, B4 |

**Item to look up `D1` (newly added by this table, 8 references)**:

> **needs external documentation (no conclusion given)**: the **maximum number of work-items per work-group** on Intel Arc B580, and its **joint constraint relationship** with the SLM / register budget. **Directions to look into**: ① SYCL 2020 specification `info::device::max_work_group_size`; ② the "Work-group Size" chapter of the Intel oneAPI GPU Optimization Guide; ③ the maximum work-group limit for kernels in the Level Zero specification; ④ the existing self-developed code already queries `max_work_group_size` at runtime (which can serve as an **access point**, but that query returns a **device-level** limit, and whether it equals the **kernel-level** feasible limit **must be confirmed separately**).

**Statistical summary (for risk ranking)**:

| Statistic | Value |
|---|---|
| number of kernels with code **α** (`group` ≥ 60000) | **3** (#0, #1, #2) |
| number of kernels with code **β** (`group` ∈ [24576, 60000)) | **5** (#3, #5, #12, #17, #18) |
| number of kernels with code **γ** (`group` ∈ (0, 24576)) | **17** |
| number of kernels with code **δ** (`group` all 0) | **9** (#7, #13, #20, #23, #24, #25, #26, #27, #28) |
| number of kernels with code **P** (`priv` non-zero and ≥2 values) | **10** (#0, #1, #2, #5, #7, #25, #29, #30, #31, #32) |
| number of kernels with code **p** (`priv` non-zero and a single value) | **2** (#8, #33) |
| number of kernels with code **W** (`maxWG` = 1024) | **8** (#20, #22, #23, #24, #25, #26, #27, #28) |
| number of kernels with code **X** (`priv` contains a unique extreme) | **2** (#7 = 404, #25 = 84) |
| number of kernels with `priv` non-zero in any target | **12** (= P's 10 + p's 2) |
| number of kernels with `priv` = 0 across all 8 targets | **22** (34 − 12) |
| number of **non-zero** kernels with `group` consistent across all 8 targets | **14** |
| number of kernels with `group` = 0 across all 8 targets | **9** |
| number of kernels whose `group` varies across targets | **11** |
| identity | `14 + 9 + 11 = 34` ✅; `α + β + γ + δ = 34` ✅; `P + p = 12` ✅ |

**All 16 statistics agree, including 3 identities.**

> **Scope clarification (code P)**: the criterion for code `P` is "`priv` non-zero **and** taking ≥ 2 distinct values across the 8 targets" = **10 kernels**; code `p` (non-zero and a single value) = **2**; their sum = the **12 kernels** with `priv` non-zero in any target. **Do not** use "the number of code P kernels" in place of "the number of kernels requiring a private segment".

**Sampling record**: **8 kernels** were sampled (#0 / #1 / #5 / #7 / #8 / #25 / #28 / #33). **The class code, kernarg, group set, priv set, vgpr_max, sgpr_max, maxWG agree 8/8 item by item**, and after **independently deriving** the class code from the measured vectors (without going through the documentation) it is **identical item by item** to the documented code.

### 2.6 Chapter Summary

| # | Conclusion |
|---|---|
| 3-1 | `group` maximum **64,640 B**, **896 B** from the 64 KiB limit, `≥65536` gets **0** hits; **does not exceed the limit** |
| 3-2 | `group` 21 values / 272 entries **agree value by value and occurrence by occurrence** |
| 3-3 | `priv` 11 values; `24 × 38`; per-target `= 24` kernel counts **7/2/4/4/2/6/6/7**; **there is no single set uniform across the 8 targets** |
| 3-4 | `wavefront_size` **32 × 238 / 64 × 34**; the difference is **only on the target axis**; **32 or 64 must not be carried over** |
| 3-5 | 8 inconsistent fields (scope 1 total **163**); 6 fields discarded / 2 fields re-verified, **both classes of strategy have measured bases**; **out-of-bounds inference of Xe values 0 occurrences** |
| 3-6 | the 34-row adaptation table + statistical summary **all 16 statistics agree**, including 3 identities |
| 3-7 | the **8** kernels with `maxWG` = 1024 must be verified jointly against the Xe work-group limit (**item to look up D1**) |

---

## 3. Operator Mapping

> **The highest discipline of this chapter**: for any **specific capability** involving Intel Xe / SPIR-V / XMX, **the item is always marked as needing external documentation with the direction to look into, and no conclusion is given**.

### 3.1 The Strength Ceiling of the Semantic Evidence Chain (**must be stated first, otherwise the table below will be misread**)

**The strongest evidence level attainable within this environment = "name-based inference"**, for the reason of four refutations (**each of which is confirmed**):

| Refutation | Content | Search range | Pattern | Hit count |
|---|---|---|---|---|
| ① source path ruled out | the whole DLSS-NR project tree on the OptiScaler side | the whole tree | `hipLaunchKernel` / the 34 kernel names / `encoder\|bottleneck\|decoder\|num_blocks\|block_idx\|swin` / DLL-embedded shader text among the 366 `.hlsl` | **0 each** |
| ② comparison module does not hold | the NVIDIA-side module = interface layer | whole file | real CUDA / PTX / ELF magics | **0** |
| ③ no AMD hardware | the runtime observation path is unavailable | — | — | — |
| ④ **operator-name scan inside the DLL** | the whole file `dlssnr_amd_pass1.dll`, 7,156,224 B (latin1 direct search, **covering the whole library**) | whole file | `softmax` / `silu` / `gelu` / `layernorm` / `matmul` / `gemm` / `wmma` / `mfma` / `dpas` / `xmx` / `subgroup` / `reduce`, etc. | **0 each** |

**Conclusion (the decidable part)**: the operator types in this table are **name-based inference** (basis = the literal mangled kernel names + the literal user parameter struct names + parameter sizes + resource fields + code sizes); for k0, k29–k33 there is additionally a re-implementation in the self-developed project tree to refer to, but **that tree is a re-implementation, not the build source of this DLL**, so what it gives is **that tree author's semantic understanding**, **not** a byte-level proof of the semantics of the device code inside the DLL. ⇒ **This table does not constitute a verification conclusion about operator semantics.**

### 3.2 The 34-Row Operator Mapping Table

**Column notes**: the `XMX direct support` column = **all 34/34 marked as needing external documentation**; this table **gives no conclusion whatsoever**. The `existing implementation on the XMX side` column = the re-implementation location inside the self-developed project tree (**this column does not mean "that implementation runs on XMX hardware"**, see §3.4); `codesz` = that kernel's code symbol `st_size` (8-target values).

| # | kernel name | operator type (**name-based inference**) | structural characteristics (decidable part) | XMX direct support | existing implementation on the XMX side | recommended path |
|---|---|---|---|---|---|---|
| k0 | `k_swin_1h_32_fp8` | Swin shifted-window operator (1 head / 32 channels / FP8) | `B` = 40 + H13; `group` = 62,592 (8/8 consistent); `priv` = 0/64×4/0×3; `maxWG` = 256; `codesz` = 40364 / 4152×4 / 14528×2 / 38184 | **needs external documentation** (T-01, T-03) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-03, T-15) |
| k1 | `k_pre_block_1h_32_fp8` | network block pre-processing (1 head / 32 channels / FP8) | `B` = 80 + H13; `group` = **64,640 (the maximum over all 272 entries)**, 896 B below the limit (8/8 consistent); `codesz` = 45056 / 9764×4 / 19536×2 / 43276 | **needs external documentation** (T-01, T-08) | **no** (0 hits across that whole tree) | **needs external documentation** (T-08, T-09, T-15) |
| k2 | `k_post_block_1h_32_fp8` | network block post-processing (1 head / 32 channels / FP8) | `B` = 80 + H13; `group` = 62,592 (8/8 consistent); `codesz` = 43088 / 7196×4 / 18164×2 / 41160 | **needs external documentation** (T-01, T-08) | **no** | **needs external documentation** (T-08, T-15) |
| k3 | `k_ffwd` | feed-forward transform | `B` = 32 + H13; `group` = 0/24576×6/0 (**inconsistent across targets**); `codesz` = 688 / 19800 / 19612×2 / 19800 / 6044×2 / 660 | **needs external documentation** (T-01, T-16) | **no** | **needs external documentation** (T-08, T-15) |
| k4 | `k_conv_res` | convolution + residual | `B` = 40 + H13; `group` = 0/8192×6/0 (**inconsistent across targets**); `codesz` = 4580 / 8732 / 8512×2 / 8732 / 3516×2 / 4308 | **needs external documentation** (T-02) | **no** | **needs external documentation** (T-02, T-15) |
| k5 | `k_qkv_attn` | QKV projection + attention | `B` = 40 + H13; `group` = 20480/58368×6/20480 (**inconsistent across targets**); `priv` = 24…24; `codesz` = 35392 / 87752×4 / 9192×2 / 33560 | **needs external documentation** (T-01, T-04) | **no** | **needs external documentation** (T-01, T-04, T-15) |
| k6 | `k_ffwd2` | feed-forward 2 | `B` = 48 + H13; `group` = 0/21504×6/0 (**inconsistent across targets**); `codesz` = 1712 / 30660 / 30340 / 30336 / 30660 / 7460×2 / 1376 | **needs external documentation** (T-01, T-16) | **no** | **needs external documentation** (T-08, T-15) |
| k7 | `k_conv_res2` | convolution + residual 2 | `B` = 64 + H13; `group` = 0 (**8/8 consistent**); `priv` = 0×7 / **404 (`#8`)**; `codesz` = 27444 / 33996 / 33992×2 / 33996 / 23412×2 / 30552 | **needs external documentation** (T-02) | **no** | **needs external documentation** (T-02, T-10) |
| k8 | `k_qkv_attn2` | QKV projection + attention 2 | `B` = 40 + H13; `group` = 21504/23808×6/21504 (**inconsistent across targets**); `priv` = **24 (8/8 consistent)**; `codesz` = 16984 / 31212×4 / 8952×2 / 16000 | **needs external documentation** (T-01, T-04) | **no** | **needs external documentation** (T-01, T-04) |
| k9 | `k_expand` | tensor expansion (Expand) | `B` = 24 + H13; `group` = 0/16384×6/0 (**inconsistent across targets**); `codesz` = 1288 / 13520 / 13364×2 / 13520 / 3908×2 / 1048 | **needs external documentation** (T-04, T-19) | **no** | **needs external documentation** (T-15, T-19) |
| k10 | `k_conv_splitk` | split-K convolution | `B` = 48 + H13; `group` = 4,096 (**8/8 consistent**); `codesz` = 3632 / 8992×4 / 7480×2 / 3508 | **needs external documentation** (T-02) | **no** | **needs external documentation** (T-02, T-11) |
| k11 | `k_qkv` | QKV projection | `B` = 40 + H13; `group` = 6,144 (**8/8 consistent**); `codesz` = 41596 / 77136 / 77128×2 / 77136 / 6076×2 / 39724 | **needs external documentation** (T-01) | **no** | **needs external documentation** (T-01, T-15) |
| k12 | `k_attention` | attention | `B` = 40 + H13; `group` = 16640/28928×6/16640 (**inconsistent across targets**); `codesz` = 2060 / 43664 / 43656×2 / 43664 / 6664×2 / 1948 | **needs external documentation** (T-01, T-04, T-06) | **no** | **needs external documentation** (T-01, T-04, T-06) |
| k13 | `k_expand2` | tensor expansion 2 | `B` = 24 + H13; `group` = 0 (**8/8 consistent**); `codesz` = 1300 / 19280 / 19356×2 / 19280 / 4928×2 / 1012 | **needs external documentation** (T-04, T-19) | **no** | **needs external documentation** (T-15, T-19) |
| k14 | `k_contract` | tensor contraction (Contract) | `B` = 48 + H13; `group` = 16,384 (**8/8 consistent**); `codesz` = 18740 / 26064 / 26108×2 / 26064 / 19404×2 / 15960 | **needs external documentation** (T-04, T-19) | **no** | **needs external documentation** (T-15, T-19) |
| k15 | `k_qkv2` | QKV projection 2 | `B` = 40 + H13; `group` = 12,800 (**8/8 consistent**); `codesz` = 12300 / 21768×5 / 8492×2 / 11208 | **needs external documentation** (T-01) | **no** | **needs external documentation** (T-01, T-15) |
| k16 | `k_attention2` | attention 2 | `B` = 40 + H13; `group` = 17152/19456×6/17152 (**inconsistent across targets**); `codesz` = 3564 / 10228 / 10008×2 / 10228 / 7564×2 / 3424 | **needs external documentation** (T-01, T-04, T-06) | **no** | **needs external documentation** (T-01, T-04, T-06) |
| k17 | `k_ffwd_inpview` | feed-forward (with the input-view parameter `FfwdPlParams`) | `B` = 32 + H13; `group` = 0/24576×6/0 (**inconsistent across targets**); `codesz` = 688 / 18600 / 18412×2 / 18600 / 4788×2 / 660 | **needs external documentation** (T-01, T-18) | **no** | **needs external documentation** (T-18, T-15) |
| k18 | `k_conv_res_views` | convolution + residual (with the view parameter `ConvPlParams`) | `B` = 72 + H13; `group` = 16384/24576×6/16384 (**inconsistent across targets**); `codesz` = 6012 / 13304 / 13140×2 / 13304 / 7304×2 / 5628 | **needs external documentation** (T-02, T-18) | **no** | **needs external documentation** (T-02, T-18) |
| k19 | `k_final_head` | final output head (Head) | `B` = 24 + H13; `group` = 0/8192×6/0 (**inconsistent across targets**); `codesz` = 384 / 7184 / 6956×2 / 7184 / 2936×2 / 288 | **needs external documentation** (T-01) | **no** | **needs external documentation** (T-15) |
| k20 | `k_repack` | data repacking (Repack) | `B` = 32 + H13; `group` = 0 (**8/8 consistent**); `maxWG` = **1024**; `codesz` = 856 / 1000×5 / 1032×2 / 796 | **needs external documentation** (T-04) | **no** | **needs external documentation** (T-15) |
| k21 | `k_dec_upsample` | decoder upsampling (Upsample) | `B` = 40 + H13; `group` = 4,096 (**8/8 consistent**); `codesz` = 1248 / 15128 / 15120 / 15116 / 15128 / 3348×2 / 1184 | **needs external documentation** (T-18, T-06) | **no** | **needs external documentation** (T-18, T-06) |
| k22 | `k_mean` | mean / reduction (Mean) | `B` = 32 + H13; `group` = 1,024 (**8/8 consistent**); `maxWG` = **1024**; `codesz` = 1084 / 1256×5 / 1272×2 / 1028 | **needs external documentation** (T-06, T-05) | **no** | **needs external documentation** (T-06, T-05) |
| k23 | `k_import` | data import (Import) | `B` = 48 + H13; `group` = 0 (**8/8 consistent**); `maxWG` = **1024**; `codesz` = 4324 / 5200×5 / 5520×2 / 4588 | **needs external documentation** (T-04) | **no** | **needs external documentation** (T-14, T-15) |
| k24 | `k_export` | data export (Export) | `B` = 64 + H13; `group` = 0 (**8/8 consistent**); `maxWG` = **1024**; `codesz` = 5440 / 6592×5 / 6960×2 / 5628 | **needs external documentation** (T-04) | **no** | **needs external documentation** (T-14, T-15) |
| k25 | `k_reproject` | reprojection (Reproject) | `B` = **128** (the second largest user struct among the 34) + H13; `kernarg` = **384**; `group` = 0; `priv` = 0×7 / **84 (`#8`)**; `maxWG` = **1024**; `codesz` = 10036 / 12260 / 12272×2 / 12260 / 12992×2 / 11376 | **needs external documentation** (T-18, T-04) | **no** | **needs external documentation** (T-18, T-10) |
| k26 | `k_flag_wait` | flag wait (synchronization primitive; mangled `Pjjj` = `unsigned int*` + 3 × `unsigned int`) | **no H13, no tail**; parameters = `0/8/global_buffer` + `8/4/by_value` + `12/4/by_value`; `kernarg` = 16; `maxWG` = **1024**; `codesz` = 112 / 116×4 / 124×2 / 112 | **needs external documentation** (T-11, T-12, T-13) | **no** | **needs external documentation** (T-11, T-12, T-13) |
| k27 | `k_align_probe` | alignment probe (synchronization / barrier helper; mangled `Ph` = `unsigned char*`, **no `by_value` parameter**) | **no H13, no tail, no `by_value`**; parameters = `0/8/global_buffer` (the only one); `kernarg` = 8; `maxWG` = **1024**; `codesz` = 4 / 52×4 / 56×2 / 4 (**the smallest of all 34 kernels**) | **needs external documentation** (T-11, T-12) | **no** | **needs external documentation** (T-11, T-12) |
| k28 | `k_flag_set` | flag set (synchronization primitive; mangled `Pjj` = `unsigned int*` + `unsigned int`) | **no H13, no tail**; parameters = `0/8/global_buffer` + `8/4/by_value`; `kernarg` = **12**; `maxWG` = **1024**; `codesz` = 92×5 / 124×2 / 72 | **needs external documentation** (T-11, T-12, T-13) | **no** | **needs external documentation** (T-11, T-12, T-13) |
| k29 | `k_swin_var<32,true>` | variable-window Swin transform (window 32, template bool = true) | `B` = **168** (`VarParams`, the largest among the 34) + H13; `group` = 15,616; `priv` = 24/100/24/24/100/24/24/24; `codesz` = 35156 / 81756 / 80128×2 / 81756 / 29580×2 / 34020 | **needs external documentation** (T-01, T-03, T-17) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-17) |
| k30 | `k_swin_var<32,false>` | variable-window Swin transform (window 32, template bool = false) | `B` = 168 + H13; `group` = 15,632; `priv` = 24/40/24/24/40/24/24/24; `codesz` = 38044 / 84880 / 83724×2 / 84880 / 29256×2 / 36568 | **needs external documentation** (T-01, T-03, T-17) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-17) |
| k31 | `k_swin_var<64,false>` | variable-window Swin transform (window 64) | `B` = 168 + H13; `group` = 15,616; `priv` = 24/244/88/88/244/24/24/24; `codesz` = 29552 / 91924 / 90116×2 / 91924 / 23148×2 / 27856 | **needs external documentation** (T-01, T-03, T-17) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-17) |
| k32 | `k_swin_var<128,false>` | variable-window Swin transform (window 128) | `B` = 168 + H13; `group` = 15,616; `priv` = 24/216/80/80/216/24/24/24; `codesz` = 28584 / 86900 / 84572×2 / 86900 / 25876×2 / 26948 | **needs external documentation** (T-01, T-03, T-17) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-17) |
| k33 | `k_swin_var<256,false>` | variable-window Swin transform (window 256) | `B` = 168 + H13; `group` = **19,200** (the highest in the swin_var series); `priv` = **24 (8/8 consistent)**; `codesz` = 28640 / 83736 / 83676×2 / 83736 / 22592×2 / 26976 | **needs external documentation** (T-01, T-03, T-17) | **yes** (scalar implementation) | **needs external documentation** (T-01, T-17) |

**Re-verification**: the `XMX direct support` column is 34/34 and the `recommended path` column is 34/34 marked as needing external documentation, **non-compliant rows 0**; the sampled k0 / k26 / k29 agree item by item.

### 3.3 "Which Go to XMX / Which Go to Generic SPIR-V" —— **this document does not give that partition**

**Reasons (three)**:

1. **there is no criterion for the direct support surface of XMX within this workspace**: all 34/34 rows of the `XMX direct support` column are marked as needing external documentation, on the basis that T-01 (XMX's primitive support and precision-mode coverage for matrix multiply / convolution) has **no criterion whatsoever** in this workspace;
2. **there is likewise no criterion within this workspace for the feasibility and boundary of the generic SPIR-V path** (T-15);
3. **the premise of that partition is the outcome of verifying T-01 / T-02 / T-03 / T-15**: if those four turn out to be "XMX does not directly support it", the roadmap must be rearranged along the generic SPIR-V path. **This document gives no conclusion on that branch.**

**⇒ The output form of this document at this point is a "partition method" rather than a "partition result"**:

| Step | Action | Input |
|---|---|---|
| 1 | look up T-01 (XMX primitives and precision coverage, including FP8 / FP16 / BF16 / INT8) | involves 25 kernels (names falling in the matrix-multiply / convolution / elementwise domain: k0–k19, k29–k33) |
| 2 | look up T-02 (whether split-K convolution and the floating-point accumulation order are constrained by a specification) | involves 4 (k4, k7, k10, k18) |
| 3 | look up T-03 (window / shift class primitives and the feasible interval of the window parameter) | involves 8 (k0, k1, k2, k29–k33) |
| 4 | look up T-15 (feasibility and performance boundary of the generic SPIR-V path) | all 34 |
| 5 | according to the results of 1–4, fill the 34 rows one by one into the two columns "XMX direct support" / "go generic SPIR-V" | this table |

### 3.4 Three Limitations on the "existing implementation on the XMX side" Column (**must be given together when citing that column**)

1. **the rows where that column = "yes" number 6** (k0, k29–k33), all coming from the self-developed project tree; **the other 28 rows are "no"** (those 28 kernel names get **0 hits** in that tree);
2. **that column does not mean "that implementation runs on XMX hardware"**: the two implementation bodies in the tree are **scalar loops** (`for d… for kk…`); that tree's only `joint_matrix` GEMM (`XmxGemm`) **is not called by any kernel** (that template gets only 1 hit in the whole tree = the definition line; `parallel_for` gets **0 hits** across all `.sycl` files). ⇒ **"whether it really goes through XMX" remains T-01, needing external documentation**;
3. **the 6 implementations are "rewritten versions"**, and **no judgement criterion was obtained for their shared-memory usage and register pressure**: the full text of `SwinKernelsXmx.sycl` **contains no shared-memory declaration whatsoever**; `SwinAttentionXmx.sycl` carries Q/K/V with **per-thread private arrays** `float q[MAX_CHANNELS]` / `k` / `v` (`MAX_CHANNELS` = 192) —— that formulation **produces no LDS request** and is **not the same implementation strategy** as the 62,592 B LDS requirement of k0 on the DLL side. ⇒ **"an implementation already exists" does not constitute substitute evidence for the class A criterion.**

### 3.5 Operator Rows Related to LDS / SLM —— Citation Discipline for Byte-Level Basis

Wherever "some kernel involves LDS / SLM" is written, **the following must be given simultaneously**:

1. the `group_segment_fixed_size` value (+ the target number);
2. the `.kd` coordinates (bundle number / offset within `.rodata`);
3. the source marker of the basis.

**Reproducible coordinates (three)**:

| No. | Basis | Byte-level coordinates | Conclusion it can support |
|---|---|---|---|
| 1 | the `swin_layer` symbol name itself | the `.strtab` of the `#2` bundle; symbol `st_value` = `0xBD00`, `st_size` = 135,092; an entry for the same symbol exists in `.dynsym` | "**a device function whose first formal parameter is the `SwinLDS` class exists inside this device ELF**" |
| 2 | the `group_segment_fixed_size` field of the `.kd` descriptor (`@+0x00`, u32) | the `.rodata` of the `#1` bundle @ `0xA180` + `64 × slot`; e.g. k1's `.kd` is in `#1` @ `0xA1C0`, and that field reads **64,640** | "the static LDS requirement of this kernel is 64,640 B" —— **272/272 collision-consistent** with the msgpack side |
| 3 | the `private_segment_fixed_size` field of `.kd` (`@+0x04`, u32) | the same `.kd` start + 4; e.g. k7 in `#8` reads **404** | "the private-segment requirement of this kernel" —— **272/272 collision-consistent** |

**Three citation disciplines**:

1. **do not write only "involves shared memory" without coordinates**;
2. **the `swin_layer` symbol can support only the layer "LDS is used as a formal parameter type"**; it **cannot** support "that function's LDS usage", "the call relationship between that function and the 34 kernels", or "how that function should be rewritten on the Xe side" —— the latter three are **all marked as needing external documentation** (T-21 / T-24);
3. **the self-developed project tree provides no LDS / SLM basis** (that tree gets **0 hits each** for `LDS` / `SLM` / `local_accessor` / `group_barrier`).

**The decidable part**: among the 34 kernels, **15** have `group_segment_fixed_size ≠ 0`; among them the **7** with `≥ 16,384` are k0, k1, k2, k5, k8, k12, k16. **The LDS basis for those 7 rows is row 2 of the table above. The limit determination belongs to T-06, needing external documentation.**

### 3.6 Three Structural Facts That Must Be Listed Separately

#### (a) Only 3 of the 34 kernels lack the "`B` + H13" parameter form

| kernel | parameter form | Criterion |
|---|---|---|
| `k_flag_wait` | `global_buffer`(8) + `by_value`(4) + `by_value`(4), `kernarg` = 16 | `04-Kernel-Parameter-Spec.md` §1.3 |
| `k_align_probe` | only `global_buffer`(8), **no `by_value`**, `kernarg` = 8 | as above |
| `k_flag_set` | `global_buffer`(8) + `by_value`(4), `kernarg` = 12 | as above |

- the whole library has **24** `global_buffer` parameters in total = 3 kernels × 8 targets; and **these 24 are the only** parameters in the whole library carrying `.address_space` (measured value the string `"global"`, raw bytes `A6 67 6C 6F 62 61 6C`);
- these 3 kernels' `max_flat_workgroup_size` is **1024 in all cases**; their `group_segment_fixed_size` is **0 in all cases**.

#### (b) The 8 kernels with `max_flat_workgroup_size` = 1024 form one semantic cluster

k20 (repack) / k22 (mean) / k23 (import) / k24 (export) / k25 (reproject) / k26 (flag_wait) / k27 (align_probe) / k28 (flag_set) —— 8 kernels × 8 targets = 64 entries; the other 26 kernels are 256. By name, the members of this cluster all belong to the "**data movement / view / reduction / synchronization**" class, and **not one belongs to the Swin / convolution / attention class**.

#### (c) `swin_layer(SwinLDS&, …)` is the 35th `.text` function, and exists only in 4 targets

| Item | Value |
|---|---|
| symbol name | `_Z10swin_layerR7SwinLDSPKhRK10BlobLayouti` (**non-template**; `7` is the name length prefix) |
| occurrence range | **`#2` gfx11-generic / `#3` gfx1100 / `#4` gfx1101 / `#5` gfx1102**; `#1` / `#6` / `#7` / `#8` get **0** hits |
| size | `st_size` = 135,092 (`#2`, `#5`) / 135,096 (`#3`, `#4`); VA is `0xBD00` for all |
| is it among the 34 kernel names | **no** |
| `.symtab` entry count | `#2`–`#5` = 348; `#1` / `#6` / `#7` / `#8` = 347; **the symbol-set difference between `#1` and `#2` is exactly this one symbol**; **the union of symbols across the 8 bundles = 348, the intersection = 347** |
| `.strtab` hits | **4 occurrences** in the whole DLL (file `0x21D89F` / `0x33A867` / `0x457867` / `0x57689F`), **all falling inside the `.strtab` of their respective bundles**; `.rodata` / `.note` / payload get **0 hits** |

- `SwinLDS` / `BlobLayout` get **0 hits** across that project tree's whole tree ⇒ **no source to refer to**;
- **its semantics and the cause of its occurrence range are undetermined** ⇒ marked as needing external documentation (T-21 / T-24).

#### (d) The `g_e4m3_lut` symbol (FP8 related, **all zero**)

| Item | Value |
|---|---|
| location and size | each of the 8 device ELFs has a **512 B** `g_e4m3_lut` object inside `.rodata` |
| bytes | **all 8 targets have 512/512 bytes equal to `0x00`** |
| `.kd` references | **no field among the 272 descriptors equals that symbol's VA** |
| reference sites across the whole DLL | **2 8-byte encodings per bundle** (1 inside `.rodata` + 1 inside `.text`) |
| meaning of the name | contains `e4m3` (a form of FP8) and `lut` (look-up table) |
| **undetermined item** | whether the table is an **all-zero placeholder** or **filled at runtime** has **no criterion within this environment** (write-site determination requires instruction-level disassembly = E-2 unavailable; runtime memory-image comparison requires AMD hardware = E-1 unavailable) ⇒ marked as needing external documentation (T-22) |

### 3.7 Chapter Summary

| # | Conclusion |
|---|---|
| 4-1 | the 34-row mapping table is complete; **`XMX direct support` 34/34 and `recommended path` 34/34 are all marked as needing external documentation** |
| 4-2 | within this environment the operator types **can only reach "name-based inference"** (source ruled out + comparison module does not hold + no hardware + 0 hits for operator names inside the DLL) |
| 4-3 | the partition of "which go to XMX / which go to generic SPIR-V" **depends on the verification of T-01 / T-02 / T-03 / T-15**, and **this document gives no partition result** |
| 4-4 | "existing implementation on the XMX side" = 6/34, and it **does not mean it runs on XMX hardware** and **does not constitute substitute evidence for the class A criterion** |
| 4-5 | LDS-related rows must give the triple coordinates of "`group` value + `.kd` coordinates + source marker" |
| 4-6 | `swin_layer` (the 35th `.text` function, only `#2`–`#5`) and `g_e4m3_lut` (512 B all zero) **both have undetermined semantics** |

---

## 4. host-Side Replacement

### 4.1 Import Surface Classified by DLL (194 entries / 10 DLLs)

**Measurement method**: custom PE parsing (`DataDirectory[1]` = IMPORT, RVA `0x6B3F4` / Size `0xDC`), resolving the ILT / IAT descriptor by descriptor and reading the names.

| # | DLL | Entry count | ILT | IAT range | Nature |
|---|---|---|---|---|---|
| 1 | `d3d12.dll` | 1 | `0x18006B4D0` | `0x18006BB30` | graphics side (D3D12 root signature serialization) |
| 2 | `dxgi.dll` | 1 | `0x18006B4E0` | `0x18006BB40` | graphics side (DXGI factory) |
| 3 | `D3DCOMPILER_47.dll` | 1 | `0x18006B4F0` | `0x18006BB50` | graphics side (runtime HLSL compilation) |
| 4 | `USER32.dll` | 15 | `0x18006B500` | `0x18006BB60–0x18006BBD0` | system side (window / input / text drawing) |
| 5 | `GDI32.dll` | 10 | `0x18006B580` | `0x18006BBE0–0x18006BC28` | system side (bitmap / DC / font) |
| 6 | `COMDLG32.dll` | 1 | `0x18006B5D8` | `0x18006BC38` | system side (open file dialog) |
| 7 | `VERSION.dll` | 3 | `0x18006B5E8` | `0x18006BC48–0x18006BC58` | system side (file version information) |
| 8 | **`amdhip64_7.dll`** | **29** | `0x18006B608` | `0x18006BC68–0x18006BD48` | **AMD HIP runtime (the main body requiring replacement)** |
| 9 | `bcrypt.dll` | 6 | `0x18006B6F8` | `0x18006BD58–0x18006BD80` | system side (CNG hashing) |
| 10 | `KERNEL32.dll` | 127 | `0x18006B730` | `0x18006BD90–0x18006C180` | system side (Win32 basics) |
| — | **total** | **194** | — | — | 10 DLLs |

**Re-verification**: 10/10 DLLs' entry counts / ILT / IAT ranges are **identical character by character, TOTAL = 194**, **ordinal = 0**; `[Hh][Ii][Pp]` gets **29** hits and they are **all in `amdhip64_7`** ⇒ **29 / 194 = 14.9%**.

### 4.2 Import-Surface Replacement Summary Table

| DLL | Entry count | Entries needing replacement | Replacement target | Items to look up |
|---|---|---|---|---|
| `KERNEL32.dll` | 127 | **0** | keep (Win32 basics) | none (at the import-surface level) |
| **`amdhip64_7.dll`** | **29** | **29** | **SYCL / oneAPI Level Zero runtime** (item by item in §4.3) | §4.5 items 1–9 |
| `USER32.dll` | 15 | **0** | keep (window / input / text) | none |
| `GDI32.dll` | 10 | **0** | keep (bitmap / DC / font) | none |
| `bcrypt.dll` | 6 | **0** | keep (CNG hashing) | the specific algorithm is determined by the call-site arguments (not resolved in this round) |
| `VERSION.dll` | 3 | **0** | keep (file version information) | none |
| `d3d12.dll` | 1 | **0** | keep (D3D12 root signature serialization) | §4.5 item 10 (artifact compatibility verification) |
| `dxgi.dll` | 1 | **0** | keep (DXGI factory) | §4.5 item 10 |
| `D3DCOMPILER_47.dll` | 1 | **0** | keep (HLSL compilation) | §4.5 item 10 |
| `COMDLG32.dll` | 1 | **0** | keep (file selection dialog) | none |
| **total** | **194** | **29** | — | — |

- **replacement ratio**: **29 / 194 = 14.9%** (computed 29 ÷ 194 = 0.14948…); **the other 165 entries (85.1%) need no replacement at the import-surface level**.
- **scope limitation of the "entries needing replacement" column**: this column **counts only import-surface entries** and **does not cover**: ① **call-site-level** argument changes for those 29 (e.g. `hipGetLastError` / `hipGetDevicePropertiesR0600`); ② the runtime filling mechanism of the 17 **exports**; ③ compatibility verification of shader / root signature artifacts.

#### (a) Graphics side (4 entries)

| Import | Name | IAT slot | thunk VA | `E8` call sites | Plan |
|---|---|---|---|---|---|
| `d3d12.dll` | `D3D12SerializeRootSignature` | `0x18006BB30` | `0x1800558D0` | **3** | **keep** (D3D12 is an API layer, exposed through the drivers of both vendors) |
| `dxgi.dll` | `CreateDXGIFactory1` | `0x18006BB40` | `0x1800558E0` | **1** | **keep** |
| `D3DCOMPILER_47.dll` | `D3DCompile` | `0x18006BB50` | `0x1800558F0` | **4** | **keep** (HLSL compilation is independent of the GPU vendor) |
| `COMDLG32.dll` | `GetOpenFileNameW` | `0x18006BC38` | — (no thunk in the ladder) | **0** | **keep** (platform-independent UI behavior) |

- **graphics-side conclusion**: **all 4 are kept**. Basis: these 4 APIs belong to the **D3D12 / DXGI / HLSL compilation / Win32 common dialog** layer, and are **not vendor-proprietary runtimes**;
- **but "keeping the import" ≠ "zero changes on the graphics side"**: this DLL participates in shader / root signature construction through `D3D12SerializeRootSignature` / `D3DCompile` (3 + 4 = **7 call sites**), and **whether the artifacts of these call sites are compatible with the D3D12 driver on Xe** must be verified during the actual port ⇒ marked as needing external documentation (§4.5 item 10).

#### (b) System side (161 entries)

| DLL | Count | Plan | Note |
|---|---|---|---|
| `KERNEL32.dll` | **127** | **keep (127/127)** | all are Win32 basic APIs (file / thread / heap / synchronization / code page / environment / virtual memory / console). **14 of them have thunk ladder slots** (the 55 ladder entries attributed by index = `d3d12` 1 + `dxgi` 1 + `D3DCOMPILER_47` 1 + `VERSION` 3 + `amdhip64_7` 29 + `bcrypt` 6 + **`KERNEL32` 14** = 55); the rest are called via direct IAT references (e.g. `GetProcAddress` **25** sites, `CloseHandle` **25** sites) |
| `USER32.dll` | **15** | **keep (15/15)** | window class registration / message handling / input / text drawing / cursor. Among them `GetAsyncKeyState` has **7** direct IAT references |
| `GDI32.dll` | **10** | **keep (10/10)** | DC / DIB bitmap / font / text color. Unrelated to GPU compute |
| `bcrypt.dll` | **6** | **keep (6/6)** | CNG hashing: `BCryptOpenAlgorithmProvider` / `BCryptCreateHash` / `BCryptHashData` / `BCryptFinishHash` / `BCryptDestroyHash` / `BCryptCloseAlgorithmProvider`. **All 6 have thunk slots** (ladder indices 35–40, 1 `E8` call site each) |
| `VERSION.dll` | **3** | **keep (3/3)** | `GetFileVersionInfoA` / `GetFileVersionInfoSizeA` / `VerQueryValueA`, 1 `E8` call site each (ladder indices 3–5) |

- **system-side conclusion**: **all 161 are kept, replacement count = 0**. Basis: these 5 DLLs are Windows system DLLs and are **not on the "AMD → Intel" replacement axis**;
- **scope limitation of "platform-independent"**: this determination **covers only the import surface itself** (the existence of the DLLs and functions, the calling ABI). It **does not cover** the functionality implemented by the call sites of these APIs (e.g. the runtime resolution in which `GetProcAddress` participates —— see §4.4 item 3).

### 4.3 The Per-Item Replacement Targets for the 29 Entries of `amdhip64_7`

> **Limitation on the meaning of the replacement target column (must be given with the table)**: that column gives the **correspondence by API category** + required checks. Wherever there is no confidence about "the specific semantics of an Intel runtime API", the item is marked as needing external documentation with the direction to look into, and **no conclusion is given**. This table **does not assert** that any Intel-side API is equivalent to a HIP API in parameters / semantics.

| # | API name | IAT slot | Purpose (read directly from the name) | `E8` call sites | direct IAT references | Replacement target (category) | Items to look up |
|---|---|---|---|---|---|---|---|
| 1 | `__hipPopCallConfiguration` | `0x18006BC68` | pop the kernel launch configuration (grid / block / shared / stream) | **68** | 0 | SYCL `handler` / Level Zero `zeCommandListAppendLaunchKernel` argument group | §4.5-1 |
| 2 | `__hipPushCallConfiguration` | `0x18006BC70` | push the kernel launch configuration | **34** | 0 | as above (used in pairs) | §4.5-1 |
| 3 | `__hipRegisterFatBinary` | `0x18006BC78` | register the fat binary (device code container) | **1** | 0 | SYCL `program` / kernel bundle, Level Zero `zeModuleCreate` | §4.5-2 |
| 4 | `__hipRegisterFunction` | `0x18006BC80` | register a kernel function (name + slot) | **34** | 0 | SYCL kernel name registration, Level Zero `zeKernelCreate` | §4.5-3 |
| 5 | `__hipRegisterVar` | `0x18006BC88` | register a device global variable | **1** | 0 | Level Zero `zeModuleGetGlobalPointer`, SYCL `device_global` | §4.5-4 |
| 6 | `__hipUnregisterFatBinary` | `0x18006BC90` | unregister the fat binary | **1** | 0 | `zeModuleDestroy` / SYCL program destruction | §4.5-2 |
| 7 | `hipDestroyExternalMemory` | `0x18006BC98` | destroy an external memory object | **14** | 0 | Level Zero `zeMemFree` / external memory extensions | §4.5-5 |
| 8 | `hipDeviceSynchronize` | `0x18006BCA0` | device synchronization | **5** | 0 | `zeCommandQueueSynchronize`, SYCL `queue::wait()` | §4.5-6 |
| 9 | `hipDriverGetVersion` | `0x18006BCA8` | get the driver version | **1** | 0 | `zeDriverGetProperties` / `zeDriverGetExtensionProperties` | §4.5-6 |
| 10 | `hipEventCreate` | `0x18006BCB0` | create an event | **4** | 0 | `zeEventCreate` / SYCL `sycl::event` | §4.5-6 |
| 11 | `hipEventElapsedTime` | `0x18006BCB8` | time between events | **2** | 0 | `zeEventQueryTimestamps` (if available) / host-side timing | §4.5-6 |
| 12 | `hipEventRecord` | `0x18006BCC0` | record an event | **4** | 0 | `zeCommandListAppendSignalEvent` / SYCL event recording | §4.5-6 |
| 13 | `hipEventSynchronize` | `0x18006BCC8` | wait for an event | **1** | 0 | `zeEventHostSynchronize` / SYCL `event::wait()` | §4.5-6 |
| 14 | `hipExternalMemoryGetMappedBuffer` | `0x18006BCD0` | get the mapped buffer of an external memory | **1** | 0 | Level Zero external memory extensions / `zeMemAllocDevice` + mapping | §4.5-5 |
| 15 | `hipFree` | `0x18006BCD8` | free device memory | **20** | 0 | `zeMemFree` / SYCL USM `free` | §4.5-7 |
| 16 | `hipGetDeviceCount` | `0x18006BCE0` | get the device count | **1** | 0 | `zeDeviceGet` count / SYCL `platform::get_devices()` | §4.5-6 |
| 17 | `hipGetDevicePropertiesR0600` | `0x18006BCE8` | get device properties (ROCm 6.0 struct version) | **3** | 0 | `zeDeviceGetProperties` / SYCL `device::get_info()` | §4.5-8 |
| 18 | `hipGetErrorString` | `0x18006BCF0` | convert an error code to a string | **6** | 0 | `zeResultToString` (if present) / a self-built error code table | §4.5-9 |
| 19 | `hipGetLastError` | `0x18006BCF8` | get the last error | **3** | 0 | Level Zero returns `ze_result_t` per call (**there is no "last error" global state**) ⇒ the call-site structure must change | §4.5-9 |
| 20 | `hipImportExternalMemory` | `0x18006BD00` | import external memory | **1** | 0 | Level Zero external memory import extensions | §4.5-5 |
| 21 | `hipLaunchKernel` | `0x18006BD08` | launch a kernel | **60** | 0 | `zeCommandListAppendLaunchKernel` / SYCL `parallel_for` | §4.5-3 |
| 22 | `hipMalloc` | `0x18006BD10` | allocate device memory | **35** | 0 | `zeMemAllocDevice` / SYCL USM `malloc_device` | §4.5-7 |
| 23 | `hipMemcpy` | `0x18006BD18` | synchronous copy | **13** | 0 | `zeCommandListAppendMemoryCopy` + synchronization / SYCL `queue::memcpy` | §4.5-7 |
| 24 | `hipMemcpyAsync` | `0x18006BD20` | asynchronous copy | **2** | 0 | `zeCommandListAppendMemoryCopy` (asynchronous) | §4.5-7 |
| 25 | `hipMemcpyToSymbol` | `0x18006BD28` | copy to a device symbol | **1** | 0 | Level Zero global pointer write (`zeModuleGetGlobalPointer` + host-side write) | §4.5-4 |
| 26 | `hipMemset` | `0x18006BD30` | synchronous fill | **29** | 0 | `zeCommandListAppendMemoryFill` + synchronization | §4.5-7 |
| 27 | `hipMemsetAsync` | `0x18006BD38` | asynchronous fill | **1** | 0 | `zeCommandListAppendMemoryFill` (asynchronous) | §4.5-7 |
| 28 | `hipRuntimeGetVersion` | `0x18006BD40` | get the runtime version | **1** | 0 | runtime version query (no direct counterpart; must be self-built) | §4.5-6 |
| 29 | `hipSetDevice` | `0x18006BD48` | set the current device | **2** | 0 | SYCL `device_selector` / `zeContext` binding | §4.5-6 |

**Summary of the 29 entries**:

| Item | Value |
|---|---|
| entry count | **29** |
| **total `E8` call sites** | **349** (**29/29 equal** per API) |
| **number of entries referencing the IAT slot directly** | **0** (all 29/29 are invoked indirectly through `FF 25` thunks; under strict MODRM determination, **RIP-relative references that are not thunks = 0**) |
| thunk addresses | `0x180055930` … `0x180055AF0`, stride `0x10`, a contiguous run of **29**, **no gaps** |
| ordinal imports | **0** (all imported by name) |
| dead imports | **none** (all 29/29 thunks have ≥1 `E8` call site within `.text`, the minimum being 1) |

**Three structural conclusions about the HIP → port**:

1. **the call surface is entirely concentrated in the thunk ladder**: the **direct IAT references = 0** of the 29 HIP APIs within `.text` (29/29); all calls go through `FF 25 disp32` thunks ⇒ **the replacement surface is the layer "the implementation of the 29 thunks"**, not call sites scattered everywhere;
2. **but replacing the thunk layer drags the call sites along**: the **parameter / return semantics** of `hipGetLastError` (**3 sites**) and `hipGetDevicePropertiesR0600` (**3 sites**) have no same-named counterpart on the Level Zero side (the former is a "last error" global state, the latter an ABI name carrying a struct-version suffix) ⇒ these two **cannot be handled by simply swapping the implementation** and **require per-call-site argument changes**;
3. **the 60 call sites of `hipLaunchKernel` have been fully enumerated** (31 same-template instances + 29 others / 9 functions) ⇒ the launch-surface replacement effort can be estimated at two levels: "**60 call sites + 29 thunks**".

### 4.4 Boundaries and Unclosed Items of the host-Side Replacement

| # | Item | Status |
|---|---|---|
| 1 | the full composition of the thunk ladder | **55 entries** (`0x1800558D0`–`0x180055C30`, stride `0x10`); the raw `FF 25` count across all `.text` is 101 = 17 export stubs + 55 ladder + 29 other scattered. Those 55 were resolved one by one to their targets and mapped to import names, agreeing item by item with the ladder table |
| 2 | per-entry attribution of the ladder indices | **closed**: indices 41–54, 14 entries in total = `FlushInstructionCache` / `GetCurrentProcess` / `GetCurrentThread` / `GetCurrentThreadId` / `GetLastError` / `GetThreadContext` / `ResumeThread` / `SetLastError` / `SetThreadContext` / `SuspendThread` / `VirtualAlloc` / `VirtualFree` / `VirtualProtect` / `VirtualQuery` (all KERNEL32) |
| 3 | the **purpose** of `GetProcAddress` / `LoadLibraryA` / `LoadLibraryExW` / `FreeLibrary` / `GetModuleHandleA/W` | **proven**: the runtime resolution capability exists (direct IAT references: `GetProcAddress` **25** sites, `FreeLibrary` **7** sites, `GetModuleHandleA` **9** sites). **Unproven**: whether they participate in filling the 17 export slots |
| 4 | the replacement surface of the 17 **exports** | all exports are pure `FF 25` forwarders (17 items, `0x1800019D0`–`0x180001AD0`), with targets = the 17 slots at `.data` tail `0x180076440..0x1800764C0` (**no file bytes, no `.reloc` coverage**, filling path unproven); all export names are VERSION.dll API names; the module name = `version.dll` |
| 5 | whether any of the 29 are "never called" dead imports | **no dead imports**: all 29/29 thunks have ≥1 `E8` call site within `.text` |
| 6 | constraints of a cross-platform runtime environment | no AMD hardware ⇒ this DLL **cannot run** within this environment; "verification of the runnability after replacement" **cannot be done** within this environment |
| 7 | **samples of similar implementations** provided by the self-developed project tree | the runtime files on the HIP side and the SYCL side correspond **function by function under the same names**: `initDevice` / `loadWeights` / `buildNetworkConfig` / `allocateBuffers` / `Evaluate` / `encodeInput` / `runBlock` / `decodeOutput` / `ResetHistory`. **A sample ≠ a conclusion**: that sample's own compilation artifacts cover only 6/34 kernels |

### 4.5 List of Items Needing External Documentation (question four, **no conclusion given**)

| # | Item to look up | Proposition it blocks | Direction to look into |
|---|---|---|---|
| 1 | the expression and lifetime of "kernel launch configuration" in SYCL / Level Zero | `__hipPopCallConfiguration` (68 sites) + `__hipPushCallConfiguration` (34 sites) = **102 call sites**, the most numerous pair in the whole library | SYCL 2020 (`sycl::handler`, `nd_range`, `local_accessor`), the oneAPI Level Zero specification (`zeCommandListAppendLaunchKernel` argument group) |
| 2 | the Level Zero module format and the SPIR-V module creation flow | `__hipRegisterFatBinary` / `__hipUnregisterFatBinary` (1 site each); the existing container = `__CLANG_OFFLOAD_BUNDLE__`, with all 8 device triples being `amdgcn-amd-amdhsa` | the oneAPI Level Zero specification (`zeModuleCreate`, `zeModuleDynamicLink`, module formats); the SPIR-V specification (module structure) |
| 3 | the Level Zero kernel handle acquisition and launch flow | `hipLaunchKernel` (60 sites) + `__hipRegisterFunction` (34 sites) = **94 call sites** | the Level Zero specification (`zeKernelCreate` / `zeKernelSetArgumentValue` / `zeKernelSetGroupSize` / `zeCommandListAppendLaunchKernel`); SYCL 2020 (kernel naming and `parallel_for`) |
| 4 | Level Zero access to device globals (symbols) | the replacement targets of `__hipRegisterVar` / `hipMemcpyToSymbol` | the Level Zero specification (`zeModuleGetGlobalPointer`) |
| 5 | Level Zero's **external memory / D3D12 interoperability** extensions | `hipDestroyExternalMemory` (14) / `hipExternalMemoryGetMappedBuffer` (1) / `hipImportExternalMemory` (1), **3 entries** in total | Level Zero external memory extensions; D3D12 ↔ Level Zero interoperability (shared resources / shared fences) |
| 6 | the counterparts of the device / driver / event / version query APIs | 9 entries (items 8 / 9 / 10 / 11 / 12 / 13 / 16 / 28 / 29) | the Level Zero specification (`zeDeviceGet`, `zeDeviceGetProperties`, `zeDriverGetProperties`, the `zeEventCreate` family, `zeEventQueryTimestamps`); SYCL 2020 (`device`, `event`, `queue::wait`) |
| 7 | the counterparts of USM / memory allocation and copy | 6 entries (items 15 / 22 / 23 / 24 / 26 / 27); `hipMalloc` 35 + `hipFree` 20 + `hipMemset` 29 = **84 call sites** | the Level Zero specification (`zeMemAllocDevice` / `zeMemAllocShared` / `zeMemAllocHost`, `zeCommandListAppendMemoryCopy`, `zeCommandListAppendMemoryFill`); SYCL 2020 (the three USM allocation types) |
| 8 | the parameter struct layout of `hipGetDevicePropertiesR0600` | item 17: the name carries an ABI version suffix (`R0600`) and the parameter struct is AMD-proprietary ⇒ **per-call-site argument changes are required (3 sites)** | AMD ROCm headers (that struct definition); oneAPI Level Zero `ze_device_properties_t` |
| 9 | the difference in error-code models | items 18 / 19: HIP has `hipGetLastError` (a "last error" global state, 3 sites) and `hipGetErrorString` (6 sites); Level Zero returns `ze_result_t` per call | the Level Zero specification (`ze_result_t` and `zeResultToString`, if present); SYCL 2020 (exceptions and `errc`) |
| 10 | the **compatibility of `D3DCompile` / `D3D12SerializeRootSignature` artifacts on Xe** | §4.2(a)'s "keeping the import ≠ zero changes" | the D3D12 driver documentation for Intel Arc B580; the correspondence between D3DCompile target profiles and the Intel driver |
| 11 | whether the HIP → SPIR-V porting toolchain has a **reusable path** | the **implementation method** of all 29 entries of §4.3 (hand-written one by one vs toolchain conversion). **This table presupposes no conclusion** | the AMD HIP SDK documentation; Intel oneAPI's HIP compatibility layer (if any); the SYCL HIP interoperability documentation. **Reference object**: the self-developed project tree already contains a sample implementation with "HIP side ↔ SYCL side correspondence function by function" |

### 4.6 Chapter Summary

| # | Conclusion |
|---|---|
| 5-1 | import surface **194 entries / 10 DLLs**; the per-DLL counts agree across 10/10 independent re-verifications |
| 5-2 | **29/194 = 14.9% need replacement**, all in `amdhip64_7`; the other 165 **need no replacement at the import-surface level** |
| 5-3 | all 4 graphics-side entries are kept; all 161 system-side entries are kept |
| 5-4 | the **direct IAT references = 0** of the 29 HIP APIs; **total `E8` call sites 349**; the thunk ladder's 29 entries are contiguous with no gaps |
| 5-5 | **2 entries require per-call-site argument changes** (`hipGetLastError` 3 sites, `hipGetDevicePropertiesR0600` 3 sites) |
| 5-6 | the **60 call sites** of `hipLaunchKernel` have been fully enumerated ⇒ the effort can be estimated at two levels: "60 call sites + 29 thunks" |
| 5-7 | 11 items to look up (including D3D12 interoperability, the error-code model, and a HIP → SPIR-V toolchain) **all give no conclusion** |

---

## 5. Weight Format and Conversion

> **This chapter makes no selection** (it gives only candidate paths and criteria).

### 5.1 The Weight Entity and Container Definition (**fully resolved**)

| Item | Value |
|---|---|
| path | external weight file `dlssnr_on_amd_weights.bin` |
| size | **147,689,451 B** (`0x8CD8FEB`) |
| SHA256 | `6BF8DC931EF3CCFFE18C82DE26AB374156E7F19539FFCF8EABAA25DCA5CF15AB` |
| second copy | same size, same SHA256, **byte-identical** |

#### (a) Container structure (determined byte by byte)

```
offset 0x00   8 bytes   char[8]  magic = "DLSSNRW1"
offset 0x08   4 bytes   uint32   = 153        ← entry count
offset 0x0C   4 bytes   uint32   = 5,673      ← total index-region length (including the 16 B header)
offset 0x10   variable   entry × 153
offset 0x1629           payload-region start
```

**Entry structure (variable length, arranged in file order)**:

```
uint8    nameLen          ← entry name length (measured value domain {19, 20, 26})
char[]   name[nameLen]    ← ASCII entry name
uint64   offset           ← LE, byte offset relative to "payload-region start"
uint64   size             ← LE, payload byte count of that entry
```

#### (b) Three identities (**closing to 0**)

| # | Identity | Measured |
|---|---|---|
| ① | walking every entry to the end == `uint32@0x0C` | **5,673 == 5,673**, difference 0 |
| ② | `Σ size` == file size − payload start | **147,683,778 == 147,689,451 − 5,673**, difference 0 |
| ③ | `offset[0] == 0` and offset chain violations | **`offset[0] = 0`; 153/153 strictly increasing, `offset[i] == Σsize[0..i-1]`; chain violations 0/153** |

**Byte-by-byte accounting of the index region**: `0x00`–`0x08` magic 8 B; `0x08`–`0x0C` header field 1 (4 B); `0x0C`–`0x10` header field 2 (4 B); `0x10`–`0x1629` **entry region 5,657 B** (= 153 × nameLen field 153 + name strings 3,056 + offset fields 1,224 + size fields 1,224); `0x1629`–`0x8CD8FEB` **payload region 147,683,778 B**.

**Remaining unattributed bytes = 0** —— that is, **outside the 153 entries** there are **no** unexplained bytes, and hence within the index region there is **no** second table / additional field region / padding region.

**Unbounded-scan reductio (a direct product of the parsing discipline)**: if the header's `count = 153` is not used as the loop bound, an unbounded scan yields **301 entries**, with the **first loss-of-control point = file `0x5E15`, nameLen `0x00`** ⇒ corroborating the parsing discipline "**the header's `count` must be used as the loop bound**".

#### (c) Entry naming and payload

| Statistic | Measured |
|---|---|
| entry count | **153** |
| names arranged in **ASCII order** | **yes** (153/153, case-sensitive) |
| `block<N>` value domain | **0 … 70**, **71 distinct blocks**, **no missing numbers** |
| `<kind>` values | `layer` (152 entries) + `blend_scale` (**1 entry**) |
| the only entry containing `blend_scale` | **`block70.layer0.blend_scale`** (`offset = 147,394,848` / `size = 2`) |
| `layer` layer-number counts | `layer0` × 71, `layer1` × 24, `layer2` × 24, `layer3` × 24, `layer4` × 9 (**scope**: this row uses the "`layer` entries" scope, `layer0` = 71 `blockN.layer0.layer`; **if the single `block70.layer0.blend_scale` is included it is 72**) |
| **total entry count** per block | `1 entry × 46`, `2 entries × 1` (block70), `4 entries × 15`, `5 entries × 9` |
| **`layer` entry count** per block | **1 × 47 / 4 × 15 / 5 × 9** |
| payload region | **147,683,778 B, contiguous with no holes**; the index region occupies only **0.0038 %** of the whole file |

**Layer-count histogram (precise scope, must accompany any citation)**:

> **1 layer × 47 (block 0–22, 39, 48–70) / 4 layers × 15 (23–29, 40–47) / 5 layers × 9 (30–38)**

> **The two scopes are not interchangeable**: under the "total entry count" scope `block70` is "2 entries"; under the "`layer` entry count" scope it is "**1 layer**".

#### (d) Element width and numeric interpretation (**boundaries must be stated**)

| Detection item | Measured | Determination |
|---|---|---|
| whether all 153 sizes are even | **yes** (153/153) | consistent with a 2-byte element width |
| entries whose size is divisible by 8 | **144 / 153** | the 9 exceptions **are all size = 2** |
| minimum / maximum size in the whole library | **2 B** / **4,196,352 B** | — |
| share of payload bytes equal to `0x00` | **2.4594 %** | not sparse |
| share of payload bytes equal to `0xFF` | **0.0056 %** | not saturated |
| payload Shannon entropy | **5.902444 bits/byte** (full marks 8) | **not random, not a high-entropy compressed stream** |
| ASCII strings inside the payload | `DLSSNRW1` **0**, `block` **0**, `layer` **0**, `ELF` **0**, `PTX` **0**, PNG magic **0** | the payload is purely numeric, with **no nested container** |
| longest contiguous `0x00` in the payload | **264 B** | local zero blocks exist (only 2 runs, both 264 B) |
| contiguous `0x00` at the end of the file | **16 B** | trailing alignment padding |
| 24 deduplicated size values | of which **12 are multi-entry size groups**; **the other 12 sizes each have exactly 1 entry** | the size pattern is highly regular |
| ASCII-printable share (payload region) | **1.0273 %** | consistent with the expected order of magnitude for "purely numeric bytes coincidentally falling in the printable range" |
| ASCII strings of length ≥16 (payload region) | only **6**; the longest is **21 bytes** | **not even one string reaching the length order of a complete name** |
| payload-region ASCII strings ∩ the 153 names | **∅** | — |
| fixed-stride autocorrelation (9 strides) | all 0.036–0.043, **no peak** | no periodic structure / repeated table / interleaved index |

- **the numeric interpretation tends toward FP16 (binary16, little-endian)**: the `blend_scale` bytes `eb 39` → **`+0.739746`**; the decoded magnitudes of three sample groups are reasonable; **decoding as bfloat16 gives non-physical magnitudes** (such as `5.9e-37`, `-6.4e+19`);
- **this task did not perform a full statistical test** ⇒ **"FP16" is recorded only as a tendency and is not upgraded to a proven conclusion**;
- **one unverified item**: "the content hashes of the 153 payloads are pairwise distinct" is **self-reported by a single source and has not yet been independently recomputed** ⇒ **it must not be treated as a confirmed conclusion**; a re-run is recommended (12 groups, 153 SHA256 computations, low cost).

#### (e) Summary of confirmed container-level items (**only proven items are listed**)

| # | Conclusion | Evidence level |
|---|---|---|
| W1 | the file is a **self-describing container** with the `DLSSNRW1` magic; header = 8 B magic + `uint32`(153) + `uint32`(5673) | **proven** |
| W2 | the index region = 153 variable-length entries, structure `(uint8 nameLen, char name[], uint64 offset, uint64 size)`; index region `[0x10, 0x1629)` | **proven** |
| W3 | offsets are **relative to the payload-region start** (`0x1629`); the three identities hold | **proven** |
| W4 | payload region 147,683,778 B, **contiguous with no holes** | **proven** |
| W5 | entry names `block<N>.layer<L>.layer` + 1 entry `block70.layer0.blend_scale`; `<N>` ∈ [0, 70] with no missing numbers | **proven** |
| W6 | element width = **2 bytes** | **proven** |
| W7 | the payload is uncompressed (entropy 5.90 b/B, no nested container, 0 hits for ASCII strings); local zero blocks and a 16 B zero tail padding exist | **proven** |
| W8 | the numeric interpretation **tends toward FP16**, **no full test performed** | **tendency + unproven** |
| W9 | the container **contains no shape / dtype field** ⇒ tensor shapes must be determined externally | **proven** |
| W10 | the two parsers in the self-developed project tree **agree** with the measurement; another `WeightBlobHeader` **does not agree** with the measurement | **proven** |

### 5.2 Ruling on the Weight Header Conflict

| Source | Location and original text | Constant | LE bytes / ASCII | Equal to the measurement |
|---|---|---|---|---|
| in-tree `Engine.cpp` | `uint32_t magic; // 'DLNR' = 0x524E4C44` + a same-named check | `0x524E4C44` | `44 4C 4E 52` / `DLNR` | **no** |
| in-tree `IntelEngine.cpp` | `uint32_t magic; // 'DLNR' = 0x524E4844` + a same-named check | `0x524E4844` | `44 48 4E 52` / **`DHNR`** | **no** |
| in-tree `weight_analyzer.cpp` | `char magic[8]; // "DLSSNRW1"` + a check | `"DLSSNRW1"` | `44 4C 53 53 4E 52 57 31` | **yes** |
| in-tree `InferenceEngine.cpp` | `strncmp(header_.magic, "DLSSNRW1", 8) != 0` | `"DLSSNRW1"` | as above | **yes** |

**Ruling**: **`DLSSNRW1` (8 B) prevails**; the 4-byte constants of `Engine.cpp` and `IntelEngine.cpp` **both fail to correspond to any field in the measured file**, **both are wrong in the same way**, and there is no room for "choosing one of the two".

**Five criteria**:

| # | Criterion |
|---|---|
| N-1 | **the conflict axes are misaligned**: the two 32-bit constants and the measurement are **simply not on the same comparison plane** —— the measured magic is **an 8-byte char array**; the two 32-bit constants are **a single `uint32_t` field**. Matching a 32-bit constant against an 8-byte magic has, **by construction, no case of equality** |
| N-2 | **two identities close to 0**: parsing with `char magic[8]` + `numTensors@8` + `numBlockLayers@12`, the name-table end == 5,673, the data region == Σsize, and the offset chain has 0 anomalies ⇒ **the 8-byte magic layout is verified by byte closure**; the 32-bit magic layout **cannot close** |
| N-3 | **`Engine.cpp` describes itself as a reconstruction guess**: the comment reads "Reconstructed from decompiled weight loading code" ⇒ it is an **unchecked speculative structure** |
| N-4 | **the constant in `IntelEngine.cpp` disagrees with its own comment**: the comment writes `'DLNR' = 0x524E4844`, but the LE ASCII of that constant is **`DHNR`** ⇒ the definition is internally self-refuting |
| N-5 | **the two constants are mutually exclusive and neither can close with the file**: they differ by `0x400`; and the measured `uint32@0 = 0x53534C44` equals **neither of them** |

**One wording correction**: `5,673` is the value of `uint32@0x0C` and is **not hard-coded in `weight_analyzer.cpp`** (the literal strings `5673` / `0x1629` get **0 hits**); it is obtained at runtime via `tellg()`.

### 5.3 In-Tree Cross-Corroboration (an independent second source)

| File | Content | Relation to the measurement |
|---|---|---|
| `weight_analyzer.cpp` | `#pragma pack(push,1) struct WeightHeader { char magic[8]; uint32_t numTensors; uint32_t numBlockLayers; }` | **byte-for-byte consistent with the container structure** (8 + 4 + 4) |
| as above | reads entry by entry `uint8 nameLen` → `name` → `uint64 offset` → `uint64 size` | **consistent with the entry structure** |
| as above | `uint64_t elems = t.size / 2; // FP16` | supports "2-byte element" (comment-level evidence) |
| as above | `for (uint32_t b = 0; b <= maxBlock && b <= 70; b++)` | **`<= 70` is consistent with the measured `block0..block70`** |
| as above | `uint32_t blockIdx = atoi(t.name.c_str() + 5);` | **reductio**: the source itself **must parse the name string** when it needs the block number ⇒ the container **indeed has no** independent block index field |
| `InferenceEngine.cpp` | magic check + per-entry reads | consistent |
| as above | the test name list contains `block0.layer0.layer` / `block23.layer0.layer` / `block23.layer2.layer` / `block47.layer3.layer` / `block70.layer0.blend_scale` | **all 5 names exist in the measured 153-entry list** |
| as above | per-block statistics use `atoi(t.name.c_str() + 5)` to parse the block number from the name | **the same reductio as above** |
| `DlssNrEngine.h` | `NUM_BLOCKS = 71` / `MAX_LAYERS_PER_BLOCK = 4` / `MAX_WINDOW_SIZE = 256` | **71 is consistent with the measured 71 blocks**; **`MAX_LAYERS_PER_BLOCK = 4` is overturned by the measurement** (see §5.6) |
| `IntelEngine.cpp` | `struct WeightBlobHeader { uint32_t magic; … }` | **conflicts with the measured format** (see §5.2) |
| `FINAL_STATUS.md` | "weight format: DLSSNRW1, FP16, 153 tensors" | **153 is consistent with the measurement**; "FP16" is a **documentation-level declaration** |

**Consistency ruling**: the two parsers **are consistent with the measured format** (matching field by field); the `WeightBlobHeader` / `TensorDesc` of `IntelEngine.cpp` **are inconsistent with the measured format** ⇒ that file's magic check **returns false on the measured file**, and `loadWeights()` takes the `return false` branch. **This document makes no causal judgement**, only registering this **reproducible consistency difference**.

> **Note**: the self-developed project tree and the DLL are **non-isomorphic**, so the table above serves **only as a cross-check of the "container format declaration"** and **must not** be used as a source-code comparison for the 34 kernels.

### 5.4 kernarg Alignment Specification

#### (a) Facts

| Item | Fact |
|---|---|
| `.kernarg_segment_align` | **8** (`8 × 272`, 8 targets consistent) —— one of the "8 consistent fields" |
| `.kernarg_segment_size` | **12 deduplicated values**: `296×72`, `424×40`, `288×32`, `304×32`, `280×24`, `320×16`, `336×16`, `328×8`, `384×8`, `16×8`, `8×8`, `12×8`; 8 targets consistent |
| the values of the 31 kernels mod 8 | **all 0** (280 / 288 / 296 / 304 / 320 / 328 / 336 / 384 / 424) |
| the 3 exception kernels | `k_flag_wait` = **16** (mod 8 = 0), `k_align_probe` = **8** (mod 8 = 0), `k_flag_set` = **12** (**mod 8 = 4**) |
| **the only kernel not satisfying 8-byte alignment** | **`k_flag_set` (12 B)** |
| user parameter region start | `offset = 0`, length = the table's `size/by_value` |
| **implicit parameter span** | **66 B** = 13 hidden parameters 50 B + **16 B hole** |
| 8-byte field alignment in the implicit region | the absolute offsets of `hidden_global_offset_x/y/z` = `B + 0x28 / +0x30 / +0x38`; **all 31 kernels are 8-aligned, 0 counterexamples** |
| **tail** | **190 B** (31 kernels × 8 targets = **248** records with difference +190); entries with difference `+0` = **24** (3 kernels × 8 targets) |
| concatenation identity (31 kernels) | `kernarg = by_value + 66 + 190` ⇔ `Σ(parameter size) + 206 = kernarg` (206 = 16 hole + 190 tail) |

#### (b) Alignment advice (**the fact column and the advice column are separated**)

| # | Advice | Basis |
|---|---|---|
| K1 | **the 8-byte alignment of the kernarg segment (`align = 8`) is consistent across all 8 targets and is one of the "few structural parameters reusable across targets"** ⇒ on the Xe side **`align = 8` should be carried over** as the starting alignment of the kernarg segment | §5.4(a) |
| K2 | **the `kernarg_segment_size` of all 31 kernels is a multiple of 8**, and the absolute offsets of the three 8-byte hidden fields are all 8-aligned ⇒ **the 31 kernels are self-consistent on the "8-byte alignment" dimension** (**0 counterexamples**) | §5.4(a) |
| K3 | **the `kernarg_segment_size = 12` of `k_flag_set` is not a multiple of 8** (mod 8 = 4) ⇒ it is the **only** kernel not self-consistent on 8-byte alignment. When handling this kernel on the Xe side its **segment length must be handled separately** (pad 4 B to 16, or relay it out according to Xe's actual alignment requirement) | §5.4(a) |
| K4 | **`align = 8` must not be taken directly as Xe's kernarg alignment requirement** —— 8 is the value in **AMD `amdhsa` metadata**; the alignment requirement on the Xe side must be verified separately | needs external documentation, direction in K5 |
| K5 | **needs external documentation**: ① the **alignment requirement of the kernel parameter (kernarg) segment on Xe** (whether a fixed alignment exists, and whether it is 8/16/32/64 bytes); ② the SYCL 2020 specification's rules on kernel parameter alignment; ③ the alignment clauses for kernel parameter layout in the Level Zero specification; ④ **whether the multiple 8-byte pointer parameters (`hidden_global_offset_x/y/z`) have additional address alignment requirements on Xe**; ⑤ whether the **packing rules for 2-byte parameters (`hidden_group_size_*`, etc.) on Xe** are the same as AMD's | direction in §8 G-40 |
| K6 | **the disposition of the 190 B tail and the 16 B hole on the Xe side requires first resolving their field attribution**, otherwise it cannot be judged whether they need Xe-side alignment —— this item **is unresolved within this workspace** | §8 U-5 |
| K7 | **the concatenation rule of the 3 exception kernels differs from the 31 kernels** (no hidden parameters, no tail); the Xe side must **implement them separately** and **must not** apply the `+206` formula | §5.4(a) |
| K8 | **`k_align_probe` has no `by_value` parameter** (its `Ph` parameter is a `global_buffer` pointer) —— when citing, the wording "**no `by_value` parameter**" must be used, and one **must not** write "its `by_value` size is 0" | §5.4(a) |
| K9 | **the Xe-side kernarg layout is best rebuilt "per kernel, per parameter"** (rather than carrying over the absolute offsets from the AMD metadata directly): the per-parameter `offset/size/value_kind` of the 34 kernels is **fully isomorphic** across the 8 targets (238/238 judgement cells consistent, `args` byte SHA256 identical 272/272), and can serve as the **authoritative input** for the Xe-side rebuild | `04-Kernel-Parameter-Spec.md` §1.2 |
| K10 | **current state of the self-developed project tree**: the existing SYCL kernels pass parameters with `struct` and **do not lay out kernarg manually by absolute offset** ⇒ that skeleton **does not solve** the kernarg alignment problem, and Xe-side alignment must be decided by the compiler | needs external documentation |

### 5.5 Candidate Weight Conversion Paths (**no selection**)

#### Common prerequisite P0 (required by all paths)

| Step | Action | Items to look up |
|---|---|---|
| **P0-a** | obtain the **shape** of each `layer` (the container **does not contain** a shape field) | **E3**: the upstream model definition file (`.onnx` / `.safetensors` / training·export scripts); or infer it from the `block<N>.layer<L>` naming regularity + the payload byte count (**the inference result must be marked as unproven**) |
| **P0-b** | settle the final ruling on the element type **FP16 vs BF16** | **E2**: a full-decode statistical test; or the upstream model definition; or comparison against the weights on the other side |
| **P0-c** | establish the mapping from `block<N>.layer<L>` → operator semantics (Swin's QKV / proj / MLP / pos_bias, etc.) | **E4**: the upstream network definition; or runtime observation |

#### Path A: keep the `DLSSNRW1` container → feed it directly to the Intel-side runtime (**smallest change**)

| Step | Action | Basis / items to look up |
|---|---|---|
| A-1 | **do not convert the container**; use the `DLSSNRW1` parser to read it into host memory | the container can be fully parsed by **pure host-side code** (no GPU needed); already implemented in the tree |
| A-2 | on the Xe side, treat each `layer` payload **as a tensor** according to its shape and upload it to USM / a `buffer` | needs external documentation (**A2-new**): the choice between `buffer` / USM in SYCL 2020 and the **alignment requirements** for 2-byte elements |
| A-3 | use `joint_matrix` for the QKV / proj / attention GEMMs | needs external documentation (**A3-new**): the **tile sizes and element type combinations** supported by `joint_matrix` |
| A-4 | fill in the unimplemented functions | the function bodies of each host-side stage in the tree **are all `return true;`** |
| **advantage** | zero conversion cost, no intermediate-format loss, isomorphic to the existing skeleton | — |
| **risk** | the `DLSSNRW1` reading logic must be **rebuilt** on the Intel side (an existing implementation is reusable, but one version in the tree disagrees with the measurement) | §5.3 |

#### Path B: `DLSSNRW1` → **OpenVINO IR** (`.xml` + `.bin`) → OpenVINO Runtime

| Step | Action | Items to look up |
|---|---|---|
| B-1 | parse the container and cut the 153 payloads into named tensors according to the P0-a shapes | same as P0-a |
| B-2 | bind the tensors into an operator graph using OpenVINO's model-building API (or by building the graph manually) | needs external documentation: whether OpenVINO provides a public API for building a model "from constant tensors + a manual graph" and its version requirements |
| B-3 | serialize to IR (`.xml` + `.bin`) | needs external documentation: IR version and element type (FP16) support |
| B-4 | load and infer on the Intel GPU with OpenVINO Runtime | needs external documentation: ① how the GPU plugin exploits **XMX** and the precision settings it requires; ② whether the FP16 constants in the IR remain FP16 on the GPU plugin (or are re-laid-out / converted); ③ whether dynamic shapes are supported (this network's H/W varies with resolution) |
| **risk** | ① **the shapes must be fully determined** (if P0-a is unclosed this path is blocked); ② whether the OpenVINO graph **does** re-lay-out operators, and whether after re-layout it **does** correspond bit for bit to the AMD original's numeric path, **has no criterion in this workspace** ⇒ needs external documentation (this network is super-resolution / denoising, and assessing the impact of numeric differences is a separate subject) | — |

#### Path C: `DLSSNRW1` → **ONNX** → OpenVINO / ONNX Runtime-DML / oneDNN graph

| Step | Action | Items to look up |
|---|---|---|
| C-1 | parse the container → named tensors (same as B-1) | same as P0-a |
| C-2 | build the graph with ONNX | needs external documentation: how ONNX expresses FP16 initializers |
| C-3 | choose the execution backend: (a) OpenVINO reads ONNX; (b) ONNX Runtime + DirectML EP; (c) hand-written oneDNN operators | needs external documentation: ① the operator set OpenVINO supports when reading ONNX; ② **whether ONNX Runtime-DML enables XMX on Intel Arc**; ③ oneDNN's **XMX backend** support and operator coverage |
| **risk** | ① one extra conversion layer ⇒ one extra layer of numeric / shape fidelity risk; ② the degree to which the backend exploits XMX depends on the EP, **and there is no criterion in this workspace** | — |

#### Path D: keep the HIP sources → go through a SYCL / HIP compatibility layer (**there are already signs of this in the workspace**)

| Step | Action | Basis / items to look up |
|---|---|---|
| D-1 | compile the workspace's `.hip` kernel sources directly | in-tree `SwinAttention.hip` (11,988 B), `ImageEncoder.hip` (4,866 B) |
| D-2 | choose a HIP → Intel compilation / compatibility layer | needs external documentation (**D2-new**): ① the support level and limitations of **chipStar** (HIP on SPIR-V / Level Zero); ② other HIP → SYCL / Level Zero paths. The workspace already contains a `USE_CHIPSTAR` branch **declaration**, which can serve as an access point |
| **risk** | ① these `.hip` files are reproduction versions **written by this project itself** (the comment says "Based on kernel signatures extracted from …") and are **not** this DLL's original source —— **the original source does not exist in this workspace**; ② the compatibility layer's support for **SLM / `__shared__`** is a hard constraint of this network (the 64,640 B band), and **whether the compatibility layer supports SLM of that magnitude must be checked** | — |

#### Path E: the **reverse** direction —— dump the weight tensors from the AMD-side runtime

| Step | Conclusion |
|---|---|
| E-1 | **not selectable**: no AMD hardware ⇒ runtime observation is unavailable within this environment |

#### Path comparison (**no selection, criteria only**)

| Path | Prerequisite gap | Depends on existing in-tree assets | Numeric fidelity risk | Provability within this workspace |
|---|---|---|---|---|
| **A** keep the container | P0-a (shape) | **highest** (parser + XMX skeleton) | **lowest** (no intermediate format) | **highest** |
| **B** → OpenVINO IR | P0-a + B-2 / B-3 / B-4 all unproven | medium | medium | low |
| **C** → ONNX | P0-a + C-2 / C-3 unproven | medium | medium-high (one extra layer) | low |
| **D** HIP sources + compatibility layer | D-2 unproven; and the sources are **reproductions, not the originals** | high | low (source level) | medium |
| **E** runtime dump | — | — | — | **not selectable** |

> **This document gives no selection conclusion.** The criterion needed for a selection is the "provability within this workspace" column above —— **A and D are the most provable, but the key unknowns of both (A's P0-a shape, D's D-2 compatibility layer capability) lie outside this workspace**.

### 5.6 Conflict and Ruling on the Layer-Count Rule Between the Two Sides

| Item | Content |
|---|---|
| **source side** | `MAX_LAYERS_PER_BLOCK = 4` (**1 hit** when searched across the whole workspace, no second definition point); `GetNumLayers()` (**2 hits**: definition / call); `ENCODER_END = 22` / `BOTTLENECK_START = 23` / `BOTTLENECK_END = 47` / `DECODER_START = 48` |
| **measurement side** | **1 layer ×47 (0–22, 39, 48–70) / 4 layers ×15 (23–29, 40–47) / 5 layers ×9 (30–38)**; 152 `layer` entries, covering 71 blocks, with contiguous indices (**0 violating blocks**) |
| **ruling** | **the data file wins**. Established rule: "wherever a 'source-code constant vs measured data file' conflict occurs, the data file wins". **Both `MAX_LAYERS_PER_BLOCK = 4` and `GetNumLayers()` are overturned by the measurement** |
| **inconsistent blocks** | **10 (block 30–39)** —— blocks **30–38 measured 5 layers vs predicted 4 layers**; block **39 measured 1 layer vs predicted 4 layers** |
| **criterion hierarchy** | **the weight file is data extracted from the AMD original (hard evidence); the source-code constants are the porter's assumptions**; moreover the weight side has been **independently recomputed by three parties** (all using the header's `count = 153` as the bound, with the three identities closing to 0); the source side has an additional **internal self-contradiction** (`MAX_LAYERS_PER_BLOCK = 4` conflicts with the measured 5-layer blocks; `GetNumLayers()` disagrees with the measurement in **10 blocks**) |
| **registration** | the source-side constants remain in the project tree, and any subsequent citation must first consult this ruling and **must no longer cite the source-code layer-count rule** |

### 5.7 Chapter Summary

| # | Conclusion |
|---|---|
| 6-1 | the weight container is **fully resolved**: `8B 'DLSSNRW1' + uint32 count(153) + uint32 indexEnd(5673) + 153×(u8 nameLen, name, u64 offset, u64 size) + payload 147,683,778 B`; **the three identities close to 0**; **unattributed bytes in the index region = 0** |
| 6-2 | entry names `block<N>.layer<L>.layer` (152) + `block70.layer0.blend_scale` (1); 71 blocks with no missing numbers; `layer` counts **1×47 / 4×15 (23–29, 40–47) / 5×9 (30–38)** |
| 6-3 | element width = **2 bytes**; the numeric interpretation **tends toward FP16** (`blend_scale` = 0.739746), **no full test performed ⇒ not upgraded to proven** |
| 6-4 | weight header ruling: **`DLSSNRW1` wins**; both 4-byte constants are **discarded** |
| 6-5 | kernarg: `align = 8` (8 targets consistent); the 31 kernels' lengths **are all multiples of 8**; **`k_flag_set` = 12 is the only one with mod 8 ≠ 0**; composed of a 66 B implicit span + a 190 B tail; **`align = 8` must not be taken directly as the Xe requirement** |
| 6-6 | conversion paths: **four candidates A / B / C / D plus E which is not selectable**; **this document makes no selection**; **A and D are the most provable**, but the key unknowns are all **outside this workspace** |
| 6-7 | "the 153 payload hashes are pairwise distinct" is an **unverified self-report** and **must not be treated as confirmed** |

---

## 6. Roadmap

> **Scope of this roadmap.** S0–S7 below is the **Intel track** of a larger, multi-stage effort: recover the source -> a common-instruction build -> vendor-accelerated backends (Intel / AMD / NVIDIA) -> one cross-GPU codebase. This roadmap covers the Intel-accelerated path only; the other tracks are described in [01-Project-Background.md](01-Project-Background.md) §2.0. Do not read this chapter as the whole project plan.

> **Roadmap discipline**: the **stage division of this roadmap is based on confirmed facts**; wherever a stage's **determination premise** belongs to "needs external documentation", **that stage is marked "prerequisite unclosed"**, and the items to look up it depends on are listed explicitly. One **must not** write "needs external documentation" as "the conditions are already in place".

### 6.1 Overview of the Stage Division

| Stage | Name | Prerequisite stages | Prerequisite unclosed items | Output |
|---|---|---|---|---|
| **S0** | criteria settled (external documentation verification) | — | — (this stage exists to close them) | the **conclusions** for items to look up T-01…T-24 + E1–E5 + A4 / B4 / C7 / D1 + K5 / K6 / K10 + each field item of §2.4(c) |
| **S1** | environment and toolchain in place | S0 (partial) | **E-2 / E-3** (disassembler, Intel toolchain unavailable within this environment) | a build and debug environment that can compile / disassemble / run |
| **S2** | host-side replacement layer | S1 | §4.5 items 1–11 | the replaced host import surface (29 → SYCL / Level Zero) |
| **S3** | weights and kernarg | S1 | **P0-a / P0-b / P0-c**; K5 / K6 / K10 | a loadable weight path + per-kernel kernarg layout |
| **S4** | kernel recompilation (in batches by A / B / C) | S1, S3 | T-01 / T-02 / T-03 / T-04 / T-06 / T-07 / T-08 / T-09 / T-12 / T-13 / T-15 | SPIR-V / XMX implementations of the 34 kernels (in three batches) |
| **S5** | block-layer scheduling completion | S4 | **per-block → kernel dispatch unobtainable**; `VarParams` 168 B; idx 949 / 951 | the per-block → kernel dispatch implementation for the 71 blocks |
| **S6** | end-to-end numerical and performance acceptance | S2, S4, S5 | all of the above | a runnable, evaluable ported version + a numerical comparison against the original |
| **S7** | integration and delivery | S6 | — | deliverable artifacts + a complete evaluation report |

### 6.2 Stage-by-Stage Expansion

#### S0 Criteria Settled (External Documentation Verification)

- **what to do**: verify item by item according to the list in §8; **what is produced is "conclusions", not "code"**;
- **priorities (based on scope of impact)**:

| Priority | Items to look up | Scope of impact |
|---|---|---|
| **P0** | T-01 / T-02 / T-03 / T-15 (**the determination premises of the roadmap**: they decide whether to take XMX or generic SPIR-V) | 25 / 4 / 8 / 34 kernels |
| **P0** | T-04 / T-06 / T-08 / T-11 / T-12 (**affecting all 34 kernels**); A4 / B4 / C7 / D1 / K5 | all 34 |
| **P1** | T-05 / T-07 / T-09 / T-10 / T-13 / T-14 / T-16 / T-17 / T-18 / T-19 / T-23 / E1–E5 / K6 / K10 / A2-new / A3-new / D2-new | by facet |
| **P2** | T-20 / T-21 / T-22 / T-24 / S1-new / B2–B4-new / C2–C3-new | by facet |

- **verifiable milestones**:
  - **M0-1**: T-01 / T-02 / T-03 / T-15 **each have a conclusion**, and the conclusions **can each be traced back to the cited specification section number** (not "we looked it up");
  - **M0-2**: according to T-01's conclusion, the 5-step partition method of §3.3 **can fill all 34 rows per row** (each row having a unique value), **with no "needs external documentation" remaining**.

#### S1 Environment and Toolchain in Place

- **what to do**: obtain (a) a usable Intel oneAPI / DPC++ (`icpx` / `dpcpp`) toolchain; (b) AMDGPU disassembly capability (`llvm-objdump` or a disassembly library supporting AMDGPU); (c) Intel Arc B580 hardware and driver;
- **verifiable milestones**:
  - **M1-1 (toolchain)**: `icpx --version` / `dpcpp --version` return success (current state: `Get-Command` gets **0 hits each**);
  - **M1-2 (disassembly)**: disassemble the `.text` of the `#1` bundle, **resolving at least 1 instruction successfully** (current state: **the number of disassembled instructions = 0**). **Recomputable criterion**: disassembly output line count > 0;
  - **M1-3 (hardware)**: device enumeration can list Intel Arc B580, and `info::device::local_mem_size` can be queried (current state: **no AMD hardware, and the in-house skeleton does not query SLM capacity**).

#### S2 host-Side Replacement Layer

- **what to do**: replace the 29 `amdhip64_7` import entries with SYCL / oneAPI Level Zero (the per-entry table of §4.3); complete the filling mechanism of the 17 export slots;
- **verifiable milestones**:
  - **M2-1**: the replaced module's **import surface contains 0 `amdhip64_7` entries** (criterion: re-run §4.1's import parsing on the product PE, with `amdhip64_7` entry count == 0);
  - **M2-2**: all 29 replacements **have an implementation, item by item**, and the **60 call sites** corresponding to `hipLaunchKernel` are completed site by site (criterion: the call-site count drops from 60 to 0, or all are redirected to the Level Zero / SYCL path);
  - **M2-3**: the **2 APIs requiring argument changes** (`hipGetLastError` 3 sites, `hipGetDevicePropertiesR0600` 3 sites) have their arguments changed site by site (criterion: the parameter structs at those 6 call sites are no longer AMD-proprietary layouts).

#### S3 Weights and kernarg

- **what to do**: convert the weights into a form loadable on the Intel side via one of the paths in §5.5 (**selection after S0**); rebuild the per-kernel kernarg layout according to §5.4;
- **the prerequisite unclosed items P0-a / P0-b / P0-c must first be closed in S0**;
- **verifiable milestones**:
  - **M3-1 (container fidelity)**: whichever path is taken, **the output tensor set corresponds one-to-one to the 153 inputs** (criterion: entry count == 153, name sets identical character by character, each `size` identical); **recomputable**: re-run the three identities of §5.1(b) on the conversion product;
  - **M3-2 (offset semantics)**: the conversion product satisfies `offset[0] == 0` and `offset[i] == Σsize[0..i-1]`;
  - **M3-3 (numeric scope)**: the element type is **settled by a full statistical test** (closing E2);
  - **M3-4 (kernarg)**: the kernarg layouts of the 34 kernels are produced per kernel, and **the 31 kernels satisfy `size mod 8 == 0`, with `k_flag_set` handled separately**.

#### S4 Kernel Recompilation (in batches by A / B / C)

| Batch | Kernel count | Nature of the work | Prerequisite items to look up |
|---|---|---|---|
| **S4-A** | **7** (k10, k13, k20, k21, k22, k23, k24) | **neither the resource surface nor the parameter surface needs rewriting** ⇒ recompile first | T-04 / T-12 (global items) |
| **S4-B** | **20** | **the resource surface needs per-target recomputation for Xe** (SLM / private segment / spill) | T-06 / T-07 / T-08 / T-09 / T-16 |
| **S4-C** | **7** (k0, k1, k2, k5 + k26, k27, k28) | **requires redesign** (SLM partitioning, or the parameter-passing form and its device-side semantics) | T-01 / T-03 / T-06 / T-13 |

- **the conclusions of T-01 / T-02 / T-03 / T-15 decide whether S4 is the "XMX path" or the "generic SPIR-V path"**;
- **verifiable milestones**:
  - **M4-1**: each batch of kernels **compiles** (criterion: the corresponding kernel name appears in the compilation product; current state: **no toolchain, cannot compile**);
  - **M4-2 (resource surface)**: each kernel's actual SLM / private-segment request amount on the Xe side is **queryable per kernel** (criterion: give the query interface name + measured value, and compare row by row against the `group` / `priv` of §2.5);
  - **M4-3 (class C)**: the per-target verification of k1's 64,640 B is complete (criterion: give the difference between the measured Xe-side limit and 64,640; **currently the known margin is 896 B**);
  - **M4-4 (exception kernels)**: the **independent implementation of the parameter-passing form** of k26 / k27 / k28 is complete (criterion: the three no longer apply the `+206` formula; `k_align_probe` is handled as "no `by_value` parameter");
  - **M4-5 (operator surface)**: the "XMX direct support / generic SPIR-V" of 34/34 kernels **has a unique value per row** (criterion the same as M0-2).

#### S5 block-Layer Scheduling Completion

- **what to do**: complete the **per-block → kernel dispatch**;
- **known state (must be phrased this way)**: **the topology and rule layer are determined by source-code hard constants**; **the per-block → kernel dispatch is unimplemented**; **and the rule layer conflicts with the weight measurement (a mixed arrangement of 1 / 4 / 5 layers)**;
- **prerequisite for progress (constraint confirmation)**: **M5-1 (layer → kernel binding) cannot be completed under the available conditions.**

  - **determined**: the **layer counts** (weight measurement 1×47 / 4×15 (23–29, 40–47) / 5×9 (30–38)), the **topology** (segmentation), the **kernel name set** (34 names);
  - **unobtainable (no solution under the available conditions)**: **the "layer → kernel binding"** —— see §8 U-16; **the internal layout of `VarParams` 168 B** —— see §8 U-4; **the internal composition of `SwinParams` (k0) `by_value` 40 B** —— see §8 U-17;
  - **⇒ this stage cannot be completed under the available conditions; it must not be phrased as "can progress", "pending restoration of hardware conditions", or "pending later closure".**

- **constraint (in effect permanently)**: **AMD hardware is not provided, and will not be provided permanently**; **the runtime observation path is permanently closed** ⇒ this clause no longer uses wording such as "pending restoration of AMD hardware conditions";

- **verifiable milestones**:
  - **M5-1**: all 71 blocks **have a unique kernel dispatch per block** (criterion: give a 71-row dispatch table, with each row's kernel name taken from the 34-name set); **❌ cannot be completed under the available conditions**;
  - **M5-2 (layer-count scope)**: the layer counts adopted by the dispatch table **agree with the weight measurement** (criterion: histogram == **1×47 (0–22, 39, 48–70) / 4×15 (23–29, 40–47) / 5×9 (30–38)**); **✅ that input is already in place**;
  - **M5-3 (consistency)**: the **10 inconsistent blocks (30–39)** of `MAX_LAYERS_PER_BLOCK = 4` and `GetNumLayers()` are explicitly disposed of in the implementation (criterion: give the disposition record for these 10 blocks, including block 39); **✅ that input is already in place**.

- **rule-source ruling**: this stage adopts **the set of rules from the weight measurement**; the source-code set (segmentation constants + `GetNumLayers()` both 4 layers) is **void (kept only as historical trace)**.

#### S6 End-to-End Numerical and Performance Acceptance

- **verifiable milestones**:
  - **M6-1**: the ported version **renders one frame** on Arc B580 (criterion: the output is non-empty and there are no device errors);
  - **M6-2 (numerical comparison)**: **the output difference from the original on the same input is quantifiable** (criterion: give a per-pixel difference metric). **Note**: **the original's output cannot be obtained within this environment** (E-1) ⇒ this milestone **can only be completed in an environment with AMD hardware**;
  - **M6-3 (performance)**: give the end-to-end time and a per-kernel time breakdown.

#### S7 Integration and Delivery

- **output**: deliverable artifacts + a complete evaluation report + a risk statement consistent with the unclosed items.

### 6.3 Dependency Graph (textual DAG)

```
S0 (criteria settled)
 ├─> S1 (environment and toolchain)
 │    ├─> S2 (host-side replacement) ─────────────┐
 │    ├─> S3 (weights and kernarg) ─> S4 (kernel recompilation, three batches A/B/C) ─> S5 (block dispatch)
 │    └──────────────────────────────────┴─> S6 (end-to-end acceptance) ─> S7 (integration and delivery)
 └─> (S0's four P0 items: T-01 / T-02 / T-03 / T-15 decide the path form of S4)
```

**Critical path**: **S0 → S1 → S3 → S4 → S5 → S6 → S7** (S2 can run in parallel with S3 / S4).

### 6.4 Overall Milestone Verifiability Table (**23/23, each with a recomputable criterion**)

> **Coverage statement**: this table covers **all 23 milestones** in the stage-by-stage expansion of §6.2 (S0 2 + S1 3 + S2 3 + S3 4 + S4 5 + S5 3 + S6 3 = 23), **with no omissions**.

| Milestone | Recomputable criterion | Current state |
|---|---|---|
| M0-1 | T-01 / T-02 / T-03 / T-15 **each have a conclusion**, and the conclusions **can each be traced back to the cited specification section number** | **not achieved within this environment** |
| M0-2 | according to T-01's conclusion, the 5-step partition method of §3.3 **can fill all 34 rows per row** (each row having a unique value), **with no "needs external documentation" remaining** | **not achieved within this environment** (currently 34/34 are all "needs external documentation") |
| M1-1 | `icpx --version` / `dpcpp --version` return success | **not achieved** (`Get-Command` 0 hits each) |
| M1-2 | `#1` bundle `.text` disassembly output line count > 0 | **not achieved** (number of disassembled instructions = 0) |
| M1-3 | `info::device::local_mem_size` can be queried | **not achieved** (the in-house skeleton queries only `max_compute_units` / `global_mem_size` / `max_work_group_size`) |
| M2-1 | the `amdhip64_7` entry count of the product PE == 0 | **not achieved** (currently 29) |
| M2-2 | the `hipLaunchKernel` call-site count goes from **60** → 0 | **not achieved** |
| M2-3 | the **2 APIs requiring argument changes** have their arguments changed site by site | **not achieved** |
| M3-1 | the conversion product's entry count == **153** and the name set is identical character by character | **not achieved** |
| M3-2 | `offset[0] == 0`, `offset[i] == Σsize` | **achieved** for the source container; not verified for the product |
| M3-3 | the element type is given as a choice between FP16 / BF16 + full evidence | **not achieved** (currently only a sampling tendency) |
| M3-4 | the mod 8 distribution of the 34 new layouts == 33 zeros + `k_flag_set` 4 | **not achieved** |
| M4-1 | the corresponding kernel name appears in the compilation product | **not achieved** |
| M4-2 | each kernel's actual SLM / private-segment request amount on the Xe side is **queryable per kernel** | **not achieved** |
| M4-3 | give the difference between the measured Xe SLM limit and 64,640 | **not achieved** (the margin 896 B is known; the limit value has not been obtained) |
| M4-4 | the **independent implementation of the parameter-passing form** of k26 / k27 / k28 is complete | **not achieved** |
| M4-5 | the "XMX direct support / generic SPIR-V" of 34/34 kernels **has a unique value per row** | **not achieved within this environment** |
| M5-1 | a 71-row dispatch table with kernel names taken from the 34-name set | **not achieved** (and **cannot be completed under the available conditions**) |
| M5-2 | histogram == 1×47 / 4×15 / 5×9 | **achieved** on the weight side; not verified on the dispatch-table side |
| M5-3 | the 10 inconsistent blocks (30–39) are explicitly disposed of in the implementation | **not achieved** |
| M6-1 | the ported version **renders one frame** on Arc B580 | **not achieved** |
| M6-2 | a per-pixel difference metric | **unachievable within this environment** (E-1) |
| M6-3 | give the end-to-end time and a per-kernel time breakdown | **not achieved** |

### 6.5 Chapter Summary

| # | Conclusion |
|---|---|
| 7-1 | the roadmap has **8 stages, S0–S7**, with critical path **S0→S1→S3→S4→S5→S6→S7** |
| 7-2 | **S0 is the only stage with no prerequisite**, and **T-01 / T-02 / T-03 / T-15 are the determination premises for the path form of S4** |
| 7-3 | **all 3 milestones of S1 are currently unachieved** (the three classes of capability —— toolchain / disassembly / hardware —— are unavailable within this environment) |
| 7-4 | the three batches of S4 = the A / B / C classes of §1 (**7 / 20 / 7**) |
| 7-5 | **M6-2 is unachievable within this environment** (the original's output cannot be obtained) |
| 7-6 | **all 23 milestones are given recomputable criteria** (file fingerprints / entry counts / histograms / mod 8 distribution / identities / call-site counts), and the overall table covers **23/23** |

---

## 7. Unclosed Items and Risks

### 7.1 block-Layer Scheduling Logic (**must be phrased as in this section**)

| Item | Accurate statement |
|---|---|
| **(a) topology and rule layer** | **already determined by source-code hard constants**: giving `ENCODER_END = 22` / `BOTTLENECK_START = 23` / `BOTTLENECK_END = 47` / `DECODER_START = 48`; `GetNumLayers()` = 4 layers in the bottleneck, 1 layer elsewhere; `GetWindowSize()` = encoder 32 / bottleneck `<30 → 64`, `<40 → 128`, `≥40 → 256` / decoder 32; the main loop `for b in 0..70` pings-pongs layer by layer |
| **(b) per-block → kernel dispatch** | **unimplemented**: the four function bodies **are all `return true;`** (`EncodeInput` / `RunSwinBlock` / `RunProjectionBlock` / `DecodeOutput`), and the two `Get*Features()` return `nullptr` |
| **(c) rule layer conflicts with the weight measurement** | **holds**: the source rules predict "the bottleneck 23–47 uniformly 4 layers", while the weight measurement is a **mixed arrangement of 1 / 4 / 5 layers**. **inconsistent blocks = 10 (30–39)** —— blocks **30–38 measured 5 layers vs predicted 4 layers**; block **39 measured 1 layer vs predicted 4 layers** |

### 7.2 List of Unclosed Items

| # | Unclosed item | Accurate statement |
|---|---|---|
| **U-1** | **the per-block → kernel dispatch of block-layer scheduling** | **unimplemented** (all four function bodies are `return true;`); **the topology and rule layer are determined**; **and the rule layer conflicts with the weight measurement (a mixed arrangement of 1/4/5 layers, 10 inconsistent blocks = 30–39)** |
| **U-2** | **compatibility ruling** | the input `0x5A = 90` and the output `0x57 = 87` are **both > 70**, incompatible with the "0–70 index space"; **that enum's upper bound is undetermined** |
| **U-3** | **the semantics of idx 949 / 951 are undetermined** | **2** of the **6** occurrences of the same signature are undetermined. Coordinates: `0x180048A44` (idx 949, `83 F9 1A 74`), `0x180048ECC` (idx 951, `83 FA 1A 0F`) |
| **U-4** | **the internal layout of `VarParams` 168 B** (**qualification: no solution under the available conditions**) | **no solution under the available conditions** (the 5 `k_swin_var`: k29–k33). **Partial information**: the in-tree source gives 16 named fields (7 `half*` + `int B,H,W,C` + `int windowSize,numHeads,headDim` + `float scale` + `int shiftSize`); **but that source struct comes to 92 B counting 64-bit pointers, whereas the DLL-side `by_value` = 168 B ⇒ the two are not the same layout**, and moreover **that tree is non-isomorphic to the DLL** (28/30 deduplicated basenames are absent from it) ⇒ the source structs **cannot** serve as a basis for the DLL-side layout. **`.args` declares only the total byte count of `by_value`, with no field names / field boundaries** ⇒ **there is no criterion within this environment to resolve the internal composition of the 168 B**. **Same family**: U-17 |
| **U-5** | **field attribution of the 190 B tail and the 16 B hole** | **not resolved** (constant across 31 kernels × 8 targets; neither has a corresponding `.args` entry). Also: `190 mod 8 = 6`, and **the relation to `align = 8` is unresolved** |
| **U-6** | **the runtime filling mechanism of the `.data` 17-item pointer table** | **the capability exists; the actual filling path is unproven**. Proven: the 17 slots exceed the `.data` raw coverage (`0x180076440..0x1800764C0`), **no file bytes**, **no `.reloc` coverage**, and the capability of `GetProcAddress` / `LoadLibraryA` / `LoadLibraryExW` / `FreeLibrary` / `GetModuleHandleA/W` exists. **Unproven**: which call site actually fills them back, using which API |
| **U-7** | **the semantics of `swin_layer` and the cause of its occurrence range** | `_Z10swin_layerR7SwinLDSPKhRK10BlobLayouti` (**non-template**) exists only in `#2`–`#5`, **is not among the 34 kernel names**, and **has no `.kd` descriptor**; its call relationship with the 34 kernels **is unproven** (no AMDGPU disassembler); `SwinLDS` / `BlobLayout` get **0 hits** across the project tree's whole tree ⇒ **no source to refer to** |
| **U-8** | **the semantics of `g_e4m3_lut` (512 B, all zero across the 8 targets)** | **undetermined**: is it an all-zero placeholder or filled at runtime? Write-site determination requires instruction-level disassembly (E-2 unavailable); runtime memory-image comparison requires AMD hardware (E-1 unavailable). Its **only reference sites = 2 8-byte encodings per bundle** (1 inside `.rodata` + 1 inside `.text`); **no field among the 272 `.kd` descriptors equals that symbol's VA** |
| **U-9** | **whether the self-developed project tree's XMX code was ever successfully compiled and run** | **no criterion**: `build/` contains **no `.sycl` compilation artifact**, the mtimes of the 6 exes are concentrated within two days, the exe import tables were not read, and the toolchain is unavailable |
| **U-10** | **the operator semantics of `k_expand` / `k_contract`** | **unresolved**: in a tensor-operator context the two names (Expand / Contract) can point to several semantics (broadcast / tensor contraction / index expansion); the only criteria in this environment are the names and the `B` sizes. **That tree has no corresponding implementation either** (both names get **0 hits** in that tree) |
| **U-11** | **the relationship between the weights inside `.hip_fat` and the external weights file** | **unproven**: the 147 MB-scale entity is confirmed to be an **external file**; but "the correspondence between that external file and the `.hip_fat` inside the DLL (6,649,000 B)" **remains unproven** |
| **U-12** | **the two diagnostic-class pending items on the gate side** | requires files outside the workspace; **statically undecidable** |
| **U-13** | **the 6 deduplicated `descsz` values across the 8 bundles** | value set = `0x8B72`(#1) / `0x8B84`(#2) / `0x8B7C`(#3) / `0x8B7C`(#4) / `0x8B7D`(#5) / `0x8B78`(#6) / `0x8B78`(#7) / `0x87DA`(#8); **max − min = 938 (`0x3AA`)** (**the older record "1,410 B" is an arithmetic error**) ⇒ **one must not assume the metadata of the 8 targets is byte-identical** |
| **U-14** | **the `kernarg_segment_size = 12` of `k_flag_set`** | **12 is not a multiple of 8** (mod 8 = 4) —— the **only** entry among the 272 with `mod 8 ≠ 0` ⇒ on the Xe side its **segment length must be handled separately** |
| **U-15** | **the caller set of `swin_layer` (first-level criterion for LDS repartitioning)** | **has not landed**: the caller is not located (`SwinLDS` is a **parameter type name** and cannot be mapped directly to a kernel name) |
| **U-16** | **the "layer → kernel binding"** (**qualification: no solution under the available conditions**) | **no solution under the available conditions**. Known: the **layer counts** (weight measurement 1×47 / 4×15 / 5×9), the **topological segmentation**, the **34 kernel name set**; but **"which of the 34 names a given layer calls" has no criterion whatsoever**, and all four avenues **are fully closed**: ① **DLL static analysis** has reached its boundary (the intersection of the dispatcher with the set of functions containing `hipLaunchKernel` = 0); ② **the workspace source** is an empty shell (four function bodies `return true;`) + **non-isomorphic to the DLL** (28/30 deduplicated basenames are absent from it); ③ **the weight file** is exhausted —— **140 patterns, the whole file including the payload region, byte-by-byte matching**: `shape` / `dtype` / operator type / `kernel` name (including the **superset prefix `k_`**) / an independent `block` index field **all get 0 hits**, and **byte-by-byte attribution of the index region: unattributed = 0** (outside the 153 descriptors there is **no second table / no hidden metadata region**); ④ **runtime observation is permanently closed**. **⇒ this gap directly blocks S5 / M5-1; it cannot be completed under the available conditions** |
| **U-17** | **the internal field composition of `SwinParams` (k0) `by_value = 40 B`** (**qualification: no solution under the available conditions**) | **no solution under the available conditions**. The DLL metadata measures k0's `by_value` parameter as `size = 40`, `offset = 0`, `kernarg_segment_size = 296`, `align = 8`; k0's 14 `.args` = **1 `by_value` (40 B) + 13 `hidden_*` (no `global_buffer` parameter at all)**. **Which fields fit in the 40 B, and how many bytes each: no solution**; **the cause of the difference (52 B) from the source `SwinParams` (92 B counting 64-bit pointers): no solution**. **Same family**: U-4. **Criterion boundary**: `.args` declares only the **total byte count** of `by_value`, **not field names / field boundaries**; the external material (upstream pass source, network definition) is not in the workspace |
| **U-18** | **the conflict between the source rules and the weight measurement has not been disposed of uniformly in the documentation** | **ruled**: §6.2 S5 adopts **the set from the weight measurement** (the source set is void, kept only as trace); **criterion hierarchy** = the data file (extracted from the AMD original) outranks the source-code constants (the porter's assumptions). **Retained as a registered item** |

### 7.3 Risk List (ordered by severity)

| # | Risk | Severity | Basis |
|---|---|---|---|
| **R-1** | **the SLM margin is extremely small**: k1's 64,640 B is only **896 B (0.875 KiB)** from the 64 KiB limit —— the smallest margin among all 272 entries; any Xe-side SLM alignment / reserved overhead will consume it first | **high** | §2.1(a) |
| **R-2** | **`#8 gfx9-generic` is a systematic outlier target**: `wavefront_size` 64 (unique), the two `priv` unique extremes (404 / 84), and `workgroup_processor_mode` **entirely absent** ⇒ **taking parameters from a single target will go systematically wrong** | **high** | §2.2, §2.3, §2.4(d) |
| **R-3** | **the rule layer conflicts with the weight measurement**: the source's "bottleneck uniformly 4 layers" is overturned; **block 39 is the second kind of inconsistency** (measured 1 layer vs predicted 4 layers), and **that block is missing from the older registration** | **high** | §5.6, §7.1 |
| **R-4** | the **8 kernels with `maxWG` = 1024** must be verified jointly against the Xe work-group limit; the in-house query returns a **device-level** limit, and **whether it equals the kernel-level feasible limit is unconfirmed** | **medium** | §2.5 item to look up `D1` |
| **R-5** | **operator semantics can only reach "name-based inference"**: source ruled out + comparison module does not hold + no hardware + 0 hits for operator names inside the DLL ⇒ a semantic error **cannot be discovered within this environment** | **medium** | §3.1 |
| **R-6** | **the register pressure of `k_conv_res2` is the highest band in the whole library** (`vgpr` 202, `sgpr` 107), and **its 404 B private segment is the largest in the whole library** (`#8` only) | **medium** | §2.4(d), §2.5 |
| **R-7** | **the kernarg segment length 12 of `k_flag_set` is unaligned** (mod 8 = 4) | **medium** | U-14 |
| **R-8** | **both 4-byte weight header constants are wrong in the same way**: neither `0x524E4C44` nor `0x524E4844` corresponds to any field in the measured file; the in-tree magic check returns false on the measured file ⇒ **if downstream trusts that code, it will reach the opposite conclusion** | **medium** | §5.2 |
| **R-9** | **the project tree is misread as "the 34 kernels already have XMX implementations"**: it actually covers only **6/34**, and its `joint_matrix` usage is concentrated inside **1 template with 0 instantiations** | **medium** | §0.3(b), §3.4 |
| **R-10** | **neither the shape nor the element type of the 147 MB weights is closed** (the container has no shape / dtype field) ⇒ the P0 prerequisite of every conversion path has a blocking point | **medium** | §5.5 common prerequisite P0 |
| **R-11** | **all three classes of verification (runtime, instruction-level, compile-level) are not executable within this environment** (E-1 / E-2 / E-3) ⇒ **the verification ceiling of all conclusions is "static byte level"** | **medium** | §0.1 |
| **R-12** | **`descsz` is unequal across bundles** (6 deduplicated values, max − min 938) ⇒ one must not assume the metadata of the 8 targets is byte-identical | **medium** | U-13 |
| **R-13** | **the internal layout of `VarParams` 168 B is unresolved** ⇒ the kernarg packing of the 5 `k_swin_var` cannot be reconstructed field by field | **low** | U-4 |
| **R-14** | **the attribution of the 190 B weight tail and the 16 B hole is unresolved** ⇒ it cannot be judged whether they need alignment on the Xe side | **low** | U-5 |
| **R-15** | **the semantics of the two symbols `swin_layer` / `g_e4m3_lut` are undetermined** | **low** | U-7, U-8 |

### 7.4 Compatibility Ruling (expansion of U-2)

| Item | Content |
|---|---|
| conflict | the input `0x5A = 90` and the output `0x57 = 87` are **both > 70**, incompatible with the "block index space 0–70" |
| confirmed adjacent facts | **4 block renumbering semantics**: `9 → 0x0A`, `23 → 0x18`, `27 → 0x1C`, `90 → 0x57`, with **all other values including `26` keeping their original value**; the four sites differ in check order (positions 1/2 test `0x5A` first; positions 3/4 test `0x1B` first); all four are outside the dispatcher |
| status | **that enum's upper bound is undetermined**; this document **gives no conclusion** |
| impact | the **input / output enums** of the block layer must first be bounded when recompiling for Xe, otherwise the domain of the dispatch table is undetermined |

### 7.5 Closed Items (**must not be listed as unclosed again**; for downstream to avoid duplicated work)

| # | Closed item |
|---|---|
| 1 | **34 = 29 (table A: 26 same-template + 3 auxiliary) + 5 (table B) = total kernels in `.hip_fat`** |
| 2 | **the 34 kernel names can be statically recovered + registration pairing 34/34** |
| 3 | **the full slot semantics of the two 8-byte-stride tables** |
| 4 | **the kernarg layout of the 34 kernels** (440 parameters per target / 3,520 in total; 3 exceptions; `k_reproject` = 384) |
| 5 | **18 resource fields (key union) / 16 field entities: 8 consistent / 8 inconsistent** |
| 6 | **`.reloc` coverage of tables A/B = 26 / 5** (19 blocks / 2044 entries) |
| 7 | **the `.data` file image boundary** (VSize `0x4390` / RSize `0x2200`) |
| 8 | **the two builds differ by only one constant** (240 B all in `.rdata`) |
| 9 | **the semantics of the 4 block renumberings** |
| 10 | **the dispatcher boundary** (`.pdata` idx 167 / len 2470 / 38 call / 19 targets) |
| 11 | **the 31 same-template instances** (idx 0–25 + 351 / 365 / 366 / 367 / 368; length 93 each; deduplicated = 1) |
| 12 | **the weight container format** (three identities closing to 0) |
| 13 | **the weight header ruling** (`DLSSNRW1` wins) |
| 14 | **the layer-count histogram** (1×47 / 4×15 / 5×9) |
| 15 | **the three `.kd` ↔ msgpack items 272/272 consistent**; `entry == code symbol VA − .kd symbol VA` **272/272, 0 counterexamples** |
| 16 | **194 import entries / 29 HIP / `E8` = 349 / direct IAT references = 0** |

### 7.6 Capability-Boundary Registration

> **Purpose of the registration**: to prevent downstream from misreading "no undeclared changes were found" as "it has been verified that there are no undeclared changes". This row is a **capability-boundary declaration**, not a finding of defect.

| # | Item | Content |
|---|---|---|
| **O-2** | **the first-version comparison is not executable within this environment** | the **first-version comparison** of a certain review report is not executable within this environment: an independent check confirmed that **the first-version entity gets 0 hits on disk** (searching by `73,194 B` finds **0 files**; searching by the hash `3A03DE7A` **hits only that review report itself** (because it cites that constant string), **no file's actual hash equals `3A03DE7A…`**; searching by file name finds **only** the one current version, with **no `.bak` / old copy / sibling backup**). ⇒ When citing that review's "**no undeclared changes**" conclusion, one must state that **its basis is an internal self-consistency check (revision-record numbers are consecutive, anchors exist, self-reported counts collide consistently with measurements), and that it was not verified by a first-version comparison** |

**Citation discipline**: wherever a statement of the "confirmed no undeclared changes" kind appears, the **qualifier** from the table above ("not verified by a first-version comparison; the basis is an internal self-consistency check") **must** be given simultaneously, and it **must not** be upgraded to "verified".

### 7.7 Chapter Summary

| # | Conclusion |
|---|---|
| 8-1 | block-layer scheduling: **the topology and rule layer are determined by source-code hard constants; the per-block → kernel dispatch is unimplemented; the rule layer conflicts with the weight measurement (a mixed arrangement of 1/4/5 layers, 10 inconsistent blocks = 30–39)** |
| 8-2 | rulings on the three conflicts: ① layer counts → **the data file wins**; ② build file location → **the project root wins**; ③ weight header → **the measured `DLSSNRW1` wins** |
| 8-3 | **18 unclosed items** (U-1 … U-18), including block enum compatibility / the semantics of idx 949-951 / the internal layout of `VarParams` 168 B / attribution of the 190 B weight tail |
| 8-4 | **15 risks**, the top 3 being the 896 B SLM margin, the `#8` systematic outlier, and the rule layer conflicting with the measurement |
| 8-5 | **16 closed items**, which downstream **must not list as unclosed again** |

---

## 8. List of External Documentation to Look Up

> **Statement of the nature of this chapter**: this chapter gives, **item by item**, the items that "can only be determined by consulting external documentation". **For each item no conclusion is given**, only "**the item to look up / why it must be looked up / which kernels it affects / the direction of verification**".

### 8.1 Roadmap Determination Premises (**four, highest priority**)

| ID | Item to look up | Why it must be looked up | Which kernels it affects | Direction of verification |
|---|---|---|---|---|
| **G-01** | **whether Intel XMX provides directly callable primitives for matrix multiply / convolution; the coverage of its precision modes (including FP8 / FP16 / BF16 / INT8)** | among the 34 kernel names, forms such as `qkv` (k5 / k8 / k11 / k15), `attention` (k12 / k16), `conv_res` (k4 / k7 / k18), `ffwd` (k3 / k6 / k17), `swin` (k0 / k1 / k2 / k29–k33) all fall within the name domain of the three operator classes "matrix multiply / convolution / elementwise". **There is no criterion whatsoever within this environment** to confirm XMX's support surface for these forms; for the three kernels whose names contain `fp8`, their `.language` is entirely `OpenCL C` and their `.language_version` is entirely `[2,0]` ⇒ **the language surface provides no precision information** | **25** (k0–k19, k29–k33) | the Intel Arc GPU architecture manual (the XMX instructions and data types chapters); the Intel oneAPI Level Zero specification (kernel capability query interfaces); the Intel oneAPI DPC++/SYCL documentation (sub-group matrix extensions). **Source ID: T-01** |
| **G-02** | **whether a primitive exists on the Intel side that can substitute for the semantics of `k_conv_splitk` (split-K convolution); whether the floating-point accumulation order of split-K reduction is constrained by a specification** | the name of `k_conv_splitk` points directly at split-K reduction (multiple work-groups each computing part of K and then accumulating); the names of `k_conv_res` / `k_conv_res2` / `k_conv_res_views` contain "convolution + residual". **There is no criterion within this environment** to determine whether a corresponding primitive exists on the Xe side, nor any criterion to determine whether the accumulation order of split-K is fixed by a specification on the Intel side (**this decides numerical reproducibility**) | **4** (k4, k7, k10, k18) | the oneDNN documentation (the convolution / split-K primitives chapters); the Intel oneAPI Level Zero specification; the SYCL 2020 specification (the floating-point reduction order clauses). **Source ID: T-02** |
| **G-03** | **whether Intel Xe provides the window / shift class primitives required by the Swin transform; the feasible interval of the `swin_var` window parameters (32/64/128/256) on the Xe side** | the 5 `k_swin_var` kernels are distinguished by the template argument for the window size, and the `group_segment_fixed_size` of `k_swin_var<256,false>` = 19,200 is the highest of the whole series. **There is no criterion within this environment** to determine the existence of window class primitives on the Xe side and the window upper bound | **8** (k0, k1, k2, k29–k33) | the Intel Arc GPU architecture manual; the oneDNN documentation (window / tensor re-layout primitives); the Intel GPU programming manual (SLM and work-group size constraints). **Source ID: T-03** |
| **G-04** | **the feasibility and performance boundary of the generic SPIR-V path (non-XMX) for this workload** | if the conclusions of G-01 / G-02 / G-03 are "XMX does not directly support it", the generic SPIR-V path must be taken. Whether that path exists and what its capability boundary is **has no criterion within this environment** | **all 34** | the SPIR-V specification (the general compute instruction set); the Intel oneAPI DPC++/SYCL documentation; the Intel Arc GPU architecture manual (the EU instruction set). **Source ID: T-15** |

### 8.2 Affecting All 34 Kernels (**six, highest priority**)

| ID | Item to look up | Why it must be looked up | Direction of verification |
|---|---|---|---|
| **G-05** | **the set of sub-group (SIMD) width values on Intel Xe and the rule for "mapping work-items to lanes within a work-group"** | `.wavefront_size` measures as **32 (`#1`–`#7`, 238 records) / 64 (`#8`, 34 records)**. AMD's wavefront width and Xe's SIMD width are not the same dimension; it is already established that "the work-item-to-thread mapping must be recomputed according to the Xe target width, and **32 or 64 must not be carried over**", but **that conclusion itself declares that it "makes no assertion"**, and there is no Xe-side value criterion within this environment | the Intel GPU programming manual (the sub-group chapter); the SYCL 2020 specification (`info::device::sub_group_sizes`); the Intel oneAPI Level Zero specification. **Source ID: T-04** |
| **G-06** | **the per-Xe-core SLM (Shared Local Memory) limit on Intel Xe, and whether "SLM limit per work-group" and "SLM limit per Xe-core" are two different constraints** | the maximum `group_segment_fixed_size` over all 272 entries = **64,640 B**, **896 B** below 65,536 B. **There is no criterion within this environment** to determine the Xe-side limit | the detailed specifications of Intel Arc B580; the Intel GPU programming manual (the SLM chapter); the Intel oneAPI Level Zero specification (device memory property interfaces). **Source ID: T-06 / A4** |
| **G-07** | **the register file (GRF) organization of Intel Xe, and whether a conversion rule from AMD `vgpr_count` / `sgpr_count` to Xe register occupancy exists** | `.vgpr_count` has **84 values** (maximum **202**) and `.sgpr_count` has **58 values** (maximum **107**). It is already established that "the two counts **cannot be converted directly** into Xe register counts". **There is no criterion within this environment** to determine whether a conversion rule exists | the Intel Arc GPU architecture manual (the register file chapter); the Intel GPU programming manual; the oneAPI DPC++ compiler documentation (register allocation reports). **Source ID: T-08** |
| **G-08** | **the correspondence between Intel Xe's barrier / fence semantics and AMD's `s_barrier` / `s_waitcnt`** | **15** of the 34 kernels have a non-zero `group_segment_fixed_size`, indicating that work-group-shared-memory communication exists, **whose correctness depends on barrier semantics**. **There is no criterion within this environment** to determine the correspondence between the two sides' barrier semantics | the Intel GPU programming manual (the barrier / fence chapters); the SPIR-V specification (`OpControlBarrier` / `OpMemoryBarrier`). **Source ID: T-09** |
| **G-09** | **the corresponding ABI fields (if any) for `group_segment_fixed_size` / `private_segment_fixed_size` on Intel Xe and their semantics; and the complete value set of the "work-group size / sub-group size / work-group count" execution modes and capabilities in SPIR-V** | what is decidable within this environment is the field semantics of the **AMD-side `amdhsa` metadata**; whether the Xe / SPIR-V side has same-named or corresponding fields and whether the semantics agree **has no criterion within this environment**. `.max_flat_workgroup_size` = **256 × 26 / 1024 × 8** (34-kernel scope); this field is an AMD-side limit, and **how it is expressed on the SPIR-V side and whether a corresponding Capability exists has no criterion within this environment** | the SPIR-V specification (the execution mode and Capability chapters); the Intel oneAPI Level Zero specification (kernel property queries); the SYCL 2020 specification (device-specific kernel queries). **Source ID: T-11 + T-12** |
| **G-10** | **the relationship between the `OpenCL C` language attribute and the HIP compilation chain, and whether that attribute has a corresponding expression on the SPIR-V side** | `.language` = `OpenCL C × 272`, `.language_version` = `[2,0] × 272`. This is **package-time metadata**, indicating that the device code was compiled in an OpenCL C dialect (HIP's device-side front end); **there is no criterion within this environment for the corresponding expression of that attribute on the SPIR-V side** | the SPIR-V specification (the `Source Language` and `Source Language Version` operands); the SPIR-V Extended Instructions for OpenCL; the AMD HIP documentation. **Source ID: T-20** |

### 8.3 By Operator Family (**by facet**)

| ID | Item to look up | Why it must be looked up | Which kernels it affects | Direction of verification |
|---|---|---|---|---|
| **G-11** | **the semantics and precision of Intel Xe's cross-work-item reduction primitives** | the name of `k_mean` (mean) points directly at reduction; the names of `k_attention` / `k_attention2` / `k_qkv_attn` / `k_qkv_attn2` contain attention (which includes reduction). **There is no criterion within this environment** to determine the semantics and precision rules of the Xe-side reduction primitives | **5** (k5, k8, k12, k16, k22) | the oneDNN / oneMKL documentation; the SYCL 2020 specification (the `reduce_over_group` family); the Intel GPU programming manual. **Source ID: T-05** |
| **G-12** | **the limit and alignment rules of Intel Xe's private segment (per-thread private memory / stack)** | the value set of `.private_segment_fixed_size` over all 272 entries = `0×208; 24×38; 64×12; 100×2; 216×2; 244×2; 40×2; 80×2; 88×2; 404×1; 84×1`, with a maximum of **404 (`k_conv_res2` in `#8`)**. **There is no criterion within this environment** to determine the corresponding constraint on the Xe side | k7 (404), k25 (84), k29–k33 | the Intel GPU programming manual (the scratch / private memory chapters); the Intel oneAPI Level Zero specification. **Source ID: T-07 / B4** |
| **G-13** | **the cause of `k_conv_res2` (404 B private segment in `#8`) and `k_reproject` (84 B private segment in `#8`) having a non-zero private-segment requirement only in `#8`, and the corresponding handling of that requirement on the Xe side** | these two kernels' `private_segment_fixed_size` is 0 in `#1`–`#7` and 404 / 84 respectively in `#8 gfx9-generic`. **There is no criterion within this environment** to explain the difference, nor any criterion to determine whether the same kind of difference will occur on the Xe side | **2** (k7, k25) | the Intel GPU programming manual; the AMD GPU programming manual (the scratch allocation differences between `gfx9` and `gfx10+`); the Intel oneAPI Level Zero specification (private memory queries). **Source ID: T-10** |
| **G-14** | **the semantics and available scope of atomic operations and memory ordering on Intel Xe** | the names of `k_flag_wait` and `k_flag_set` point directly at the "read flag / write flag" synchronization primitives, and their mangled formal parameter sequences give **pointer + scalar**, with the storage the pointer refers to shared by multiple kernel instances. **How such semantics are expressed on the Xe side and what the atomicity scope is has no criterion within this environment** | **3** (k26, k27, k28) | the SPIR-V specification (the `OpAtomic*` family and the memory semantics operands); the Intel oneAPI Level Zero specification (atomic operation guarantees); the Intel GPU programming manual (the atomics and memory ordering chapters). **Source ID: T-13** |
| **G-15** | **the data-movement primitives between host and device on Intel Xe (corresponding to the semantics of `k_import` / `k_export` / `k_repack`)** | the names of the three point directly at data ingress/egress and re-layout. **There is no criterion within this environment** to determine the corresponding primitives on the Xe side and their alignment / stride constraints | **3** (k20, k23, k24) | the Intel oneAPI Level Zero specification (the memory copy family); the SYCL 2020 specification (`queue::memcpy` / `copy`); the Intel GPU programming manual (the USM chapter). **Source ID: T-14** |
| **G-16** | **the cause of the `k_ffwd` series' `group_segment_fixed_size` = 0 in `#1` / `#8` but = 24,576 in `#2`–`#7`** | `.kd` and the msgpack metadata are **272/272 consistent**, so this difference is a **real difference and not a parsing error**. **There is no criterion within this environment** to explain the cause, nor any criterion to determine which band the Xe side should take | **3** (k3, k6, k17) | the AMD GPU programming manual (the LDS allocation strategies of `gfx9` / `gfx10` vs `gfx11` / `gfx12`); the Intel GPU programming manual (SLM allocation). **Source ID: T-16** |
| **G-17** | **the internal field layout of `VarParams` (168 B, the user parameter struct of the 5 `k_swin_var`), and its parameter-packing requirements on the Xe side** | that struct's internal layout is **unresolved**; the field attribution of the 16 B hole and the 190 B tail is **unresolved**; the relation between `.kernarg_segment_align = 8` and the 190 tail is **unresolved (190 mod 8 = 6)**. **There is no criterion within this environment** to resolve its internal layout | **5** (k29–k33) | the Intel oneAPI Level Zero specification (kernel parameter packing and alignment); the SYCL 2020 specification (kernel parameter passing rules); **the internal layout of `VarParams` must first be supplied within this environment** (see §7.2 U-4). **Source ID: T-17 / K6** |
| **G-18** | **how "view / stride" class parameters on Intel Xe are expressed inside a kernel and what they cost** | the names of 4 kernels point directly at views: `k_ffwd_inpview` (`FfwdPlParams`), `k_conv_res_views` (`ConvPlParams`), `k_reproject` (`ReprojParams`, `B` = 128, the second largest user struct among the 34), `k_dec_upsample` (`DecUpParams`). **There is no criterion within this environment** to determine the Xe-side view expression and its cost | **4** (k17, k18, k21, k25) | the SYCL 2020 specification (`accessor` / `buffer`'s `range` and `id`); the Intel oneAPI Level Zero specification (USM pointers and offsets); the oneDNN documentation (memory descriptors / layouts). **Source ID: T-18** |
| **G-19** | **the operator semantics of the two kernels `k_expand` / `k_contract` (the concrete meaning of "expand / contract" in a tensor-operator context)** | in a tensor-operator context the two names can point to several semantics (broadcast / tensor contraction / index expansion). The criteria in this environment are only the names and the `B` sizes (24 B / 48 B respectively), **insufficient to choose among several semantics**; the project tree side has no corresponding implementation either (**0 hits** each) | **3** (k9, k13, k14) | the oneDNN documentation (`reorder` / `shuffle` / `reduce` primitives); **the operator semantics must first be obtained within this environment** (see §7.2 U-10). **Source ID: T-19** |

### 8.4 Three Special Symbols and Two Structures Inside the device ELF

| ID | Item to look up | Why it must be looked up | Which kernels it affects | Direction of verification |
|---|---|---|---|---|
| **G-20** | **whether `swin_layer(SwinLDS&, unsigned char const*, BlobLayout const&, int)` is called by one of the 34 kernels** | this symbol exists only in `#2`–`#5` and **is not among the 34 kernel names**. Whether it is the **inlined predecessor** of the 34 kernels (i.e. the product of the `k_swin_var` series inlining `swin_layer` on some targets) or an independent function **has no criterion within this environment** (no AMDGPU disassembly performed) | k0, k1, k2, k29–k33 (related items); **directly related to the four targets `#2`–`#5`** | the AMD GPU programming manual; the AMD HIP documentation (device function inlining strategies); **AMDGPU disassembly capability must be supplied within this environment** (see §7.2 U-7). **Source ID: T-21 / S1-new** |
| **G-21** | **the semantics of the two class names in `swin_layer` and `SwinLDS` / `BlobLayout`; and why that function exists only in the four targets `#2`–`#5`** | that symbol (135,092 / 135,096 B) appears only in `#2` / `#3` / `#4` / `#5`; `#1` / `#6` / `#7` / `#8` get **0 hits**. That function **is not among the 34 kernel names** and **has no `.kd` descriptor**; `SwinLDS` / `BlobLayout` get **0 hits** across the project tree's whole tree ⇒ **no source to refer to** | as above | the AMD GPU programming manual (LDS descriptors and the `gfx11` / `gfx12` differences); the AMD HIP documentation (device function inlining and LDS declarations). **Source ID: T-24** |
| **G-22** | **the semantics of `g_e4m3_lut` (512 B, all zero across the 8 targets)** | each of the 8 device ELFs has a 512 B `g_e4m3_lut` object inside `.rodata`, **512/512 bytes all `0x00`**; **no field among the 272 `.kd` descriptors equals that symbol's VA**. The name contains `e4m3` (a form of FP8) and `lut` (look-up table). **Whether the table is an all-zero placeholder or filled at runtime has no criterion within this environment** | the FP8-related k0, k1, k2; **the related surface covers all 34** | the Intel Arc GPU architecture manual (FP8 formats and conversion instructions); the OCP Microscaling Formats (MX) specification; **"whether there is a write site for that symbol outside `.rodata`" must be supplied within this environment** (requires disassembly). **Source ID: T-22** |
| **G-23** | **whether the project tree's `joint_matrix` GEMM can be reused by the 34 kernels; and whether the scalar loops of that tree's two Swin implementation bodies will be auto-vectorized to XMX by the Intel compiler** | the only implementation body in that tree using `joint_matrix` **gets only 1 hit in the whole tree = the definition line, with no instantiation and no call**; and its two Swin implementation bodies are **scalar triple loops**. **There is no criterion within this environment** to determine "whether a scalar loop is automatically mapped to XMX", nor any criterion to determine whether that template applies to the shapes of the 34 kernels | k0, k29–k33 (which have implementations); if the template is general, **the related surface covers all 34** | the Intel oneAPI DPC++/SYCL documentation (`joint_matrix` usage and tile size constraints); the Intel Arc GPU architecture manual (XMX tile shapes); the SYCL 2020 specification (sub-group matrix extensions). **Source ID: T-23** |

### 8.5 host Side (**11 items**)

| ID | Item to look up | Why it must be looked up | Direction of verification |
|---|---|---|---|
| **G-24** | **the expression and lifetime of the "kernel launch configuration" in SYCL / Level Zero** | `__hipPopCallConfiguration` (68 sites) + `__hipPushCallConfiguration` (34 sites) = **102 call sites**, the most numerous pair in the whole library | SYCL 2020 (`sycl::handler`, `nd_range`, `local_accessor`); the oneAPI Level Zero specification (`zeCommandListAppendLaunchKernel` argument group). **Source ID: §4.5-1** |
| **G-25** | **the Level Zero module format and the SPIR-V module creation flow** | the existing container = `__CLANG_OFFLOAD_BUNDLE__`, with all 8 device triples being `amdgcn-amd-amdhsa` ⇒ **what is being replaced is the container format, not the API** | the oneAPI Level Zero specification (`zeModuleCreate`, `zeModuleDynamicLink`, module formats); the SPIR-V specification (module structure). **Source ID: §4.5-2** |
| **G-26** | **the Level Zero kernel handle acquisition and launch flow** | `hipLaunchKernel` (60 sites) + `__hipRegisterFunction` (34 sites) = **94 call sites** | the Level Zero specification (`zeKernelCreate` / `zeKernelSetArgumentValue` / `zeKernelSetGroupSize` / `zeCommandListAppendLaunchKernel`); SYCL 2020 (kernel naming and `parallel_for`). **Source ID: §4.5-3** |
| **G-27** | **Level Zero access to device globals (symbols)** | the replacement targets of `__hipRegisterVar` / `hipMemcpyToSymbol`; the thunk of `hipMemcpyToSymbol` appears within the enumeration of the dispatcher's 38 `call` targets | the Level Zero specification (`zeModuleGetGlobalPointer`). **Source ID: §4.5-4** |
| **G-28** | **Level Zero's external memory / D3D12 interoperability extensions** | `hipDestroyExternalMemory` (14) / `hipExternalMemoryGetMappedBuffer` (1) / `hipImportExternalMemory` (1), **3 entries** in total; related to the D3D12 interoperability surface | Level Zero external memory extensions; D3D12 ↔ Level Zero interoperability (shared resources / shared fences). **Source ID: §4.5-5** |
| **G-29** | **the counterparts of the device / driver / event / version query APIs** | 9 entries | the Level Zero specification (the device / driver / event families); SYCL 2020 (`device`, `event`, `queue::wait`). **Source ID: §4.5-6** |
| **G-30** | **the counterparts of USM / memory allocation and copy** | 6 entries; `hipMalloc` 35 + `hipFree` 20 + `hipMemset` 29 = **84 call sites** | the Level Zero specification (the three USM allocations, memory copy, memory fill); SYCL 2020 (the three USM allocation types). **Source ID: §4.5-7** |
| **G-31** | **the parameter struct layout of `hipGetDevicePropertiesR0600`** | the name carries an ABI version suffix (`R0600`) and the parameter struct is **AMD-proprietary** ⇒ **per-call-site argument changes are required (3 sites)**; it is not merely swapping the API name | AMD ROCm headers (that struct definition); the oneAPI Level Zero device properties struct. **Source ID: §4.5-8** |
| **G-32** | **the difference in error-code models** | HIP has `hipGetLastError` (a "last error" **global state**, 3 sites) and `hipGetErrorString` (6 sites); Level Zero **returns per call** ⇒ **the call-site structure must change** | the Level Zero specification (return codes and conversion to strings, if present); SYCL 2020 (exceptions and error codes). **Source ID: §4.5-9** |
| **G-33** | **the compatibility of `D3DCompile` / `D3D12SerializeRootSignature` artifacts on Xe** | all **4 graphics-side entries are kept**, but "keeping the import ≠ zero changes": **whether the artifacts of these 7 call sites are compatible with the D3D12 driver on Xe** must be verified | the D3D12 driver documentation for Intel Arc B580; the correspondence between D3DCompile target profiles and the Intel driver. **Source ID: §4.5-10** |
| **G-34** | **whether a reusable path exists for a HIP → SPIR-V porting toolchain** | it decides the **implementation method** of all 29 entries of §4.3 (hand-written one by one vs toolchain conversion). **This document presupposes no conclusion** | the AMD HIP SDK documentation; Intel oneAPI's HIP compatibility layer (if any); the SYCL HIP interoperability documentation. **Source ID: §4.5-11** |

### 8.6 Weights and kernarg

| ID | Item to look up | Why it must be looked up | Direction of verification |
|---|---|---|---|
| **G-35** | **the official field names of the two uint32 at `0x08` / `0x0C`** (**semantics proven**: 153 = entry count, 5,673 = total index-region length; **names unproven**) | when converting formats the writer needs to know the field names (otherwise downstream tools cannot interoperate) | the upstream export tool source; the export script or documentation in the project tree. **Source ID: E1** |
| **G-36** | **the final ruling on the element type FP16 vs BF16** | currently only a **sampling tendency toward FP16** (`blend_scale` = 0.739746; BF16 decodes to non-physical magnitudes), **with no full statistical test performed** ⇒ **it cannot be upgraded to a proven conclusion** | ① magnitude / distribution statistics after a full decode; ② the upstream model definition file; ③ comparison against the weights on the other side. **Source ID: E2 / P0-b** |
| **G-37** | **the shape and tensor semantics of each `layer`** (the container **does not contain** a shape field) | the container is a "name / offset / length" structure with **no shape / dtype** ⇒ the shape must be obtained before converting to any format. **This is the common prerequisite P0-a of all conversion paths** | the upstream model definition file; or infer it from the `block<N>.layer<L>` naming regularity + the payload byte count (**the inference result must be marked as unproven**). **Source ID: E3 / P0-a** |
| **G-38** | **the correspondence between `layer0`–`layer4` and the Swin operators** | it decides the binding relationship between the 5 `k_swin_var` and `layer`; **this document gives no mapping conclusion** | the upstream network definition; runtime observation. **Source ID: E4 / P0-c** |
| **G-39** | **the semantics of `blend_scale` (= 0.739746)** | whether it is the blend coefficient of the final composition decides the role of that `size = 2` tensor in the port | the upstream composition logic; **whether a host-side configuration item is related to it must be confirmed separately (relatedness must not be assumed)**. **Source ID: E5** |
| **G-40** | **the alignment requirement of the kernel parameter (kernarg) segment on Xe** (whether a fixed alignment exists, and whether it is 8/16/32/64 bytes); additional alignment for pointer parameters; the packing rules for 2-byte parameters | `.kernarg_segment_align = 8` is the value in **AMD `amdhsa` metadata** and **must not be taken directly as Xe's requirement**; the kernarg layout of the 34 kernels is one of the core inputs of the port | the "Kernel Arguments" chapter of the Level Zero specification; the kernel parameter passing chapter of the SYCL 2020 specification; the "Kernel Arguments" chapter of the Intel oneAPI GPU Optimization Guide. **Source ID: K5** |
| **G-41** | **field attribution of the 190 B tail and the 16 B hole** (**unresolved within this workspace**) | without resolving the field attribution it cannot be judged whether they need alignment on the Xe side; the relation of 190 mod 8 = 6 to `align = 8` is likewise unresolved | the upstream pass source; runtime observation. **Source ID: K6 / T-17 (partial)** |
| **G-42** | **the Xe compiler's alignment / packing behavior for kernel parameter structs** | the in-tree SYCL kernels pass parameters with `struct` and **do not lay out kernarg manually** ⇒ **alignment is decided by the Xe compiler**, and the compiler's behavior must be checked | the DPC++ / IGC documentation; compiler optimization-report class diagnostics. **Source ID: K10** |
| **G-43** | **the 2-byte element alignment requirements of SYCL `buffer` / USM; the tile sizes and element type combinations supported by `joint_matrix`** | steps A-2 / A-3 of path A; the 2-byte elements come from the measurement (153/153 sizes are even), and the tile combinations decide whether the GEMM can be expressed directly | the "Memory Model" and "USM" chapters of SYCL 2020; the size / type support table in the Intel oneAPI `joint_matrix` documentation. **Source ID: A2-new / A3-new** |
| **G-44** | **the three items of the OpenVINO path**: the manual graph-building API, IR version / FP16 support, and the GPU plugin's exploitation of XMX / whether FP16 is preserved / dynamic shape support | B-2 / B-3 / B-4 of path B are all unproven | the OpenVINO official documentation "Build a Model", "IR specification", "GPU plugin". **Source ID: B2 / B3 / B4-new** |
| **G-45** | **the two items of the ONNX path**: FP16 initializer expression; the XMX support and operator coverage of the three backends (OpenVINO / ORT-DML / oneDNN) | C-2 / C-3 of path C are all unproven | the ONNX specification `TensorProto`; the OpenVINO ONNX front end; the ORT-DML EP; oneDNN GPU support. **Source ID: C2 / C3-new** |
| **G-46** | **chipStar (HIP on SPIR-V / Level Zero) support level and limitations (including the SLM / `__syncthreads` mapping)** | D-2 of path D; **the compatibility layer's support for SLM is a hard constraint of this network** (the 64,640 B band) | the chipStar official documentation (HIP API coverage table, known limitations). **Source ID: D2-new** |

### 8.7 Classification Thresholds and Xe-Side Values

| ID | Item to look up | Why it must be looked up | Direction of verification |
|---|---|---|---|
| **G-47** | **whether this table's self-set thresholds (4096 / 32768 / 64) hold on Xe** | these three thresholds **have no specification source whatsoever** (confirmed by the five-way search R1–R5) ⇒ they are **banding tools**, not platform constraints. The **reversibility** of the classification result with respect to the thresholds has been given (the recomputation under shifted bands is item-by-item identical across all three bands) | look up G-06 (SLM limit) / G-12 (private segment limit) / G-40 (kernarg alignment) together, and judge from those whether the self-set bands align with Xe's actual capacity bands. **Source ID: §1.1 (new)** |
| **G-48** | **the maximum number of work-items per work-group on Intel Xe, and its joint constraint relationship with the SLM / register budget** | the **8 kernels with `max_flat_workgroup_size` = 1024** must be verified jointly against the Xe work-group limit; the in-house query returns a **device-level** limit, and **whether it equals the kernel-level feasible limit is unconfirmed** | the SYCL 2020 specification `info::device::max_work_group_size`; the "Work-group Size" chapter of the Intel oneAPI GPU Optimization Guide; the maximum work-group limit for kernels in the Level Zero specification. **Source ID: D1** |
| **G-49** | **the counterpart of `.workgroup_processor_mode` on the Xe side** | this field is 1 for `#1`–`#7` and **entirely absent in `#8`** (34/34 kernels) ⇒ it cannot serve as cross-target common input | the AMD ROCm LLVM documentation (the metadata key definition, to confirm the AMD-side semantics) → the work-group processing mode chapter of the Intel oneAPI GPU Optimization Guide (to find the Xe-side counterpart). **Source ID: C7** |
| **G-50** | **how spill is determined and reported on Xe; the quantitative measure of spill's impact on Xe performance** | `.sgpr_spill_count` has **10** non-zero entries and `.vgpr_spill_count` **14** (272-entry scope); both are recommended to be **discarded** on the Xe side, but after discarding **the register pressure on the Xe side must be reassessed** | the IGC documentation; the "Spilling" chapter of the Intel oneAPI GPU Optimization Guide. **Source ID: §2.4(c)** |
| **G-51** | **the alignment granularity of SLM requests on Xe; the semantics of the value returned by `info::device::local_mem_size` (whether it includes reserved overhead)** | 64,640 B is only **896 B** from 64 KiB; if the Xe side has alignment / reserved overhead, **k1 will be affected first** | the Intel Arc B-series whitepaper; the SYCL 2020 specification `local_mem_size`; the error form reported by Intel DPC++ compilation diagnostics when SLM is exceeded. **Source ID: A4 (partial)** |

### 8.8 Summary Statistics

| Category | Entry count | IDs |
|---|---|---|
| roadmap determination premises | 4 | G-01 … G-04 |
| affecting all 34 kernels | 6 | G-05 … G-10 |
| by operator family | 9 | G-11 … G-19 |
| device ELF special symbols and structures | 4 | G-20 … G-23 |
| host side | 11 | G-24 … G-34 |
| weights and kernarg | 12 | G-35 … G-46 |
| classification thresholds and Xe-side values | 5 | G-47 … G-51 |
| **total** | **51** | — |
