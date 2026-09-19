# Analysis Methodology

Under the triple constraint of **no AMD hardware, no AMDGPU disassembler, no Intel toolchain** (see `01-Project-Background.md` §2.2), all conclusions in this project rest on **static byte analysis**. This determines that the core proposition of the methodology is not "which tool to use", but:

> **Given that only bytes can be read, how do we make a conclusion as hard to get wrong as possible.**

This chapter presents a reproducible method together with the discipline that accompanies it.

---

## 1. General Principles

### 1.1 Bytes Are the Final Criterion

No documentary statement, no source-code comment, no existing summary is a basis for a conclusion. The only acceptable bases are:

1. the **raw bytes** of the target file (giving the triple coordinate file / VA / RVA, together with the raw byte string);
2. **PE / ELF structure fields** (obtained by parsing the bytes according to the specification);
3. **recomputable arithmetic** (counts, identities, frequency distributions).

Between mutually conflicting statements, the bytes always adjudicate.

### 1.2 Coordinates Must Be Given to the Point of Traceability

Every key conclusion gives a triple coordinate, so that the reader can recompute it independently:

| Coordinate | Meaning | Conversion |
|---|---|---|
| **file** | File offset | Converted via each section's `PointerToRawData` and the VA |
| **RVA** | Relative virtual address | `RVA = VA − 0x180000000` |
| **VA** | Virtual address | Obtained by adding the RVA to the ImageBase |

The conversion relations used in this section (all verified by measurement):

- `.text`: `file = VA − 0x180001000 + 0x400`
- `.rdata`: `file = VA − 0x180056000 + 0x55200`
- `.hip_fat`: `file = VA − 0x18007F000 + 0x78200`

Check points: VA `0x180012380` → file `0x11780`; VA `0x180055A70` → file `0x54E70`.

### 1.3 Falsification Is as Important as Confirmation

What this project records is not only "what was found", but also **"within what range the search was run and how many hits it gave"**. Every "X does not exist" conclusion must give three elements:

> **range + match pattern + hit count**

If any of the three elements is missing, the conclusion is not reviewable. A typical example is "searching the whole file for `softmax` / `silu` / `gelu` / `layernorm` / `matmul` / `gemm` / `wmma` / `mfma` / `dpas` / `xmx` / `subgroup` / `reduce`, each giving 0 hits".

---

## 2. PE Structure Parsing

### 2.1 Parsing Approach

Rather than depending on an external PE library, the `DataDirectory` entries are parsed by hand according to the PE specification. Reason: the fields this project needs to parse (whether an export forwarder exists, import descriptors one by one, the `.reloc` block structure, the `LoadConfig` directory) are often abstracted away by high-level APIs in third-party libraries, and yet they are exactly the criteria for the conclusions.

### 2.2 Parsing Items

| Item | Location | Purpose |
|---|---|---|
| DOS / NT headers | `0x00` / `0x80` | Locate the PE32+ header and the OptionalHeader |
| `DllCharacteristics` | `OptionalHeader + 0x46` (file `0xD6`) | Determine whether `DYNAMIC_BASE` / `HIGH_ENTROPY_VA` / `NX_COMPAT` / `GUARD_CF` are set |
| Section table | `IMAGE_FILE_HEADER.NumberOfSections` | 12 sections, field by field (RVA / VirtualSize / PointerToRawData / SizeOfRawData) |
| `DataDirectory[0]` export | RVA given by the directory | `NumberOfFunctions` / `NumberOfNames` / `Base`, AddressOfFunctions, Forwarder fields |
| `DataDirectory[1]` import | RVA `0x6B3F4` / Size `0xDC` | Per descriptor, decode the ILT / IAT and read the name and hint |
| `DataDirectory[5]` relocation | RVA `0x6DD000` / Size `0x1090` | Per block, decode the entries, type distribution, and coverage statistics per section |
| `LoadConfig` | Reached from `DataDirectory[10]` | `GuardCFCheckFunctionPointer` / `GuardCFFunctionTable` / `GuardCFFunctionCount` |
| TLS directory | `DataDirectory[9]` | `AddressOfCallbacks` |

### 2.3 Key Discipline: Distinguish "Valid Endpoint" from "Upper Bound of the Memory Range"

The most error-prone point in this section's method is treating "the upper bound of the memory range of some region" as "the end of the valid entries of that structure".

A concrete example: the two function pointer tables were recorded in early material as `table A = 0x180056170–0x1800562C0`, `table B = 0x180058A48–0x180058B90`. These two endpoints are **memory ranges** (all bytes within the interval), **not pointer-entry ranges**. Under an 8-byte stride, the slots that actually carry function pointers are:

- **table A = items 0–40** (`0x180056170`–`0x1800562B8`), of which items 0–25 / 30–32 are function pointers, items 26 / 33 / 41 are NULL, items 27–29 are the sentinel region, and items 34–40 are auxiliary data;
- **table B = items 0–4** (`0x180058A48`–`0x180058A68`), followed by negative-value sentinels.

**Lesson**: interval endpoints must be determined independently; one must not carry over a previously assumed boundary. This discipline directly produced a numerical difference in one recomputation — the same search using the **narrow caliber** (the table A slots 0–25 window ∪ the table B slots 0–4 window) gave **97** locations, while using the **wide caliber** (the full table A window ∪ the table B window) gave **110**; the difference of 13 came entirely from legitimate references that the narrow caliber had truncated. Both numbers are correct, but one must state which caliber was taken.

---

## 3. `__CLANG_OFFLOAD_BUNDLE__` Unpacking

### 3.1 Container Shape

The `.hip_fat` section (VA `0x18007F000` / RVA `0x7F000` / RAW `0x78200`) begins with the magic `__CLANG_OFFLOAD_BUNDLE__` (**unique in the whole file**).

### 3.2 Header Parsing

Parsed in the following order:

```
align padding to an 8-byte boundary
uint64  numBundles
repeated numBundles times:
    uint64  tripleSize
    char    triple[tripleSize]
    uint64  offset          ← offset relative to the "start of the data region"
    uint64  size
```

The raw 8 bytes of `numBundles` are `09 00 00 00 00 00 00 00` = 9.

### 3.3 Parsing Results and Boundary Verification

Of the 9 entries, 1 is the host placeholder (**size = 0**) and 8 are device bundles. Boundary verification items:

| Check | Result |
|---|---|
| Measured character count of the 9 triple strings vs. the declared `tripleSize` | **9/9 consistent** |
| Whether the triple strings contain a NUL terminator | They do not |
| Position of the last byte of the last triple | section start + `0x229` |
| The 8-byte-aligned upper bound | section start + `0x230` |
| section start + `0x230` to section start + `0x1000` | **3,536 bytes of all-zero padding** |
| The true start of the data region | section start + `0x1000` (file `0x79200` / VA `0x180080000`) |

### 3.4 The Three Consequences of the `#0` host Placeholder

1. **Do not run ELF parsing on an empty range** — parsing the empty range `[0x79200, 0x79200)` would read the bytes of `#1` and produce a spurious conclusion;
2. The actual number of device code objects in `.hip_fat` is **8** (not 9);
3. **The host-side code is not inside this DLL** — that bundle carries no host object file.

### 3.5 The `.hip_fat` Byte Accounting Identity

Used to cross-check whether the parsing is correct:

```
0x1000 (header and padding region)
+ Σ(8 real sizes) = 0x6514F0
+ Σ(7 gaps)       = 0x4FB8
= 0x6574A8  (= section VirtualSize)
```

The 8 sizes item by item:

```
0x89728 + 0x11E0A0 + 0x11C068 + 0x11C068
+ 0x11E0A0 + 0x67B88 + 0x67B88 + 0x844A8  = 0x6514F0
```

The difference `0x5FB8` = gaps `0x4FB8` + header region `0x1000`. The premise for this equation to hold is that `#0` counts as 0 bytes.

---

## 4. device ELF Extraction and Parsing

### 4.1 Location

The bytes of each device bundle at `offset` are a complete ELF file, with the interval `[data region start + offset, data region start + offset + size)`.

### 4.2 Parsing Items

| Item | Purpose |
|---|---|
| `e_ident` | Verify `EI_OSABI` (`0x40` = ELFOSABI_AMDGPU_HSA) and `EI_ABIVERSION` (`4`) |
| `e_machine` | Verify `0xE0` (224 = EM_AMDGPU) |
| Program headers / section table | Locate `.text` / `.rodata` / `.note` / `.symtab` / `.strtab` / `.dynsym` |
| Section table closure check | `e_shoff + e_shnum × e_shentsize == size` |

Measured: for the 8 ELFs, `e_type = 0x3`, `e_machine = 0xE0`, `e_ehsize = 64`, `e_phentsize = 56`, `e_phnum = 9`, `e_shentsize = 64`, `e_shnum = 16`, `e_shstrndx = 14`, **8/8 identical**; `e_shoff + e_shnum × e_shentsize == size` differs by 0; `e_machine = 0xE0` gives **8/8 hits**.

### 4.3 The `.kd` Descriptor

Inside the `.rodata` of a device ELF there is a set of kernel descriptors (`.kd`), each 64 bytes, indexed by `slot`:

```
.kd start = offset 0xA180 within .rodata + 64 × slot
```

Field layout (measured byte by byte):

| Relative offset | Field | Width |
|---|---|---|
| `+0x00` | `group_segment_fixed_size` | u32 |
| `+0x04` | `private_segment_fixed_size` | u32 |

The role of `.kd` is as an **independent second source**: the LDS / private segment requirements it carries can be collided against the msgpack metadata. Measured collision result: **272/272 consistent** (each of the three fields 272/272), and `entry == code symbol VA − .kd symbol VA` **272/272, 0 counterexamples**.

Example: the `.kd` of k1 is in `#1` @ `0xA1C0`, and the `group_segment_fixed_size` field reads **64,640**; k7 in `#8` has `private_segment_fixed_size` reading **404**. Both agree value by value with the msgpack side.

### 4.4 Symbol Table

`.symtab` / `.strtab` / `.dynsym` are used to:

- recover the kernels' C++ mangled names;
- read the `st_value` / `st_size` of code symbols (used for the `codesz` column);
- detect extra symbols **outside the 34 kernel names**.

An example of extra-symbol detection: `_Z10swin_layerR7SwinLDSPKhRK10BlobLayouti` (**non-template**) exists only in the four targets `#2`–`#5`, with 0 hits in `#1` / `#6` / `#7` / `#8`; the `.symtab` entry count for `#2`–`#5` = 348 and for the rest = 347; the set difference between the symbol sets of `#1` and `#2` is exactly that one symbol; the union of the 8 bundles' symbols = 348 and the intersection = 347.

---

## 5. md-snapshot `.note` Section and AMDGPU msgpack Metadata Decoding

This is the project's **most central metadata source**.

### 5.1 Locating the `.note` Section

Each device ELF has one `.note` section with `sh_type = 7` (SHT_NOTE) and `sh_flags = 2`. The section carries one note:

```
namesz  @ note + 0x00   (u32)
descsz  @ note + 0x04   (u32)
type    @ note + 0x08   (u32)
name    @ note + 0x0C
desc    @ note + 0x0C + align4(namesz)
```

Measured (taking bundle `#1` as the example: `sh_name = 1`, `sh_addr = sh_offset = 0x238`, `sh_size = 0x8B88`): `type = 32` = `NT_AMDGPU_METADATA`; the name is the ASCII `AMDGPU` (`namesz = 8`, including the NUL).

**Start of the msgpack document** = `0x238 + 12 + 8 = 0x24C` (relative to the bundle start).

### 5.2 Document Structure

The top level of the msgpack document is a map whose keys are dot-prefixed field names:

```
{
  ".args": [ { ... }, ... ],          ← parameter array
  ".name": "...",                     ← kernel mangled name
  ".symbol": "...",
  ".kernarg_segment_size": ...,
  ".kernarg_segment_align": ...,
  ".group_segment_fixed_size": ...,
  ".private_segment_fixed_size": ...,
  ".sgpr_count": ...,
  ".sgpr_spill_count": ...,
  ".vgpr_count": ...,
  ".vgpr_spill_count": ...,
  ".wavefront_size": ...,
  ".max_flat_workgroup_size": ...,
  ".workgroup_processor_mode": ...,
  ".uniform_work_group_size": ...,
  ".uses_dynamic_stack": ...,
  ".language": ...,
  ".language_version": ...,
  ...
}
```

### 5.3 Parameter Entries

`.args` is an array of parameter maps. Two key sets were measured:

| Key set | Occurrences |
|---|---|
| `{.offset, .size, .value_kind}` | **3,496** |
| `{.address_space, .offset, .size, .value_kind}` | **24** |

That is, of the 3,520 parameters in the whole set, **only these 24** `global_buffer` parameters carry `.address_space`; the measured value is the string `"global"`, raw bytes `A6 67 6C 6F 62 61 6C`.

**Discipline**: `.value_kind` **is not a kernel-level field**; it appears only inside parameter maps (one per each of the 3,520 parameters; the kernel map has no such key). The key that early material treated as a "device enqueue symbol" gets **0 hits** when searched across the whole set of 8 targets × 34 kernels; that field does not exist in the metadata and must not be used as an actual field.

### 5.4 msgpack Encoding-Width Discipline (a correction that must be observed)

msgpack integers have multiple encoding widths, and **the same numeric value may have different encoding bytes**. One mis-recorded encoding width was found and corrected during the project:

| Item | Value |
|---|---|
| Field | the `.kernarg_segment_size` of `k_reproject` |
| Value | **384** |
| Correct encoding | **`CD 01 80`** (`CD` = **uint16**, big-endian `0x0180` = 384) |
| Coordinate | blob `#1` `[28169, 28172)` → file `0x80255` / VA `0x180087055` |
| Collision | `CD 01 80` gives **1** hit in blob `#1` and **9** hits in the whole DLL; whereas the encoding string formed under the uint32 notation (`CE` + 4 big-endian bytes) gives **0 hits** in both blob `#1` and the whole DLL |

**Conclusion**: when giving encoding bytes, they must be verified together with the decoded numeric value — searching with the wrong encoding width yields a false negative of "0 hits".

Encoding reference (common values involved in this project):

| Value | Encoding |
|---|---|
| 12 | `0C` (positive fixint) |
| 24 | `18` (positive fixint) |
| 32 | `20` (positive fixint) |
| 40 | `28` (positive fixint) |
| 64 | `40` (positive fixint) |
| 80 | `50` (positive fixint) |
| 128 | `CC 80` (uint8) |
| 168 | `CC A8` (uint8) |
| 384 | `CD 01 80` (uint16) |

### 5.5 Consistency and Difference of Cross-Target Decoding

The metadata of the 8 targets is **not of equal length**: the maximum-minus-minimum of `descsz` across the 8 device targets is **938** (`0x3AA`, `#1` `0x8B72` vs `#8` `0x87DA`). Therefore:

> **Cross-target consistency must be done item by item; one must not assume the 8 targets' metadata is byte-identical.**

The item-by-item results (see `04-内核参数规格.md` (in Chinese) §3, §4):

- **Parameter side**: `.kernarg_segment_size`, the `.args` element count, and the per-parameter `.offset` / `.size` / `.value_kind` — 238/238 decision cells consistent, the `.args` arrays' byte-level SHA256 identical 272/272 (12 distinct byte strings), 0 differing entries;
- **Resource side**: of the 16 field entities, **8 are consistent and 8 are inconsistent**.

### 5.6 Locator Read-Back Verification

The parser itself must also be verified. The approach: using an independent msgpack reference implementation, read back and compare **all 4,080 intervals** one by one, with **0 failures**.

---

## 6. Byte Pattern Scanning

Because there is no AMDGPU disassembler, the analysis of the host-side `.text` relies heavily on **byte pattern scanning**. This is a method roughly two orders of magnitude faster than disassembly, but it can only answer "where does some pattern appear".

### 6.1 Scan Denominator

The `.text` code volume is `0x54C36` = **347,190 bytes**. All "whole `.text`" class conclusions use this value as their denominator.

### 6.2 Fast Path: Raw Byte Counting

Pattern matching is done directly over the whole section, **without filtering by instruction boundary**. This gives an **upper bound** on the number of pattern occurrences.

Examples (whole `.text`):

| Pattern | Meaning | Raw hit count |
|---|---|---|
| `FF 15` | `call [rip+disp32]` | 407 |
| `FF 25` | `jmp [rip+disp32]` | 101 |
| `FF D0` | `call rax` | 28 |
| `FF D1` | `call rcx` | 1 |
| `FF D2` | `call rdx` | 6 |
| `FF D3` | `call rbx` | 5 |
| `FF E0` | `jmp rax` | 10 |
| `FF E1` | `jmp rcx` | 13 |
| `FF E2` | `jmp rdx` | 2 |
| `FF E3` | `jmp rbx` | 12 |
| `FF 24 25` | `jmp [disp32]` | 0 |

### 6.3 Slow Path: Confirmation by Instruction Boundary

Raw byte counting is an **upper bound**; a second confirmation by instruction boundary is required to obtain the number of true call sites.

Example (the decomposition of the `FF 25` count of **101**):

| Component | Count | Note |
|---|---|---|
| Export stubs | **17** | `0x1800019D0`–`0x180001AD0`, stride `0x10` |
| Thunk ladder | **55** | `0x1800558D0`–`0x180055C30`, stride `0x10`, continuity check passed |
| Other scattered | **29** | listed address by address |
| **Total** | **101** | ✅ |

**Discipline**: whenever writing "how many call sites are in the whole `.text`", one must state whether it is a **raw byte count** or a count after **confirmation by instruction boundary**. The two may be equal (e.g. `E8` → `0x180055A70`, 60 locations, both calibers giving 60) or unequal (e.g. inside the dispatcher function body `E8` gives **48** raw hits, while the `call`s parsed by instruction boundary number only **38**; the 10 `E8` bytes that are not call starts all fall inside existing instructions).

### 6.4 Resolving RIP-Relative References

Scanning `48 8D 0D/05/15/35 XX XX XX XX` (`lea reg, [rip+disp32]`) and `48 8B XX XX XX XX` (`mov reg, [rip+disp32]`), compute:

```
target = RIP + disp32      (RIP = instruction end address = instruction start + instruction length)
```

Filter for hits that land in the target region. Examples (used to prove the target of `FF 25`):

```
0x180055A70 + 6 = 0x180055A76
0x180055A76 + 0x16292 = 0x18006BD08
```

### 6.5 Closed-Set Enumeration of `E8 rel32`

For one concrete target (e.g. the VA of some thunk), enumerate all locations in the whole `.text` where `E8 rel32` resolves to that VA, obtaining a **closed set**. A closed set is the only qualified form for "where the call sites are" class conclusions.

Example:

| Call target | Hits in the whole `.text` |
|---|---|
| `0x180055A70` (`hipLaunchKernel` thunk) | **60** |
| `0x180055960` (`__hipRegisterFunction` thunk) | **34** |
| `0x180001000` (W1 entry) | **0** |
| `0x180001EB0` (initialization wrapper body) | **2** |

"0 hits" is likewise a conclusion (for example, W1–W26 have no external direct caller).

### 6.6 The `lea` → `call` Distance Criterion

Inside one registration loop, the distance between `lea rdx, [rip+X]` (loading the address of a table slot) and the subsequent `call` (the registration function) is **always `0x14` (20) bytes**. This gives a strong criterion: if at `0x14` before some `call` there is an `lea rdx` whose target falls in the table pointer region, then that `call` pairs with the table and with that slot.

This criterion produced one substantive correction: early on, a wide window of "within `0x40` bytes before the `call`" was used, giving "31 paired + 3 unpaired"; after switching to the fixed `0x14` distance, **the pairing became 34/34 with no unpaired items**. The three slots previously judged "unpaired" (table A slots 30 / 31 / 32) each have their own registration site.

### 6.7 Capability Boundary of Pattern Scanning

Byte pattern scanning **cannot**:

- determine "the semantics of one instruction" (requires disassembly);
- determine "what is written to some memory location at runtime" (requires runtime observation);
- rule out structures that "exist but in a different form" (it can only rule out the patterns that were listed).

Therefore all "0 hits" conclusions from pattern scanning must state the list of searched patterns and the range in the conclusion itself.

---

## 7. Cross-Validation: Independent Re-Derivation

The **core quality mechanism** of this project's methodology is: **every number delivered must be obtained by at least two mutually independent paths**.

### 7.1 What "Independent" Means

"Independent" does not mean "a second person took a look"; it means **independently implemented**:

| Independence dimension | Approach |
|---|---|
| **Implementation independence** | The verifier **does not read** any existing JSON / intermediate artifact, and recomputes directly from the DLL bytes with a **self-written parser** |
| **Path independence** | The same metric is obtained via two different toolchains (e.g. hashing with both `Get-FileHash` and `hashlib.sha256`) |
| **Coordinate independence** | The same value is read from two different structures (e.g. the LDS requirement read from both the msgpack metadata and the device ELF's `.kd` descriptor) |
| **Caliber independence** | The same conclusion is computed once more in the commutative form (e.g. `0x1000 + Σsize + Σgap == VirtualSize`) |

### 7.2 The Three Vehicles of Cross-Validation

**(a) Three independent corroborations (self-consistent counts)**

The conclusion "34 kernels" is corroborated by three mutually independent counts:

| Corroboration | Measured | Relation to the metadata |
|---|---|---|
| (a) code entries in table A `0x180056170..0x1800562A8` that point into `.text` | **34** items | equal |
| (b) calls to `0x180055960` (the `__hipRegisterFunction` thunk) in the whole `.text` | `call` → **34** sites, `jmp` → **0** sites | equal |
| (c) number of kernel entries in the metadata | 272 ÷ 8 = **34** | equal |

The three corroborations are mutually independent (a PE data-section pointer table / a count of code call sites / a msgpack entry count), and the conclusions agree.

**(b) An independent second source (two sets of structures for the same value)**

The LDS and private segment requirements exist in two places simultaneously:

1. the `.group_segment_fixed_size` / `.private_segment_fixed_size` of the msgpack metadata (the `.note` section);
2. the `+0x00` / `+0x04` fields of the 64-byte `.kd` descriptor inside the device ELF's `.rodata`.

Measured collision: **272/272 consistent**, and `entry == code symbol VA − .kd symbol VA` **272/272, 0 counterexamples**.

**(c) Identity closure**

If the structure parsing is correct, the byte accounting should close to 0. The identities established include:

| Identity | Measured |
|---|---|
| `0x1000 + Σsize(0x6514F0) + Σgap(0x4FB8) == 0x6574A8` (= section VirtualSize) | holds |
| 8/8 bundles `e_shoff + e_shnum × e_shentsize == size` | difference 0 |
| Weight container: walking all entries to the end == `uint32@0x0C` | `5,673 == 5,673`, difference 0 |
| Weight container: `Σsize == file size − payload start` | `147,683,778 == 147,689,451 − 5,673`, difference 0 |
| Weight container: `offset[0] == 0` and `offset[i] == Σsize[0..i-1]` | 153/153 hold, chain violations **0/153** |
| kernarg composition: `kernarg == by_value + 66 + 190` (31 kernels) | holds one by one, 31/31 |

### 7.3 Real Errors Caught by Cross-Validation

Independent recomputation is not formalism; it has caught several substantive errors. Typical categories:

| Category | Example |
|---|---|
| **Mis-recorded encoding width** | the 384 of `k_reproject` was originally given with a uint32 encoding string; after switching to the uint16 `CD 01 80`, the original encoding string gives 0 hits in the whole file |
| **Caliber mixing** | treating "8 distinct values" as "8 non-zero entries"; the correct statement is: `.sgpr_spill_count` has **10** non-zero entries, `.vgpr_spill_count` has **14** non-zero entries, and the distinct value counts (including 0) are 8 each |
| **Endpoint truncation** | the upper bound of the search window was cut at table A slot 25, making "97 locations in the whole `.text`" inconsistent with the stated range; the wide caliber gives 110 locations |
| **Mis-labeled address nature** | three addresses (`0x1800124B0`, `0x1800120B0`, `0x180012EBC`) were repeatedly labeled as function entries, but measurement shows all of them fall in the middle of existing functions |
| **Arithmetic error** | the max-minus-min of `descsz` across bundles was originally recorded as 1,410 B; measurement gives 6 distinct values with max − min = **938** |
| **Narrative contradicting the bytes** | "slots 30–32 have no `lea` registration site; their values come from `.rdata` static initializers" was refuted by byte evidence — the three slots each have a registration site |

### 7.4 Handling Conflicts

When two pieces of material give mutually exclusive conclusions about the same fact, the handling rules are:

1. **the bytes adjudicate**, not the age, level of detail, or authorship of the material;
2. if the two sides' byte references **themselves point to different addresses**, first establish which address is correct, then compare the content;
3. if **both sides are defective**, adopt neither and rewrite from the bytes;
4. after adjudication, the overturned statement **is rewritten according to its byte basis**, not simply deleted.

---

## 8. Reproducibility of Results

### 8.1 The Three Elements of Every Conclusion

This project requires every key conclusion to have:

```
conclusion statement
  ├─ evidence: raw byte string / PE-ELF field / arithmetic expression
  ├─ coordinate: file / RVA / VA (triple)
  └─ caliber: which statistical caliber the value was taken from
```

### 8.2 Sample: the Shape of One Complete Conclusion

Taking the LDS requirement of `k_pre_block_1h_32_fp8` as the example:

| Item | Value |
|---|---|
| Conclusion | this kernel's `group_segment_fixed_size` = **64,640 B** |
| Evidence 1 (msgpack) | the `.group_segment_fixed_size` field of this kernel's map inside the device `#1` metadata |
| Evidence 2 (`.kd`) | the `+0x00` u32 field at `.rodata` @ `0xA180 + 64 × slot` of bundle `#1` reads 64,640 |
| Caliber | this value occurs **8 times** under the 272-entry caliber (1 per each of the 8 targets); one **must not** write "this kernel = 64,640" without attaching the caliber |
| Collision | 272/272 consistent |

### 8.3 Known Non-Reproducible Items

For several conclusions the basis lies **outside the workspace**, and this project registers that honestly rather than covering it up. For example: the "no undeclared modifications" conclusion of one review report rests on an **internal self-consistency check** (revision record numbers are consecutive, anchors exist, self-reported counts collide consistently with measurement) and has **not been verified against a first version** — because the first-version entity gets 0 hits on disk. Anyone citing such a conclusion must give that qualifier at the same time, and **must not** upgrade it to "verified".

---

## 9. The Boundary of the Methodology (an honest statement)

The method described in this chapter **cannot** do the following. For any question in the categories below, this project uniformly gives no conclusion:

| Capability boundary | Reason |
|---|---|
| **Runtime behavior** (under what conditions some kernel is called, what value some global is written with) | no AMD hardware (E-1) |
| **Instruction-level semantics** (what operation some piece of device code actually performs) | no AMDGPU disassembler (E-2); the `.text` of the 34 kernels totals 6,081,960 bytes, and **the number of disassembled instructions = 0** |
| **Compile feasibility** (whether the recompiled kernels can compile, whether they can run) | no Intel / SYCL toolchain (E-3) |
| **The specific capabilities of Xe / XMX** (SLM limit, sub-group width, XMX tile constraints) | there is no Xe criterion anywhere in the workspace; nor does the DLL contain any Intel / Xe / SPIR-V target |

This project's methodology therefore produces **specification and assessment**, whose credibility comes from **byte-level traceability** and **independent recomputation**, not from runtime verification.
