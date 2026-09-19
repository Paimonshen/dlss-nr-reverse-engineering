# Open Gaps and Limits

This document concentrates on **the questions this project cannot answer**, and why each question cannot be answered.

The purpose of listing these is not self-limitation, but to let readers:
1. judge which conclusions can be used directly and which can only serve as a direction;
2. avoid repeating dead ends that have already been walked;
3. know what conditions must first be supplied in order to break through a given gap.

---

## 0. Three Classes of Limitation

The limitations this project encountered fall into three classes with entirely different natures:

| Class | Meaning | Condition for breaking through |
|---|---|---|
| **Capability boundary** | a judgement that is **permanently unobtainable** in the current environment (e.g. requires target hardware, requires a toolchain) | the missing **physical condition** (hardware, toolchain) |
| **Unresolved item** | **no judgement criterion yet exists** to decide it within the range of available material | a **new evidence source** is needed (upstream source, external documentation, runtime observation) |
| **External dependency** | the determination depends on **specifications or documentation outside the workspace** | consult external material in the specified direction |

For each class, this document gives "why" and "what is needed".

---

## 1. Capability Boundaries (three hard constraints)

### 1.1 No AMD hardware → the runtime observation path is unavailable

**Status**: the runtime observation path is **unavailable**, and is confirmed as a **permanent condition** (no AMD hardware is provided).

**Direct consequences**:

- the original cannot be run on AMD and its behavior observed;
- the original's output cannot be obtained (⇒ numerical-comparison milestones are **unattainable in the current environment**);
- weight tensors cannot be obtained through a runtime dump;
- it cannot be observed under what conditions a given kernel is called (block scheduling);
- it cannot be observed what value a given global is written with at runtime (the filling of `g_e4m3_lut`).

**Affected critical gap**: the "layer → kernel binding" of §2 is closed off directly because of this.

### 1.2 No AMDGPU disassembler → instruction-level criteria are unobtainable

**Status**: `llvm-objdump` gets **0** hits when searched for in the workspace; `capstone` 5.0.7 does not support AMDGPU (searching the module for AMD / GPU related properties gets **0** hits).

**Quantified consequence**:

> The `.text` of the 34 kernels totals **6,081,960 bytes** (the sum of the 8 device ELFs), and **the number of disassembled instructions = 0**.

**Affected questions**:

- the **specific semantics** of a given device function cannot be determined (e.g. what `swin_layer` actually does);
- it cannot be determined whether `g_e4m3_lut` has a write site outside `.rodata`;
- the actual usage of the `SwinLDS` / `BlobLayout` classes in the device code cannot be determined.

⇒ **Only "symbol level" and "byte pattern level" judgements can be made; "instruction level" judgements cannot.**

### 1.3 No Intel / SYCL compilation toolchain → compile-level criteria are unobtainable

**Status**: `Get-Command` on `icx` / `icpx` / `dpcpp` / `clang` / `clang++` / `cl` / `hipcc` / `g++` gets **0 hits each**.

**Direct consequences**:

- no `.sycl` / `.hip` source file in the workspace was compiled;
- **"whether the ported version compiles" is unverifiable in this environment**;
- **whether the in-workspace re-implementation project tree (including its SYCL attempt) was ever successfully compiled and run has no judgement criterion**: its `build/` contains **no `.sycl` compilation artifact whatsoever**.

### 1.4 The Joint Consequence of the Three Constraints

> **The verification ceiling for every conclusion of this project is "static byte level".**

For any judgement of the runtime, instruction, or compile class, this document set gives no conclusion at all.

---

## 2. Core Gap: the "layer → kernel binding" is unobtainable

This is the project's **most important and least closable gap**.

### 2.1 The Shape of the Problem

The network structure has 71 blocks (measured in the weight file as `block0` … `block70`, **with no missing numbers**), and 34 kernels. The shape of the problem is:

> **Which of the 34 kernels does a given layer of a given block call?**

**What is already determined**:

| Item | Status |
|---|---|
| **layer counts** | **determined**: weight measurement **1 layer × 47 (block 0–22, 39, 48–70) / 4 layers × 15 (23–29, 40–47) / 5 layers × 9 (30–38)** |
| **topological segmentation** | **determined**: `ENCODER_END = 22` / `BOTTLENECK_START = 23` / `BOTTLENECK_END = 47` / `DECODER_START = 48` |
| **the 34 kernel names set** | **determined**, and kernel name ↔ wrapper function ↔ handle table slot is **34/34 statically closed** |
| **"layer → kernel binding"** | **unobtainable** |

### 2.2 All Four Avenues Are Closed

#### Avenue ①: DLL static analysis —— **has reached its boundary**

All available static means have been exhausted; the **negative conclusions** obtained are as follows:

| # | Established boundary | Measured |
|---|---|---|
| 1 | signature comparison (`cmp r32,0x1A`) inside the dispatcher function body `[0x180012380, 0x180012D26)` | **0 hits** (the body contains only 4 `83 F8/F9/FA imm8`, with immediates `0x10/0x10/0x20/-0x27`, none of which belongs to a block signature; the nearest signature is at `0x180013117`, `0x3F1` away from the dispatcher end) |
| 2 | total instruction count under the scope "linear disassembly function by function over the 1167 `.pdata` function bodies" | **82,170** (a single linear disassembly of all `.text` gives only 76,661, stopping after the last instruction at `0x180049EBE` upon encountering non-code bytes) |
| 3 | immediates `70` / `71` / `72` within that set | **91** hits (`0x48` = 72, 85 times; `0x46` = 70, 4 times; `0x47` = 71, 2 times), **none of which is a block index comparison** (55 of them are `sub` / `add rsp,0x48` stack-adjustment forms, 36 are non-stack-adjustment forms) |
| 4 | the origin of "71 blocks" | **documentation transcription only**; there is no corresponding immediate comparison inside the DLL |
| 5 | location of the dispatch points | only inside the **4 renumbering functions**, and **all outside the dispatcher** |
| 6 | intersection of the dispatcher's 38 `call` targets with the 14 function entries containing `hipLaunchKernel` | **= 0** |
| 7 | storage of the renumbering results | written only to **BSS-type globals** (`0x180076394` / `0x180076398`, **no file initializer**) ⇒ statically there are only write sites, **no initial value table** |
| 8 | the form of the 3 read sites | the value is written into a **write-only, never-read** stack frame field and then handed to a **virtual call** (vtable filled at runtime) |
| 9 | the 34 wrapper entries (31 same-template instances + 3 auxiliary wrappers) | **no direct `E8` call** (invoked indirectly through the handle table) |
| 10 | the size of the signature enumeration | **6 occurrences** of the same signature (4 are inlined copies inside block renumbering; the other 2, idx 949 / 951, have **undetermined semantics**) |

#### Avenue ②: in-workspace source —— **it is a stub + non-isomorphic to the DLL**

**Stub**:

- the four key function bodies in `OptiScalerIntegration.cpp` (`EncodeInput` / `RunSwinBlock` / `RunProjectionBlock` / `DecodeOutput`) **are all `return true;`**;
- the two `Get*Features()` return `nullptr`;
- `NrBackend_Evaluate` and the function bodies of the host-side stages are likewise **all `return true;`**.

**Non-isomorphic**:

| # | Basis |
|---|---|
| 1 | **kernel basename collision 2/30**: that tree has 6 deduplicated basenames; the DLL's 34 kernels have **30** deduplicated basenames; **the intersection is only 2** (`k_swin_1h_32_fp8`, `k_swin_var`) ⇒ **28/30 DLL basenames do not exist in that tree** |
| 2 | **4 basenames present in that tree but absent from the DLL**: `blend_output` / `dlssnr_imgenc` / `mlp_projection` / `residual_add` |
| 3 | **the 34 kernel names get zero hits outside that tree** (0 hits each across the 2,996 non-tree source files of the whole workspace) |
| 4 | **no equivalent in the full Git history either**: 5,951 historical source file paths; path substring `engine/` **0**, `swin` **0**, `runtime_intel` **0** |
| 5 | **the depended-on SDK is not in the workspace**: the `hip/hip_runtime.h` file itself gets **0** hits; `rocm` directory **0**; `hipcc` **0** |

⇒ **that tree is a re-implementation project of the same network, not the source code of this DLL**; its scheduling constants reflect **that tree author's assumptions**, not the DLL's actual bindings.

**Moreover, that tree's scheduling rules have been refuted by the data**: the source rules predict "the bottleneck 23–47 uniformly 4 layers", while the weight measurement is a **mixed arrangement of 1 / 4 / 5 layers**, with **10 inconsistent blocks (30–39)**.

#### Avenue ③: the weight file —— **exhausted**

A **byte-by-byte exhaustive check** was performed over the 147,689,451-byte weight file: **140 patterns, covering the entire file including the payload region (100% of bytes), naive string matching (not regex, not approximate, not sampled)**.

Search range definition:

| Code | Byte range | Length |
|---|---|---|
| **H** | index region `[0x0000, 0x1629)` | 5,673 B |
| **D** | payload region `[0x1629, 0x8CD8FEB)` | 147,683,778 B |
| **W** | whole file | 147,689,451 B |

Results (all **0 hits**):

| Category | Pattern count | Result |
|---|---|---|
| `shape` / `dims` / `dim` class (including case variants, `rank`, `stride`) | 13 | **W all 0** |
| `dtype` / numeric-format class | — | **W all 0** |
| **operator type names** (`qkv` / `attn` / `conv` / `ffwd` / `swin` / `mlp` / `norm`, etc.) | **43** | **W all 0** |
| **`kernel` name set** (10 named basenames + **superset prefix `k_`** + `kernel` / `Kernel` / `KERNEL` / `__global__` / `__kernel` / `hipLaunchKernel`) | — | **W all 0** |
| **independent `block` index field** (10 field-name patterns) | 10 | **W all 0** |

**Triple proof at the structural level**:

| # | Proof | Evidence |
|---|---|---|
| **B1** | the container has **only 4 classes of fields** (`magic` / `count` / `indexEnd` / `entry[]`), and `entry[]` has only **3 sub-fields** (`name` / `offset` / `size`). The index region's **5,673 B are 100% byte-by-byte attributed to these 4 classes, unattributed bytes = 0** | byte-by-byte accounting |
| **B2** | **no `kernel` name field exists** | 0 hits in the above searches |
| **B3** | **no independent `block` index field exists**: 10 field-name patterns get 0 hits; and **there are no bytes to carry it** —— if a `uint32 blockIdx` existed, the index region would have to be ≥ 6,285 B, whereas **the measured value is exactly 5,673 B** | byte accounting + reductio |
| **B4** | **no operator type field exists**: 43 patterns get 0 hits across the whole file; the only operator-semantics carrier in the names is the suffix literal `layer` (152 entries) and `blend_scale` (1 entry), whose **granularity reaches only "which layer" and not "which kernel"** | exhaustive search |
| **B5** | **no hidden metadata inside the payload**: ASCII-printable share **1.0273 %**; ASCII strings of length ≥16 number only **6**, the longest being **21 B** (**shorter than the upper end 26 of the full length range whose shortest name length is 19**); the intersection of payload-region ASCII strings with the 153 names is **∅**; the autocorrelation over 9 strides shows **no periodic peak**; the 153 payloads **cover gaps 0** | exact counting over the whole payload region |

**Corroborating evidence (the source code's own self-disclosure)**: both in-tree parsers **must parse the name string** when they need the block number (`atoi(t.name.c_str() + 5)`) —— this is the **reductio** of "there is indeed no independent block index field in the container".

**Ruling out the "partial acquisition" possibility**:

| Band | Does it hold | Reason for exclusion |
|---|---|---|
| **can** | does not hold | would require a kernel name or mapping table inside the container; B1 has proven there are no bytes to carry it, and B2 has proven the kernel name field gets 0 hits |
| **partial** | **does not hold** | "partial acquisition" requires that at least a **partial binding** can be established. The measured `entry.name` **reaches only the granularity of `block<N>.layer<L>.layer`** (152 entries) + `block70.layer0.blend_scale` (1 entry), and **contains no kernel / operator identifier whatsoever**. B4 proves operator names get 0 hits across 43 patterns ⇒ **even "which class of operator this layer belongs to" is not in the container, so a partial binding cannot be established either** |
| **cannot** | **holds** | the five independent pieces of evidence B1–B5 all point to the same conclusion |

#### Avenue ④: runtime observation —— **permanently unavailable**

The reason is given in §1.1. **This avenue is not "temporarily unavailable"; the condition simply does not exist.**

### 2.3 Conclusion

> **The "layer → kernel binding" is unobtainable under the available conditions.**
>
> All four avenues (DLL static analysis, in-workspace source, weight file, runtime observation) are **closed**.

**Consequence**: this gap **directly blocks** stage S5 of the roadmap and its milestone M5-1.

**What breaking through requires** (any one of):

1. AMD hardware, with runtime recording at the 4 read sites + the **34 handle slots (table A 29 + table B 5)**, to obtain the `value → kernel` triples;
2. obtaining the **upstream pass source** of this DLL (including the block scheduling definitions);
3. obtaining the **block dimension definition** from the host side or outside `.hip_fat` (this enum's upper bound is undetermined within this DLL).

### 2.4 One Compatibility Problem That Must Be Noted

The input of the **block renumbering** contains `0x5A = 90`, and its output contains `0x57 = 87`, **both > 70**.

⇒ This is **incompatible** with the assumption that "the block index space is 0–70"; **this enum's upper bound is undetermined within this DLL** (known ≥ 90, and the renumbering result space ≥ 87).

This means that even once a binding exists, the **input / output enums** of the block layer must first be bounded, otherwise the domain of the dispatch table is undetermined.

---

## 3. Structural Unresolved Items

### 3.1 The Internal Layout of `VarParams` 168 B

**Status**: **unobtainable under the available conditions.**

**Kernels involved**: k29, k30, k31, k32, k33 (the 5 `k_swin_var`).

**What is already confirmed**:

| Item | Value |
|---|---|
| `by_value` parameter `size` | **168** |
| `by_value` parameter `offset` | **0** |
| `.kernarg_segment_size` | **424** |
| `.kernarg_segment_align` | **8** |
| parameter shape | 1 `by_value` (168 B) + 13 `hidden_*` |

**Why it is unobtainable**:

1. **`.args` declares only the total byte count of `by_value`, not field names or field boundaries** —— at this level the metadata is a "black-box length", not a struct definition;
2. **structs in the in-workspace source cannot serve as a basis**: the in-tree source gives 16 named fields (7 `half*` + `int B,H,W,C` + `int windowSize,numHeads,headDim` + `float scale` + `int shiftSize`); but **that struct comes to 92 B counting 64-bit pointers, while the DLL-side `by_value` = 168 B ⇒ the two are not the same layout**; and moreover **that tree is non-isomorphic to the DLL** (28/30 deduplicated basenames are absent from it);
3. **external material is not in the workspace** (upstream pass source, network definition).

**Consequence**: the kernarg packing of the 5 `k_swin_var` kernels **cannot be reconstructed field by field**; consequently the parameter-packing requirements on the Xe side also cannot be determined (external checklist item G-17).

**Same-family unresolved item**: the `SwinParams` 40 B of §3.2.

### 3.2 The Internal Composition of `SwinParams` 40 B

**Status**: **unobtainable under the available conditions.**

**Kernels involved**: k0 (`k_swin_1h_32_fp8`).

**What is already confirmed**:

| Item | Value |
|---|---|
| `by_value` parameter `size` | **40** |
| `by_value` parameter `offset` | **0** |
| `.kernarg_segment_size` | **296** |
| `.kernarg_segment_align` | **8** |
| parameter shape | **1 `by_value` (40 B) + 13 `hidden_*`, and no `global_buffer` parameter whatsoever** |

**Why it is unobtainable**:

1. **which fields fit in the 40 B, and how many bytes each: unobtainable** —— the criteria boundary is the same as §3.1 (`.args` declares only the total byte count);
2. **the cause of the 52 B difference from the source `SwinParams` (92 B counting 64-bit pointers): unobtainable**;
3. external material (upstream pass source, network definition) is not in the workspace.

**One retraction that needs stating**: the claim that "the 40 B of `SwinParams` is already explained (the pointer goes through `global_buffer`)" **is wrong** —— among k0's 14 `.args` there is **no `global_buffer` parameter at all** (the whole library has only 24 `global_buffer` parameters, all belonging to the three exception kernels k26 / k27 / k28). That claim has been retracted.

### 3.3 Field Attribution of the 190 B Weight Tail and the 16 B Hole

**Status**: **not resolved.**

**What is already confirmed**:

- **the 16 B hole**: located in the hidden region `+0x18`–`+0x28` (between the end of `hidden_remainder_z` and the start of `hidden_global_offset_x`), **constant across 31 kernels × 8 targets**, with no corresponding `.args` entry;
- **the 190 B tail**: the difference `+190` occurs **248** times (31 kernels × 8 targets), and the difference `+0` occurs **24** times (3 kernels × 8 targets); neither has a **corresponding `.args` entry**.

**Why it is unresolved**:

- the metadata contains no field names or boundaries;
- instruction-level disassembly (E-2 unavailable) or the upstream source is required.

**Also unresolved along the way**: `190 mod 8 = 6`, and **its relation to `.kernarg_segment_align = 8` is unresolved**.

**Consequence**: it cannot be determined whether these two segments need alignment on the Xe side (external checklist items G-41 / K6).

### 3.4 Runtime Filling Mechanism of the `.data` 17-Item Pointer Table

**Status**: **the capability exists; the actual filling path is unproven.**

**What is already proven**:

- the 17 slots are located at `0x180076440..0x1800764C0`, **outside the raw coverage of `.data`** (the `.data` file image only extends to VA `0x180076200`);
- **no file bytes**;
- **no `.reloc` coverage** (`DIR64` count 0);
- the module **possesses the runtime resolution capability** of `GetProcAddress` (direct IAT references **25** sites), `LoadLibraryA`, `LoadLibraryExW`, `FreeLibrary` (**7** sites), `GetModuleHandleA/W` (**9** sites).

**What is unproven**: which **call site, using which API**, actually fills these 17 slots.

**Why it is unproven**: runtime observation is required (E-1 unavailable); statically one can only prove "the capability exists", not "it was actually used".

### 3.5 The Semantics of `swin_layer` and the Cause of Its Occurrence Range

**Status**: **undetermined.**

**What is already confirmed**:

| Item | Value |
|---|---|
| symbol name | `_Z10swin_layerR7SwinLDSPKhRK10BlobLayouti` (**non-template**; `7` is the name length prefix) |
| occurrence range | **`#2` gfx11-generic / `#3` gfx1100 / `#4` gfx1101 / `#5` gfx1102**; `#1` / `#6` / `#7` / `#8` get **0** hits |
| size | `st_size` = 135,092 (`#2`, `#5`) / 135,096 (`#3`, `#4`); VA is `0xBD00` for all |
| is it among the 34 kernel names | **no** |
| does it have a `.kd` descriptor | **no** |
| `.symtab` entry count | `#2`–`#5` = 348; the rest = 347; **the symbol-set difference between `#1` and `#2` is exactly this one symbol**; the union of symbols across the 8 bundles = 348, the intersection = 347 |
| counterpart in the in-workspace source | `SwinLDS` / `BlobLayout` get **0 hits** across that project tree ⇒ **no source to refer to** |

**Why it is undetermined**:

1. its **call relationship** with the 34 kernels is unproven (no AMDGPU disassembler, E-2);
2. why its occurrence range is only the 4 targets (rather than 8) **has an unresolved cause**.

**The boundary of what it can support (must be strictly observed)**: the `swin_layer` symbol **can support only** the statement "**a device function whose first formal parameter is the `SwinLDS` class exists inside this device ELF**". It **cannot** support:

- "the LDS usage of that function";
- "the call relationship between that function and the 34 kernels";
- "how that function should be rewritten on the Xe side".

⇒ Consequently the **first-level criterion for LDS re-partitioning derived from it has not landed** (external checklist items G-20 / G-21).

### 3.6 The Semantics of `g_e4m3_lut` (512 B, all zero)

**Status**: **undetermined.**

**What is already confirmed**:

| Item | Value |
|---|---|
| location and size | each of the 8 device ELFs has a **512 B** `g_e4m3_lut` object inside `.rodata` |
| bytes | **all 8 targets have 512/512 bytes equal to `0x00`** |
| `.kd` references | **no field among the 272 descriptors equals that symbol's VA** |
| reference sites across the whole DLL | **2 8-byte encodings per bundle** (1 inside `.rodata` + 1 inside `.text`) |
| meaning of the name | contains `e4m3` (a form of FP8) and `lut` (look-up table) |

**Why it is undetermined**:

- deciding "whether it is an all-zero placeholder or filled at runtime" requires **write-site determination**, which requires instruction-level disassembly (E-2 unavailable);
- or it requires a **runtime memory-image comparison** (E-1 unavailable).

⇒ both avenues are unavailable at the same time, so this question is **undecidable in this environment** (external checklist item G-22).

### 3.7 The Operator Semantics of `k_expand` / `k_contract`

**Status**: **unresolved.**

**The shape of the problem**: in a tensor-operator context the two names (Expand / Contract) **can point to several semantics** (broadcast / tensor contraction / index expansion).

**The only available criteria**: the names and the `B` sizes (24 B / 48 B respectively).

**The criteria are insufficient to choose among several semantics**; and the in-workspace project tree **has no corresponding implementation either** (both names get **0 hits** in that tree).

⇒ the operator semantics must first be obtained before the corresponding primitive on the Xe side can be determined (external checklist item G-19).

### 3.8 The Cause of the Two Unique Extremes

**Status**: **unresolved.**

| Kernel | `private_segment_fixed_size` | Occurrence range |
|---|---|---|
| k7 `k_conv_res211Conv2Params` | **404** | `#8 gfx9-generic` only |
| k25 `k_reproject12ReprojParams` | **84** | `#8 gfx9-generic` only |

Each occurs **exactly once** among the 272 entries, and both are 0 in `#1`–`#7`.

**Why it is unresolved**: there is no criterion in this environment to explain the difference (it would require the `gfx9` versus `gfx10+` scratch-allocation differences from the AMD GPU programming manual, or runtime observation).

**Consequence**: "taking parameters from some single target" will **systematically miss** these two extremes (external checklist item G-13).

### 3.9 The Cause of the `k_ffwd` Series' `group` Taking 0 and 24,576 Across Targets

**Status**: **unresolved.**

The `group_segment_fixed_size` of k3 / k6 / k17 is **0** in `#1` / `#8` and **24,576** in `#2`–`#7`.

**Key limitation**: `.kd` and the msgpack metadata are **272/272 consistent** ⇒ this difference is a **real difference, not a parsing error**.

**Why it is unresolved**: there is no criterion in this environment to explain the cause, nor any criterion to decide which band the Xe side should take (external checklist item G-16).

### 3.10 The Relationship Between the Packed Region Inside `.hip_fat` and the External Weight File

**Status**: **unproven.**

**Already confirmed**: the 147 MB-scale entity is an **external file** (147,689,451 B / `DLSSNRW1` / SHA256 `6BF8DC93…`), accounted separately from the packed region inside the DLL (`.hip_fat` 6,649,000 B).

**Unproven**: "the correspondence between that external file and the `.hip_fat` inside the DLL".

### 3.11 Unequal-Length Metadata Across the 8 Targets

**Status**: **unresolved (generation rule).**

`descsz` deduplicated across bundles gives **6 distinct values**:

| Target | `descsz` |
|---|---|
| `#1` | `0x8B72` |
| `#2` | `0x8B84` |
| `#3` | `0x8B7C` |
| `#4` | `0x8B7C` |
| `#5` | `0x8B7D` |
| `#6` | `0x8B78` |
| `#7` | `0x8B78` |
| `#8` | `0x87DA` |

**max − min = 938 (`0x3AA`)**.

**One correction**: the "difference of 1,410 bytes" recorded in earlier material was an **arithmetic error**.

**Consequence (a meaningful conclusion)**: **one must not assume the metadata of the 8 targets is byte-identical**; cross-target consistency must be established item by item.

---

## 4. The Enum Semantics of the `71 block`

### 4.1 The Shape of the Problem

The number "71" appears in two sources:

| Source | Form |
|---|---|
| **weight file** | entry names cover `block0` … `block70`, **71 blocks in total, no missing numbers** —— this is a **measurement** |
| **in-workspace source** | `constexpr uint32_t NUM_BLOCKS = 71;` —— this is a **declaration** |

But inside the **DLL's static bytes**, "71" gives:

| Search | Range | Result |
|---|---|---|
| immediates `70` / `71` / `72` | the **82,170** instructions under the "linear disassembly function by function over the 1167 `.pdata` function bodies" scope | **91** hits (`0x48` = 72, 85 times; `0x46` = 70, 4 times; `0x47` = 71, 2 times), **none of which is a block index comparison** |
| this signature comparison (`cmp r32,0x1A`) | the dispatcher function body | **0 hits** |

⇒ **"71 blocks" exists inside the DLL only as documentation transcription, with no corresponding immediate comparison.**

### 4.2 Block Renumbering (the settled part)

Inside `.text` there are **4** inlined copies of the same-signature (`cmp r32,0x1A`) **renumbering** (the other 2, idx 949 / 951, have undetermined semantics):

| Input | Output |
|---|---|
| `9` | `0x0A` (10) |
| `0x17` (23) | `0x18` (24) |
| `0x1B` (27) | `0x1C` (28) |
| `0x5A` (90) | `0x57` (87) |
| all other values (**including `0x1A` = 26**) | **keep their original value** |

The branch order differs pairwise among the four sites (sites 1 / 2 test `0x5A` before `0x1B`; sites 3 / 4 test `0x1B` before `0x5A`), but the branch semantics are entirely identical; these are **the same function inlined four times**.

⇒ Therefore the earlier statement "the only determined block values are 5: 9, 23, 26, 27, 90" must be rewritten semantically as:

> **`26` is merely the comparison bound of the `jg` and is not renumbered; the values actually specially handled and renumbered are the four: 9 / 23 / 27 / 90.**

### 4.3 The Undetermined Parts

| Item | Status |
|---|---|
| **the occasion of the 4 renumberings** (under what conditions they are called) | **undetermined** —— requires runtime observation |
| **the purpose of the renumbering results** | **undetermined** —— the results are written only to BSS-type globals (no file initializer); the 3 read sites write the value into **write-only, never-read** stack frame fields and hand it to a **virtual call** (vtable filled at runtime) |
| **the semantics of the other 2 occurrences of the same signature (idx 949 / 951)** | **undetermined**. Coordinates: `0x180048A44` (idx 949, raw bytes `83 F9 1A 74`), `0x180048ECC` (idx 951, raw bytes `83 FA 1A 0F`). This project does **not claim** they are renumbering copies |
| **the upper bound of the block enum** | **undetermined** —— the input contains `0x5A` = 90 and the output contains `0x57` = 87, both > 70 |

### 4.4 Compatibility Ruling

| Item | Content |
|---|---|
| conflict | the input `0x5A` = 90 and the output `0x57` = 87 are **both > 70**, which is **incompatible** with "the block index space is 0–70" |
| status | **this enum's upper bound is undetermined**; this project **gives no conclusion** |
| impact | the **input / output enums** of the block layer must first be bounded when porting, otherwise the domain of the dispatch table is undetermined |

---

## 5. Questions That Need External Documentation

The following questions are **not "unsolvable", but "require knowledge from outside the workspace in order to be decided"**. This project gives no conclusion, only the directions to look into. The complete list is in `05-Intel-Feasibility-Assessment.md` §8; this section gives a **classified index** and **priorities**.

### 5.1 Highest Priority (determines the shape of the roadmap)

| ID | Item to look up | Scope of impact |
|---|---|---|
| **G-01** | whether XMX provides directly callable primitives for matrix multiply / convolution, and the coverage of its precision modes (FP8 / FP16 / BF16 / INT8) | **25 kernels** |
| **G-02** | whether a primitive that can substitute for split-K convolution semantics exists; whether the floating-point accumulation order of split-K reduction is constrained by a specification | 4 kernels |
| **G-03** | whether the window / shift primitives needed by the Swin transform are provided; the feasible range of the window parameter (32/64/128/256) on the Xe side | 8 kernels |
| **G-04** | the feasibility and performance boundary of the generic SPIR-V path (non-XMX) for this workload | **all 34** |

> **These four are the determination premises for whether stage S4 "takes the XMX path" or "takes the generic SPIR-V path".**

### 5.2 Affecting All 34 Kernels

| ID | Item to look up |
|---|---|
| **G-05** | Xe's set of sub-group (SIMD) width values and the work-item-to-lane mapping rule (⇒ `.wavefront_size` 32/64 **must not be carried over**) |
| **G-06** | Xe's per-Xe-core SLM limit; whether "SLM limit per work-group" and "SLM limit per Xe-core" are two different constraints |
| **G-07** | Xe's register file (GRF) organization, and whether a conversion rule from AMD `vgpr_count` / `sgpr_count` to Xe register occupancy exists |
| **G-08** | the correspondence between Xe's barrier / fence semantics and AMD `s_barrier` / `s_waitcnt` |
| **G-09** | the corresponding ABI fields (if any) on Xe for `group_segment_fixed_size` / `private_segment_fixed_size`; the complete value set of execution modes and capabilities in SPIR-V |
| **G-10** | the relationship between the `OpenCL C` language attribute and the HIP compilation chain, and its corresponding expression on the SPIR-V side |

### 5.3 Platform Capacity and Numerics (Xe side)

| ID | Item to look up |
|---|---|
| **G-47** | whether this table's self-declared thresholds (4096 / 32768 / 64) hold on Xe |
| **G-48** | the maximum number of work-items per work-group on Xe, and its joint constraint relationship with the SLM / register budget |
| **G-49** | the counterpart of `.workgroup_processor_mode` on the Xe side |
| **G-50** | how spill is determined and reported on Xe; the quantitative measure of spill's performance impact |
| **G-51** | the alignment granularity of SLM requests on Xe; the semantics of the value returned by `info::device::local_mem_size` (whether it includes reserved overhead) |
| **G-12** | Xe's private-segment (per-thread private memory / stack) limit and alignment rules |
| **G-40** | the alignment requirements of the kernel parameter (kernarg) segment on Xe; additional alignment for pointer parameters; the packing rules for 2-byte parameters |
| **G-42** | the Xe compiler's alignment / packing behavior for kernel parameter structs |

> **Of these, G-51 and G-06 are directly related to a known high-risk point**: k1's 64,640 B is only **896 B** below the 64 KiB limit, and any alignment / reserved overhead will eat into it first.

### 5.4 Operator-Family Related

| ID | Item to look up | Affected kernels |
|---|---|---|
| **G-11** | the semantics and precision of Xe's cross-work-item reduction primitives | k5, k8, k12, k16, k22 |
| **G-13** | the cause of the two unique extremes (404 / 84, both `#8` only) and their corresponding handling on the Xe side | k7, k25 |
| **G-14** | the semantics and available scope of atomic operations and memory ordering on Xe | k26, k27, k28 |
| **G-15** | the data-movement primitives between host and device on Xe | k20, k23, k24 |
| **G-16** | the cause of the `k_ffwd` series' `group` taking 0 and 24,576 across targets | k3, k6, k17 |
| **G-17** | the internal field layout of `VarParams` 168 B and its parameter-packing requirements on the Xe side | k29–k33 |
| **G-18** | how "view / stride" class parameters are expressed inside a kernel on Xe and what they cost | k17, k18, k21, k25 |
| **G-19** | the operator semantics of `k_expand` / `k_contract` | k9, k13, k14 |

### 5.5 device ELF Special Symbols

| ID | Item to look up |
|---|---|
| **G-20** | whether `swin_layer(SwinLDS&, …)` is called by one of the 34 kernels |
| **G-21** | the semantics of `swin_layer` and of `SwinLDS` / `BlobLayout`; why it exists only in `#2`–`#5` |
| **G-22** | the semantics of `g_e4m3_lut` (512 B, all zero across the 8 targets) |
| **G-23** | whether the project tree's `joint_matrix` GEMM can be reused; whether its scalar loops will be auto-vectorized to XMX by the compiler |

### 5.6 Host Side (11 items)

| ID | Item to look up |
|---|---|
| **G-24** | the expression and lifetime of the "kernel launch configuration" in SYCL / Level Zero (**102 call sites**, the most in the whole library) |
| **G-25** | the Level Zero module format and the SPIR-V module creation flow |
| **G-26** | the Level Zero kernel handle acquisition and launch flow (**94 call sites**) |
| **G-27** | Level Zero access to device globals (symbols) |
| **G-28** | Level Zero's external-memory / D3D12 interoperability extensions |
| **G-29** | the counterparts of the device / driver / event / version query APIs (9 items) |
| **G-30** | the counterparts of USM / memory allocation and copy (6 items, **84 call sites**) |
| **G-31** | the parameter struct layout of `hipGetDevicePropertiesR0600` (**requires per-call-site argument changes**) |
| **G-32** | the difference in error-code models (HIP has a "last error" global state; Level Zero returns per call) |
| **G-33** | the compatibility of `D3DCompile` / `D3D12SerializeRootSignature` artifacts on Xe (**7 call sites**) |
| **G-34** | whether a reusable path exists for a HIP → SPIR-V porting toolchain (determines how the 29 items are implemented) |

### 5.7 Weights and kernarg

| ID | Item to look up |
|---|---|
| **G-35** | the **official field names** of the two uint32 at `0x08` / `0x0C` (semantics proven, names unproven) |
| **G-36** | the **final ruling** on the element type FP16 vs BF16 (currently only a sampling tendency, no full statistical test performed) |
| **G-37** | the **shape** and tensor semantics of each `layer` (the container has no shape / dtype field) —— **the common prerequisite of all conversion paths** |
| **G-38** | the correspondence between `layer0`–`layer4` and the Swin operators |
| **G-39** | the semantics of `blend_scale` (= 0.739746) |
| **G-41** | the field attribution of the 190 B tail and the 16 B hole |
| **G-43** | the 2-byte element alignment requirements of SYCL `buffer` / USM; the tile sizes and element type combinations supported by `joint_matrix` |
| **G-44** | the three items of the OpenVINO path (manual graph-building API, IR version / FP16, GPU plugin XMX utilization / FP16 preservation / dynamic shape) |
| **G-45** | the two items of the ONNX path (FP16 initializer expression; XMX support and operator coverage of the three backends) |
| **G-46** | chipStar (HIP on SPIR-V / Level Zero) support and limitations (including SLM / `__syncthreads` mapping) |

### 5.8 Statistics

| Category | Entry count |
|---|---|
| roadmap determination premises | 4 |
| affecting all 34 kernels | 6 |
| by operator family | 9 |
| device ELF special symbols | 4 |
| host side | 11 |
| weights and kernarg | 12 |
| classification thresholds and Xe-side numerics | 5 |
| **total** | **51** |

---

## 6. Explanation of the Strength of the Conclusions

### 6.1 Three Limitations That Must Accompany Any Citation

1. **The cross-target consistency conclusion covers only the parameter surface**: `.kernarg_segment_size`, the `.args` element count, and the per-parameter `.offset` / `.size` / `.value_kind` are consistent across the 8 targets (238/238 judgement cells, `args` byte SHA256 272/272); **resource-class fields have separate differences** (8 of the 16 field entities are inconsistent).

2. **Operator semantics can only reach "name-based inference"**: four refutations hold simultaneously (the source path is ruled out + the comparison module does not hold + no hardware + 0 hits for operator names inside the DLL). ⇒ This conclusion **does not constitute a verification conclusion about operator semantics**.

3. **"An implementation already exists" does not constitute proof of capability**: the project tree covers **6/34** kernels, its only `joint_matrix` usage is concentrated in **1 template with 0 instantiations**, and the remaining implementation bodies are **scalar loops**; moreover no judgement criterion has been obtained for its shared-memory usage and register pressure.

### 6.2 Seven Places Where Mixing Scopes Produces Wrong Conclusions

| # | Scope A | Scope B | Consequence |
|---|---|---|---|
| 1 | **272-entry scope** | **34-kernel scope** | `.max_flat_workgroup_size` = 256 × 208 / 1024 × 64 vs 256 × 26 / 1024 × 8 |
| 2 | **scope 1 (field × kernel pair) 163** | **scope 2 (cell count compared with `#1`) 605** | estimating as "163 × 7" gives 1141 and as "163 × 28" gives 4564; **both are wrong** |
| 3 | **scope 1** | **scope 3 (8 targets compared pairwise) 2183** | as above |
| 4 | **value + occurrence count** | **single-point attribution** | 64,640 occurs 8 times, 58,368 / 28,928 occur 6 times each; **single-point attribution is not allowed** |
| 5 | **number of non-zero spill entries** (10 / 14) | **number of distinct values** (8 each, including 0) | treating "8" as the entry count is wrong |
| 6 | **narrow scope (97)** | **broad scope (110)** | the RIP reference counts of the table A/B pointer regions; both numbers are correct, and which one is used must be stated |
| 7 | **`layer` entry count** | **total entry count** | `block70` is "1 layer" / "2 entries" under the two scopes respectively |

### 6.3 Closed Items (**must not be listed as unresolved again**)

The following 16 items are closed; downstream **should not duplicate the work**:

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
| 13 | **the weight header ruling** (`DLSSNRW1` wins, both 4-byte constants are wrong) |
| 14 | **the layer-count histogram** (1×47 / 4×15 / 5×9) |
| 15 | **the three `.kd` ↔ msgpack items 272/272 consistent**; `entry == code symbol VA − .kd symbol VA` **272/272, 0 counterexamples** |
| 16 | **194 import entries / 29 HIP / `E8` = 349 / direct IAT references = 0** |

### 6.4 One Capability-Boundary Registration

> **Purpose of the registration**: to prevent "no undeclared changes were found" from being misread as "it has been verified that there are no undeclared changes".

The **first-version comparison of a certain review report is not executable in this environment**: an independent check confirmed that **the first-version entity gets 0 hits on disk** (searching by `73,194 B` gives **0 files**; searching by the hash `3A03DE7A` **hits only that review report itself**, because it cites that constant string —— **no file's actual hash equals `3A03DE7A…`**; searching by file name finds **only** the one current version, with **no `.bak` / old copy / sibling backup**).

⇒ When citing that review's "**no undeclared changes**" conclusion, its basis is an **internal self-consistency check** (revision-record numbers are consecutive, anchors exist, self-reported counts collide consistently with measurements), and it is **not verified by a first-version comparison**. Wherever such a statement appears, this limitation **must** be given alongside it, and it **must not** be upgraded to "verified".

---

## 7. Gap Summary Table

| ID | Gap | Class | Status | Condition for breaking through |
|---|---|---|---|---|
| **U-1** | per-block → kernel dispatch | capability boundary | **unobtainable** (all four avenues closed) | AMD hardware / upstream pass source / block dimension definition |
| **U-2** | block enum upper bound | unresolved | **undetermined** (known ≥ 90) | upstream definition / runtime observation |
| **U-3** | semantics of idx 949 / 951 | unresolved | **undetermined** | instruction-level disassembly |
| **U-4** | internal layout of `VarParams` 168 B | unresolved | **unobtainable** | upstream source / runtime observation |
| **U-5** | attribution of the 190 B tail and the 16 B hole | unresolved | **not resolved** | upstream source / runtime observation |
| **U-6** | runtime filling mechanism of the 17-item pointer table | capability boundary | **capability exists, path unproven** | runtime observation |
| **U-7** | semantics of `swin_layer` and the cause of its range | unresolved | **undetermined** | instruction-level disassembly / upstream source |
| **U-8** | semantics of the all-zero `g_e4m3_lut` | capability boundary | **undecidable** | instruction-level disassembly or runtime image comparison |
| **U-9** | whether the project tree's XMX code was ever compiled and run | capability boundary | **no criterion** | Intel toolchain |
| **U-10** | operator semantics of `k_expand` / `k_contract` | unresolved | **unresolved** | upstream network definition / runtime observation |
| **U-11** | relationship between the `.hip_fat` packed region and the external weights | unresolved | **unproven** | upstream packaging flow |
| **U-12** | two diagnostic-class pending items | external dependency | **statically undecidable** | files outside the workspace |
| **U-13** | `descsz` unequal across bundles (938) | unresolved | **rule unresolved** | upstream packer behavior |
| **U-14** | `k_flag_set` kernarg = 12 (mod 8 = 4) | identified | **must be handled separately** | platform alignment specification (G-40) |
| **U-15** | the caller set of `swin_layer` | capability boundary | **has not landed** | instruction-level disassembly |
| **U-16** | **the "layer → kernel binding"** | capability boundary | **unobtainable** | same as U-1 |
| **U-17** | internal composition of `SwinParams` 40 B | unresolved | **unobtainable** | upstream source |
| **U-18** | handling of the conflict between source rules and weight measurement | ruled | **ruled** (the data file wins) | — |

---

## 8. Three Pieces of Advice for Downstream Readers

1. **Whenever you cite a number, check the scope first**. The seven scope mixes listed in §6.2 produce wrong conclusions; this document set gives an explicit label everywhere a scope label is needed, and you should carry them along.

2. **Whenever you cite an item marked "needs external documentation", do not write it as "the conditions are already in place"**. In its roadmap stage division this project has already listed the **prerequisite unclosed items** of each stage explicitly; stage S0 exists precisely to close those prerequisites.

3. **For any judgement of the runtime, instruction, or compile class, this project gives no conclusion at all**. This does not mean such judgements are unimportant, but that **they require conditions this project does not have**. If the reader has those conditions (AMD hardware, an AMDGPU disassembler, an Intel toolchain), the **coordinates, counts, identities and search patterns** given in this document set can be used directly for recomputation and progress.
