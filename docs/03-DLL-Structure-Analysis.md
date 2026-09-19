# DLL Structure Analysis

This document gives the complete structural picture of `dlssnr_amd_pass1.dll`: the section table, the export surface, the import surface, the thunk ladder, the two function pointer tables, the kernel registration mechanism, and one open question (the `71 block`).

## 0. File Identity

| Item | Value |
|---|---|
| File name | `dlssnr_amd_pass1.dll` |
| Size | 7,156,224 bytes (`0x6D3200`) |
| SHA256 | `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| Format | PE32+, ImageBase `0x180000000`, **12 sections** in total |
| `DllCharacteristics` | **`0x0160`** = `HIGH_ENTROPY_VA 0x20` + `DYNAMIC_BASE 0x40` + `NX_COMPAT 0x100`; **`GUARD_CF 0x4000` is not set**. Field location = `OptionalHeader + 0x46` (file `0xD6`), raw 2 bytes `60 01` |
| Module name | `version.dll` (pointed to by the export directory Name RVA) |
| DllMain | Entry RVA `0x2CFCC` → VA `0x18002CFCC` |
| TLS callback | `AddressOfCallbacks = 0x18006B188` |

**One correction regarding `DllCharacteristics`**: `0x4160` once appeared in early material; that was the value of another module (the NVIDIA-side interface layer). The measured raw bytes of this DLL are `60 01`; the bytes govern.

### 0.1 The Two Build Variants

Two builds differing by a single constant exist in the workspace:

| Variant | SHA256 prefix | Location |
|---|---|---|
| Y | `3c9ca13f…` | OptiScaler package side |
| X | `fe96f589…` | installer / setup side |

The two differ by **240 bytes byte by byte, all of them falling in `.rdata`**, and the semantic difference is only `min(maxIter, 2097152u)` vs `262144u`; `.text` / `.hip_fat` are **byte-identical**.

⇒ All of this project's conclusions (except that constant) **apply equally** to both builds.

---

## 1. Section Table (all 12 sections)

| # | Section | RVA | VA | VirtualSize | RAW (file offset) | SizeOfRawData |
|---|---|---|---|---|---|---|
| 1 | `.text` | `0x1000` | `0x180001000` | `0x54C36` | `0x400` | `0x54E00` |
| 2 | `.rdata` | `0x56000` | `0x180056000` | `0x1D0A4` | `0x55200` | `0x1D200` |
| 3 | `.data` | `0x74000` | `0x180074000` | `0x4390` | `0x72400` | `0x2200` |
| 4 | `.pdata` | `0x79000` | `0x180079000` | `0x36B4` | `0x74600` | `0x3800` |
| 5 | `.fptable` | `0x7D000` | `0x18007D000` | `0x100` | `0x77E00` | `0x200` |
| 6 | `.hipFatB` | `0x7E000` | `0x18007E000` | `0x18` | `0x78000` | `0x200` |
| 7 | `.hip_fat` | `0x7F000` | `0x18007F000` | `0x6574A8` | `0x78200` | `0x657600` |
| 8 | `.retarc` | `0x6D7000` | `0x1806D7000` | `0x21F0` | `0x6CF800` | `0x2200` |
| 9 | `.retard` | `0x6DA000` | `0x1806DA000` | `0x18` | `0x6D1A00` | `0x200` |
| 10 | `.tls` | `0x6DB000` | `0x18006DB000` | `0x9` | `0x6D1C00` | `0x200` |
| 11 | `_RDATA` | `0x6DC000` | `0x18006DC000` | `0x1F4` | `0x6D1E00` | `0x200` |
| 12 | `.reloc` | `0x6DD000` | `0x18006DD000` | `0x1090` | `0x6D2000` | `0x1200` |

### 1.1 Observations on the Sections

- **`.hip_fat`** is the largest section (`SizeOfRawData` `0x657600` = 6,649,344 bytes), carrying the GPU-side fatbin container. Its internal structure is in `02-Analysis-Methodology.md` §3.
- The `VirtualSize` of **`.pdata`** `0x36B4` is consistent with **1,167** `RUNTIME_FUNCTION` entries (`0x36B4 = 1167 × 12`), so `.pdata` can serve as a **closed set of function boundaries** — this is the baseline for a large part of this project's analysis.
- The **`.text`** code volume is `0x54C36` = **347,190 bytes**, the denominator for all indirect-call scans.
- **This section table does not contain `.rsrc`** — the DLL has no resource section. (The entity of the 147 MB order of magnitude is an external weight file, measured separately from the 6,649,000 bytes of `.hip_fat`.)
- `.fptable` / `.hipFatB` / `.retard` are auxiliary sections of very small size (`0x18`–`0x100`).
- `.retarc` (`0x21F0`) carries 527 `DIR64` relocations (see §5.4).

### 1.2 The `.data` File Image Boundary (one key fact)

| Item | Value |
|---|---|
| `.data` VA | `0x180074000` |
| `VirtualSize` | `0x4390` |
| `PointerToRawData` | `0x72400` |
| `SizeOfRawData` | `0x2200` |

**The file image covers only VA `0x180074000..0x180076200`**; the part with VA ≥ `0x180076200` **has no file image and is zero-initialized at load time (BSS type)**.

Therefore `0x180076390` / `0x180076394` / `0x180076398` / `0x180077394` / `0x180077398` **all have no file initial value**.

**Refuting "the bytes read by file offset really belong to `.pdata`"**: for `0x180076394`, using `file = VA − 0x180074000 + 0x72400` gives file `0x74794`, and that offset falls inside the `.pdata` section (RAW `0x74600..0x77E00`) — file `0x74794` = offset `0x194` within the `.pdata` section → record index **33** (0-based), field `UnwindInfoRVA` = `0x6D2A8`; file `0x74798` → record index **34**, field `BeginRVA` = `0x2D20`.

⇒ For a BSS-type global, "the bytes read by file offset" belong to **some other structure** and do not constitute that global's initial value.

### 1.3 Address Conversion (verified by measurement)

| Section | Conversion |
|---|---|
| `.text` | `file = VA − 0x180001000 + 0x400` |
| `.rdata` | `file = VA − 0x180056000 + 0x55200` |
| `.hip_fat` | `file = VA − 0x18007F000 + 0x78200` |

Check points: VA `0x180012380` → file `0x11780`; VA `0x180055A70` → file `0x54E70`.

---

## 2. The `version.dll` Proxy Export Surface

### 2.1 Export Directory Header

| Item | Value |
|---|---|
| `NumberOfFunctions` / `NumberOfNames` / `Base` | **17 / 17 / 1** |
| Entry addresses | `0x1800019D0 + 0x10k` (k = 0..16), **all falling in `.text`** |
| Entry byte shape | 16 bytes each: `FF 25 disp32` (**6 bytes**) + `66 2E 0F 1F 84 00 00 00 00 00` (**10 bytes of NOP padding**) |
| Jump targets | `0x180076440`, `0x180076448`, …, `0x1800764C0` (stride 8, **17** items in total), located at the tail of `.data` |
| PE static forwarders (Forwarder RVA) | **0** (all Forwarder fields are None) |
| Module name | `version.dll` |
| `.reloc` `DIR64` coverage of `0x180076440–0x1800764C0` | **0 entries** |

### 2.2 The 17 Export Names and RVAs

| Export name | RVA |
|---|---|
| `GetFileVersionInfoA` | `0x19D0` |
| `GetFileVersionInfoByHandle` | `0x19E0` |
| `GetFileVersionInfoExA` | `0x19F0` |
| `GetFileVersionInfoExW` | `0x1A00` |
| `GetFileVersionInfoSizeA` | `0x1A10` |
| `GetFileVersionInfoSizeExA` | `0x1A20` |
| `GetFileVersionInfoSizeExW` | `0x1A30` |
| `GetFileVersionInfoSizeW` | `0x1A40` |
| `GetFileVersionInfoW` | `0x1A50` |
| `VerFindFileA` | `0x1A60` |
| `VerFindFileW` | `0x1A70` |
| `VerInstallFileA` | `0x1A80` |
| `VerInstallFileW` | `0x1A90` |
| `VerLanguageNameA` | `0x1AA0` |
| `VerLanguageNameW` | `0x1AB0` |
| `VerQueryValueA` | `0x1AC0` |
| `VerQueryValueW` | `0x1AD0` |

**17/17 all correspond correctly.**

### 2.3 The Correct Statement of the Proxy Mechanism

> **The 17 export "names" are VERSION.dll API names; the export "entries" are `FF 25` thunks through the 17-item pointer table in the `.data` section (VA `0x180076440`).**

All three points must be given together, otherwise a wrong understanding results:

1. **Export table static forwarders = 0** — this is **not** the PE forwarder mechanism. The forwarder mechanism requires `AddressOfFunctions[i]` to fall **inside** the export directory; measured, 17/17 fall in `.text`.
2. **The export entries are pure stubs** — 16 bytes each, 6 bytes of `FF 25` + 10 bytes of NOP, with no actual code.
3. **The jump target is the 17-item pointer table in `.data`, and that table is not covered in `.reloc` and has no file bytes** — i.e. the table is filled at **runtime**, and the filling path is not evidenced (see §7.2 U-6).

**One address that has been repeatedly mis-labeled**: `0x180001AE0` **is not the function body of any export**.

- Export `VerQueryValueW` = **`0x180001AD0`** (16-byte stub, bytes `FF 25 EA 49 07 00 66 2E 0F 1F 84 00 00 00 00 00`);
- Export `VerQueryValueA` = **`0x180001AC0`** (pure thunk);
- `0x180001AE0` is an **independent `.pdata` function** (interval `0x180001AE0..0x180001B6A`, length `0x8A` = 138), and its two internal calls must **be counted from `0x180001AE0`**:
  - `+0x4F` (VA `0x180001B2F`): `E8 FC 3D 05 00` → `0x180055930` (`__hipPopCallConfiguration`)
  - `+0x7A` (VA `0x180001B5A`): `E8 11 3F 05 00` → `0x180055A70` (`hipLaunchKernel`)

Early material recorded the same code block under the export `VerQueryValueW` (`0x180001AD0`), **with the base address off by `0x10`**.

---

## 3. Import Surface (194 entries / 10 DLLs)

### 3.1 Classification DLL by DLL

Measurement method: self-written PE parsing (`DataDirectory[1]` = IMPORT, RVA `0x6B3F4` / Size `0xDC`), decoding the ILT / IAT descriptor by descriptor and reading the names.

| # | DLL | Entries | ILT | IAT range | Nature |
|---|---|---|---|---|---|
| 1 | `d3d12.dll` | 1 | `0x18006B4D0` | `0x18006BB30` | graphics side (D3D12 root signature serialization) |
| 2 | `dxgi.dll` | 1 | `0x18006B4E0` | `0x18006BB40` | graphics side (DXGI factory) |
| 3 | `D3DCOMPILER_47.dll` | 1 | `0x18006B4F0` | `0x18006BB50` | graphics side (runtime HLSL compilation) |
| 4 | `USER32.dll` | 15 | `0x18006B500` | `0x18006BB60–0x18006BBC0` | system side (window / input / text drawing) |
| 5 | `GDI32.dll` | 10 | `0x18006B580` | `0x18006BBE0–0x18006BC28` | system side (bitmap / DC / font) |
| 6 | `COMDLG32.dll` | 1 | `0x18006B5D8` | `0x18006BC38` | system side (open file dialog) |
| 7 | `VERSION.dll` | 3 | `0x18006B5E8` | `0x18006BC48–0x18006BC58` | system side (file version information) |
| 8 | **`amdhip64_7.dll`** | **29** | `0x18006B608` | `0x18006BC68–0x18006BD48` | **AMD HIP runtime** |
| 9 | `bcrypt.dll` | 6 | `0x18006B6F8` | `0x18006BD58–0x18006BD80` | system side (CNG hashing) |
| 10 | `KERNEL32.dll` | 127 | `0x18006B730` | `0x18006BD90–0x18006C180` | system side (Win32 basics) |
| — | **Total** | **194** | — | — | 10 DLLs |

- All imports are **imported by name**, with **ordinal = 0**.
- The first of `amdhip64_7.dll`'s 29 items is `__hipPopCallConfiguration` (slot `0x18006BC68`), and the last is `hipSetDevice` (slot `0x18006BD48`).
- The first slot of the next import DLL, `bcrypt.dll`, is `0x18006BD58`.

### 3.2 Each DLL and Its Relation to the "AMD → Intel" Replacement Axis

| DLL | Entries | On the replacement axis |
|---|---|---|
| `KERNEL32.dll` | 127 | no (Win32 basics) |
| **`amdhip64_7.dll`** | **29** | **yes** (the HIP runtime, the main replacement target) |
| `USER32.dll` | 15 | no |
| `GDI32.dll` | 10 | no |
| `bcrypt.dll` | 6 | no |
| `VERSION.dll` | 3 | no |
| `d3d12.dll` | 1 | no (but artifact compatibility needs verification) |
| `dxgi.dll` | 1 | no (same as above) |
| `D3DCOMPILER_47.dll` | 1 | no (same as above) |
| `COMDLG32.dll` | 1 | no |

**Replacement ratio = 29 / 194 = 14.9%** (computed as 29 ÷ 194 = 0.14948…), and the remaining 165 entries (85.1%) need no replacement **at the import surface level**. The detailed table is in `05-Intel可行性评估.md` (in Chinese) §5.

### 3.3 Porting Implications of the Graphics-Side Imports

Besides the HIP runtime surface, this DLL **also statically imports**:

- `d3d12.dll!D3D12SerializeRootSignature` (IAT `0x18006BB30`, **3** `E8` call sites)
- `dxgi.dll!CreateDXGIFactory1` (IAT `0x18006BB40`, **1** site)
- `D3DCOMPILER_47.dll!D3DCompile` (IAT `0x18006BB50`, **4** sites)
- `COMDLG32.dll!GetOpenFileNameW` (IAT `0x18006BC38`, **0** `E8` sites)

plus runtime resolution capability: `GetProcAddress` (IAT `0x18006BF60`, **25** direct IAT references), `LoadLibraryA` (`0x18006C030`), `LoadLibraryExW` (`0x18006C038`), `FreeLibrary` (`0x18006BE78`, **7** sites), `GetModuleHandleA/W` (`0x18006BF30` / `0x18006BF40`, **9** sites).

⇒ For a port to Intel Arc, besides replacing the HIP runtime, the whole graphics-side import surface must also be covered. Whether the **artifacts** of these 3 + 4 = **7 call sites** are compatible with the D3D12 driver on Xe must be verified during the actual port.

### 3.4 Import Name Resolution Examples

| IAT slot | hint | Name | Name RVA / file |
|---|---|---|---|
| `0x18006BD08` | 388 (`0x0184`) | `hipLaunchKernel` | RVA `0x6C59A` |
| `0x18006BD28` | 496 | `hipMemcpyToSymbol` | file `0x6AF28` |
| `0x18006BC68` | 116 | `__hipPopCallConfiguration` | — |
| `0x18006BC70` | 117 | `__hipPushCallConfiguration` | — |
| `0x18006BC78` | 118 | `__hipRegisterFatBinary` | — |
| `0x18006BC80` | 119 | `__hipRegisterFunction` | — |

**One correction**: the 2-byte RVA hint of slot `0x18006BD08` is **388** (`0x0184`), followed by the ASCII `hipLaunchKernel` (**not empty**). The early material's record of "Hint 32276, Function name empty (containing a NUL byte)" was a parsing error.

---

## 4. The `hipLaunchKernel` Thunk Ladder and the Calling Mechanism

### 4.1 Mechanism Overview

HIP API calls inside `.text` are **all made through `FF 25 disp32` (`jmp qword ptr [rip+disp32]`) thunks**:

```
call site  ──E8 rel32──>  thunk (FF 25 disp32)  ──>  IAT slot  ──>  amdhip64_7.dll
```

The thunk region has a **16-byte stride** shape: `FF 25 …` (6 bytes) + `CC`×10 or NOP padding.

### 4.2 Overall Composition of the Thunk Ladder

| Item | Value |
|---|---|
| Ladder range | `0x1800558D0`–`0x180055C30` |
| Stride | `0x10` (16 bytes) |
| Count | **55** |
| Continuity check | **passed, no gaps** |

The whole `.text` `FF 25` **raw byte count = 101**, decomposed as:

| Component | Count |
|---|---|
| Export stubs (`0x1800019D0`–`0x180001AD0`) | **17** |
| Thunk ladder (`0x1800558D0`–`0x180055C30`) | **55** |
| Other scattered | **29** |
| **Total** | **101** |

**One abandoned statement**: "thunk count 100" and "thunk block end `0x180055C20`" disagree with measurement — the measured ladder end is `0x180055C30` and the count is 55.

**One sub-interval correction**: the sub-interval `0x180055900–0x180055B0F` measures exactly **33** entries (stride `0x10`, targets all IAT slots); it is **part of the 55-item ladder region**, and the two do not contradict. What should be abandoned is only the usage of treating it as "the ladder as a whole".

### 4.3 IAT Slot Attribution of the Ladder

The 55 entries attributed by index:

| Attribution | Count |
|---|---|
| `d3d12.dll` | 1 |
| `dxgi.dll` | 1 |
| `D3DCOMPILER_47.dll` | 1 |
| `VERSION.dll` | 3 |
| **`amdhip64_7.dll`** | **29** |
| `bcrypt.dll` | 6 |
| **`KERNEL32.dll`** | **14** |
| **Total** | **55** |

The 14 KERNEL32 entries at indices 41–54 are: `FlushInstructionCache` / `GetCurrentProcess` / `GetCurrentThread` / `GetCurrentThreadId` / `GetLastError` / `GetThreadContext` / `ResumeThread` / `SetLastError` / `SetThreadContext` / `SuspendThread` / `VirtualAlloc` / `VirtualFree` / `VirtualProtect` / `VirtualQuery`.

### 4.4 Key Thunks (entries with byte evidence)

| thunk VA | file | Raw bytes | → IAT slot | Resolved name (hint) |
|---|---|---|---|---|
| `0x1800558D0` | `0x54CD0` | `FF 25 5A 62 01 00` | `0x18006BB30` | `D3D12SerializeRootSignature` (14) |
| `0x1800558E0` | — | — | `0x18006BB40` | `CreateDXGIFactory1` (4) |
| `0x1800558F0` | — | — | `0x18006BB50` | `D3DCompile` (1) |
| `0x180055900` | — | — | `0x18006BC48` | `VERSION.dll!GetFileVersionInfoA` (0) |
| `0x180055910` | — | — | `0x18006BC50` | `VERSION.dll!GetFileVersionInfoSizeA` (4) |
| `0x180055920` | — | — | `0x18006BC58` | `VERSION.dll!VerQueryValueA` (15) |
| `0x180055930` | `0x54D30` | `FF 25 32 63 01 00` | `0x18006BC68` | `__hipPopCallConfiguration` (116) |
| `0x180055940` | — | — | `0x18006BC70` | `__hipPushCallConfiguration` (117) |
| `0x180055950` | `0x54D50` | `FF 25 22 63 01 00` | `0x18006BC78` | `__hipRegisterFatBinary` (118) |
| `0x180055960` | `0x54D60` | `FF 25 1A 63 01 00` | `0x18006BC80` | `__hipRegisterFunction` (119) |
| `0x180055A70` | `0x54E70` | `FF 25 92 62 01 00` | `0x18006BD08` | `hipLaunchKernel` (388) |
| `0x180055A80` | `0x54E80` | `FF 25 8A 62 01 00` | `0x18006BD10` | `hipMalloc` |
| `0x180055A90` | `0x54E90` | `FF 25 82 62 01 00` | `0x18006BD18` | `hipMemcpy` |
| `0x180055AA0` | `0x54EA0` | `FF 25 7A 62 01 00` | `0x18006BD20` | `hipMemcpyAsync` |
| `0x180055AB0` | `0x54EB0` | `FF 25 72 62 01 00` | `0x18006BD28` | `hipMemcpyToSymbol` (496) |

**Target verification example**: `0x180055A70 + 6 = 0x180055A76`; `0x180055A76 + 0x16292 = 0x18006BD08`.

### 4.5 Three Statements That Must Be Explicitly Refuted

| Statement | Why it does not hold |
|---|---|
| "the `hipLaunchKernel` thunk = `0x180055670`" | the bytes at `0x180055670` are `EC 20 48 8B EA 80 7D 70 00`, **not `FF 25`**; its preceding `push rbp` is at `0x18005566A`, i.e. that address falls in the middle of a function. The real thunk is `0x180055A70` |
| "the handle table is at `0x180055D70`–`0x180058668`" | `0x180055D70` / file `0x55170` is **all `0xCC` padding**. The real table is at `0x180056170` (`.rdata`, from file `0x55370`) |
| "the Dispatcher calls `hipLaunchKernel` or a wrapper" | among the **38 `call`** targets of the dispatcher (19 distinct targets, fully enumerated) there is **no** `0x180055A70`, and **no wrapper body of any kind** |

---

## 5. The Two 8-Byte-Stride Function Pointer Tables

This is the most central — and the most error-prone — part of this DLL's structure analysis.

### 5.1 Table Entry Semantics and Slot Width (two settled points)

**Settled point one: table entry semantics = 8-byte absolute VA** (not a section-relative offset / RVA). Three independent criteria:

| # | Criterion | Result |
|---|---|---|
| ① | **Image range criterion** — interpreting as RVA (low 32 bits + `0x180000000` gives values like `0x200001000`, or the whole 64-bit value plus the base gives `0x300001000`) | **all exceed the actual image upper bound `0x1806DE090`** |
| ② | **Structure match criterion** — under the 8-byte interpretation, 34/34 function pointer entries **land exactly on `.pdata` entry starts** | the RVA interpretation gives **0 hits** |
| ③ | **High-byte criterion** — the top 4 bytes of a table entry are always `0x00000001` | the typical encoding of a 64-bit absolute address |

**Settled point two: "4-byte slots" does not hold.** Three criteria:

- the `uint64 LE` of table A items 0–25 is **26/26** exactly `0x180001000 + 0x60k`;
- under the 4-byte view, the first 51 dwords "fall inside the image" = **0/51** and "are exactly `.pdata` starts" = **0/51** (example dwords `0x80001000` / `0x00000001` are half a value + a high-bit flag);
- the measured distance between adjacent slots is **8 bytes**.

**Clause-by-clause adjudication (handling of the early "4-byte slots" statement)**:

| Early statement | Adjudication (under the 8-byte entry caliber) |
|---|---|
| the base `0x180056170` holds | **holds** |
| "slot 26 = NULL" | **holds** |
| "slots 27–29 = `0xFFFFFFFC`" | **holds** under the 4-byte dword caliber, **does not hold** when counted as 8-byte entries (the values of 8-byte entries 27/28/29 are `0xFFFFFFFCFFFFFFFC` / `0x00000000FFFFFFFC` / `0xFFFFFFFC00000000` respectively; and there is a 4th `0xFFFFFFFC` dword at `0x18005625C`) |
| "slot 41 = 0 terminates" | **holds** (the function pointer region terminates); but "the table ends at slot 41" does not hold — slots 42–45 have data |

### 5.2 Table A @ `0x180056170`, Full Table (items 0–45)

file conversion: `file = VA − 0x180056000 + 0x55200`

| Item | Slot VA | file | 8 raw bytes | `uint64 LE` | Nature |
|---|---|---|---|---|---|
| 0 | `0x180056170` | `0x55370` | `00 10 00 80 01 00 00 00` | `0x180001000` | `.text` function start (`.pdata` idx 0) |
| 1 | `0x180056178` | `0x55378` | `60 10 00 80 01 00 00 00` | `0x180001060` | idx 1 |
| 2 | `0x180056180` | `0x55380` | `C0 10 00 80 01 00 00 00` | `0x1800010C0` | idx 2 |
| 3 | `0x180056188` | `0x55388` | `20 11 00 80 01 00 00 00` | `0x180001120` | idx 3 |
| 4 | `0x180056190` | `0x55390` | `80 11 00 80 01 00 00 00` | `0x180001180` | idx 4 |
| 5 | `0x180056198` | `0x55398` | `E0 11 00 80 01 00 00 00` | `0x1800011E0` | idx 5 |
| 6 | `0x1800561A0` | `0x553A0` | `40 12 00 80 01 00 00 00` | `0x180001240` | idx 6 |
| 7 | `0x1800561A8` | `0x553A8` | `A0 12 00 80 01 00 00 00` | `0x1800012A0` | idx 7 |
| 8 | `0x1800561B0` | `0x553B0` | `00 13 00 80 01 00 00 00` | `0x180001300` | idx 8 |
| 9 | `0x1800561B8` | `0x553B8` | `60 13 00 80 01 00 00 00` | `0x180001360` | idx 9 |
| 10 | `0x1800561C0` | `0x553C0` | `C0 13 00 80 01 00 00 00` | `0x1800013C0` | idx 10 |
| 11 | `0x1800561C8` | `0x553C8` | `20 14 00 80 01 00 00 00` | `0x180001420` | idx 11 |
| 12 | `0x1800561D0` | `0x553D0` | `80 14 00 80 01 00 00 00` | `0x180001480` | idx 12 |
| 13 | `0x1800561D8` | `0x553D8` | `E0 14 00 80 01 00 00 00` | `0x1800014E0` | idx 13 |
| 14 | `0x1800561E0` | `0x553E0` | `40 15 00 80 01 00 00 00` | `0x180001540` | idx 14 |
| 15 | `0x1800561E8` | `0x553E8` | `A0 15 00 80 01 00 00 00` | `0x1800015A0` | idx 15 |
| 16 | `0x1800561F0` | `0x553F0` | `00 16 00 80 01 00 00 00` | `0x180001600` | idx 16 |
| 17 | `0x1800561F8` | `0x553F8` | `60 16 00 80 01 00 00 00` | `0x180001660` | idx 17 |
| 18 | `0x180056200` | `0x55400` | `C0 16 00 80 01 00 00 00` | `0x1800016C0` | idx 18 |
| 19 | `0x180056208` | `0x55408` | `20 17 00 80 01 00 00 00` | `0x180001720` | idx 19 |
| 20 | `0x180056210` | `0x55410` | `80 17 00 80 01 00 00 00` | `0x180001780` | idx 20 |
| 21 | `0x180056218` | `0x55418` | `E0 17 00 80 01 00 00 00` | `0x1800017E0` | idx 21 |
| 22 | `0x180056220` | `0x55420` | `40 18 00 80 01 00 00 00` | `0x180001840` | idx 22 |
| 23 | `0x180056228` | `0x55428` | `A0 18 00 80 01 00 00 00` | `0x1800018A0` | idx 23 |
| 24 | `0x180056230` | `0x55430` | `00 19 00 80 01 00 00 00` | `0x180001900` | idx 24 |
| 25 | `0x180056238` | `0x55438` | `60 19 00 80 01 00 00 00` | `0x180001960` | idx 25 |
| 26 | `0x180056240` | `0x55440` | `00 00 00 00 00 00 00 00` | `0` | **NULL** |
| 27 | `0x180056248` | `0x55448` | `FC FF FF FF FC FF FF FF` | `0xFFFFFFFCFFFFFFFC` | sentinel (two 4-byte `0xFFFFFFFC`) |
| 28 | `0x180056250` | `0x55450` | `FC FF FF FF 00 00 00 00` | `0x00000000FFFFFFFC` | sentinel + 0 |
| 29 | `0x180056258` | `0x55458` | `00 00 00 00 FC FF FF FF` | `0xFFFFFFFC00000000` | 0 + sentinel |
| 30 | `0x180056260` | `0x55460` | `E0 1A 00 80 01 00 00 00` | `0x180001AE0` | `.text` function start (`.pdata` idx 26, auxiliary wrapper) |
| 31 | `0x180056268` | `0x55468` | `70 1B 00 80 01 00 00 00` | `0x180001B70` | idx 27 |
| 32 | `0x180056270` | `0x55470` | `E0 1B 00 80 01 00 00 00` | `0x180001BE0` | idx 28 |
| 33 | `0x180056278` | `0x55478` | `00 00 00 00 00 00 00 00` | `0` | NULL |
| 34 | `0x180056280` | `0x55480` | `C0 62 05 80 01 00 00 00` | `0x1800562C0` | address inside `.rdata` (not `.text`) |
| 35 | `0x180056288` | `0x55488` | `A0 7E 00 80 01 00 00 00` | `0x180007EA0` | inside `.text`, **not** a `.pdata` start |
| 36 | `0x180056290` | `0x55490` | `B0 7E 00 80 01 00 00 00` | `0x180007EB0` | same as above |
| 37 | `0x180056298` | `0x55498` | `C0 7E 00 80 01 00 00 00` | `0x180007EC0` | same as above |
| 38 | `0x1800562A0` | `0x554A0` | `F0 7E 00 80 01 00 00 00` | `0x180007EF0` | same as above |
| 39 | `0x1800562A8` | `0x554A8` | `00 7F 00 80 01 00 00 00` | `0x180007F00` | same as above |
| 40 | `0x1800562B0` | `0x554B0` | `10 7F 00 80 01 00 00 00` | `0x180007F10` | same as above |
| 41 | `0x1800562B8` | `0x554B8` | `00 00 00 00 00 00 00 00` | `0` | end of the function pointer region |
| 42 | `0x1800562C0` | `0x554C0` | `01 00 00 00 00 00 00 00` | `0x1` | not a function pointer shape |
| 43 | `0x1800562C8` | `0x554C8` | `00 00 00 00 50 40 07 00` | `0x0007405000000000` | not a function pointer shape |
| 44 | `0x1800562D0` | `0x554D0` | `D8 62 05 00 C0 62 05 00` | two 4-byte `.rdata` RVAs (`0x562D8` / `0x562C0`) | not a function pointer shape |
| 45 | `0x1800562D8` | `0x554D8` | `00 00 00 00 00 00 00 00` | `0` | — |

**Table A's function pointer region = items 0–41**; among them, items 0–25 (26 same-template wrappers) + items 30–32 (3 auxiliary wrappers) = **29**.

**Table A structure summary**:

- slots 0–25: W1–W26 same-template wrapper addresses (stride 8)
- slot 26: NULL separator
- slots 27–29: sentinel `0xFFFFFFFC` (byte-interleaved)
- slots 30–32: auxiliary kernel wrappers (`k_flag_wait` / `k_align_probe` / `k_flag_set`)
- slot 33: NULL separator
- slot 34: an internal `.rdata` pointer
- slots 35–40: **6** swin_var helper function addresses
- slot 41: NULL (end of the function pointer region)
- slots 42–45: non-function-pointer data (small values / `.rdata` pointers)

**One correction**: early material recorded "slots 35–39: 5 helpers"; measurement gives **slots 35–40, 6 in total** (`0x180007EA0` / `EB0` / `EC0` / `EF0` / `F00` / `F10`, files in order `0x72A0` / `72B0` / `72C0` / `72F0` / `7300` / `7310`).

### 5.3 Table B @ `0x180058A48`, Full Table (items 0–11)

file conversion: `file = VA − 0x180058000 + 0x57600`

| Item | Slot VA | file | 8 raw bytes | `uint64 LE` | Nature |
|---|---|---|---|---|---|
| 0 | `0x180058A48` | `0x57C48` | `D0 2F 02 80 01 00 00 00` | `0x180022FD0` | `.text` function start (`.pdata` idx 351) |
| 1 | `0x180058A50` | `0x57C50` | `50 55 02 80 01 00 00 00` | `0x180025550` | idx 365 |
| 2 | `0x180058A58` | `0x57C58` | `B0 55 02 80 01 00 00 00` | `0x1800255B0` | idx 366 |
| 3 | `0x180058A60` | `0x57C60` | `10 56 02 80 01 00 00 00` | `0x180025610` | idx 367 |
| 4 | `0x180058A68` | `0x57C68` | `70 56 02 80 01 00 00 00` | `0x180025670` | idx 368 |
| 5 | `0x180058A70` | `0x57C70` | `11 B3 FC FF C2 B5 FC FF` | two negative-value 4-byte sentinels | sentinel region |
| 6 | `0x180058A78` | `0x57C78` | `C6 B9 FC FF 6F B4 FC FF` | two negative-value sentinels | sentinel region |
| 7 | `0x180058A80` | `0x57C80` | `C6 B9 FC FF C6 B9 FC FF` | two negative-value sentinels | sentinel region |
| 8 | `0x180058A88` | `0x57C88` | `C6 B9 FC FF 15 B7 FC FF` | two negative-value sentinels | sentinel region |
| 9 | `0x180058A90` | `0x57C90` | `00 00 00 00 00 00 00 00` | `0` | NULL |
| 10 | `0x180058A98` | `0x57C98` | `FF FF FF FF FF FF FF FF` | `0xFFFFFFFFFFFFFFFF` | all-`FF` sentinel |
| 11 | `0x180058AA0` | `0x57CA0` | `98 2F 06 80 01 00 00 00` | `0x180062F98` | address inside `.rdata` |

**Table B's function pointer region = items 0–4 (5 same-template instances)**.

### 5.4 The Count Equation, Settled

> **Table A wrapper count 29 (26 + 3) + table B 5 = 34 == the `.hip_fat` metadata kernel total 34**

This equation is supported by two independent criteria: the decoded results of the `uint64` values in the table slots, and the 34 kernel entries of the `.hip_fat` metadata.

### 5.5 `.reloc` Coverage and the Self-Consistency of "Absolute VA"

**Manual parsing** (using only `DataDirectory[5]` RVA `0x6DD000` / Size `0x1090` and the block structure):

| Item | Value |
|---|---|
| Block count | **19** |
| Total entries | **2044** |
| Type distribution | `DIR64`(10) **2040** + `ABSOLUTE`(0) **4** |
| `DIR64` by section | `.rdata` 1412 + `.data` 100 + `.hipFatB` 1 + `.retarc` 527 |

**Coverage**:

| Interval | `DIR64` covered entries | Evidence |
|---|---|---|
| Table A interval RVA `0x56170..0x5624F` | **26** | entries from file `0x6D2008`, first three raw 2 bytes `70 A1` / `78 A1` / `80 A1`, last entry RVA `0x56238` |
| Table B interval RVA `0x58A40..0x58A7F` | **5** | from file `0x6D2310`: `48 AA` / `50 AA` / `58 AA` / `60 AA` / `68 AA` |
| `0x180076390..0x18007639F` | **0** | — |
| `0x180077390..0x18007739F` | **0** | — |

**Ruling**: 26 + 5 = **31 pointer slots are indeed covered by `DIR64`**, which is **self-consistent** with the load-time relocation implied by `DYNAMIC_BASE (0x40)` / `HIGH_ENTROPY_VA (0x20)`. The original tension of "the table entries are absolute VAs yet are not relocated" **does not hold**.

That the two BSS global intervals have coverage 0 is also a meaningful fact — they are not pointers and need no relocation.

### 5.6 The Filler (who writes these two tables)

**(a) Filler = a single `.pdata` function: idx 136 = `[0x180010810, 0x180010F77)` (length 1895)**

Within this function, `call → 0x180055960` (the `__hipRegisterFunction` thunk) gets **34** hits.

**Pairing adjudication: 34/34, no unpaired items.** Criterion: at `0x14` (20) bytes before that `call` there is an `lea rdx, [rip+X]` with X falling in the table A/B pointer region (the distance between `lea rdx` and `call` is **always `0x14`**). Distribution:

| Points to | Count |
|---|---|
| table A slots 0–25 | **26** |
| table A slots 30–32 | **3** |
| table B slots 0–4 | **5** |
| **Total** | **34** |

**The 34 `lea` sites (stride `0x34` = 52 bytes)**:

| Points to | Site VA |
|---|---|
| `0x180056170 + 8k` (table A slots 0–25) | `0x18001085A`, `0x18001088E`, `0x1800108C2` … `0x180010D6E` |
| table A slots 30–32 | `0x180010DA2`, `0x180010DD6`, `0x180010E0A` |
| `0x180058A48 + 8j` (table B slots 0–4) | `0x180010E3E`, `0x180010E72`, `0x180010EA6`, `0x180010EDA`, `0x180010F0E` |

`lea` site + `0x14` is the registration call site (e.g. `0x18001085A` → `0x18001086E`; `0x180010DA2` → `0x180010DB6`).

**(b) The registration sites of the three auxiliary wrappers (all five elements present)**

| Site (`call`) VA | RVA | file | Raw 5 bytes | `lea rdx` site VA / raw 6 bytes → target slot | `lea r8` target | kernel name |
|---|---|---|---|---|---|---|
| `0x180010DB6` | `0x10DB6` | `0x101B6` | `E8 A5 4B 04 00` | `0x180010DA2` / `48 8D 15 B7 54 04 00` → **`0x180056260`** (table A slot 30 / content `0x180001AE0` / idx 26) | `0x1800578A3` | `_Z11k_flag_waitPjjj` |
| `0x180010DEA` | `0x10DEA` | `0x101EA` | `E8 71 4B 04 00` | `0x180010DD6` / `48 8D 15 8B 54 04 00` → **`0x180056268`** (table A slot 31 / content `0x180001B70` / idx 27) | `0x1800578B7` | `_Z13k_align_probePh` |
| `0x180010E1E` | `0x10E1E` | `0x1021E` | `E8 3D 4B 04 00` | `0x180010E0A` / `48 8D 15 5F 54 04 00` → **`0x180056270`** (table A slot 32 / content `0x180001BE0` / idx 28) | `0x1800578CB` | `_Z10k_flag_setPjj` |

**(c) A second independent piece of evidence: the self-referential slot `lea rcx` of the three auxiliary wrappers themselves**

| Function (`.pdata` idx) | `lea rcx` VA | → target slot | Slot content |
|---|---|---|---|
| 26 (`0x180001AE0`) | `0x180001B48` | **`0x180056260`** | `0x180001AE0` |
| 27 (`0x180001B70`) | `0x180001BB8` | **`0x180056268`** | `0x180001B70` |
| 28 (`0x180001BE0`) | `0x180001C39` | **`0x180056270`** | `0x180001BE0` |

This is **fully isomorphic** to the shape of the 26 same-template instances, which at `+0x3E` reference their own slot.

**(d) An old judgment that was overturned**

Early material recorded: "slots 30–32 have no `lea` registration site; their values come from `.rdata` static initializers (initialized by the PE loader)", and on that basis judged "slots 30–32 ↔ the three exception kernels" to be "derived by elimination + ordering".

**That judgment has been overturned by byte evidence**: measured, **all 34 registration calls** carry an `lea rdx` at `call − 0x14`, and 3 of them point to table A slots 30 / 31 / 32. Therefore:

> **"The one-to-one correspondence of table A slots 30–32 ↔ `k_flag_wait` / `k_align_probe` / `k_flag_set` is direct byte evidence."**

Three independent elements are given simultaneously in the same instruction sequence of the same registration site: ① `lea rdx` → the slot; ② `lea r8` → the kernel name string; ③ the slot content = the function entry VA of the corresponding wrapper. Together with the self-referential slots of (c), that makes two independent groups of evidence.

**(e) The parameter structure of the registration call** (full disassembly of site #1)

```
mov rsi, [rip+0x667bf]        ; module handle cache
lea rcx, [rip+0x6d7d3]
call 0x180055950              ; __hipRegisterFatBinary (obtain the module handle)
lea rdx, [rip+0x4590f]        ; → 0x180056170 (table A slot 0)
lea r8,  [rip+0x46d58]        ; → 0x1800575C0 (kernel name string)
mov rcx, rsi
mov r9, r8
call 0x180055960              ; __hipRegisterFunction
```

That is, **`rcx` = the module handle, `rdx` = &table slot, `r8` = &kernel name (passed again via `r9`)**.

⇒ **The kernel name is an actual argument carried directly by the registration call** (`r8`), **not an inference**.

### 5.7 The Readers (who reads these two tables)

**Search scope** = all 1167 `.pdata` functions in `.text`, linearly disassembled along instruction boundaries; **pattern** = RIP-relative memory operands whose target falls in the two tables' pointer region.

| idx | Function range | Reference count | Nature | `call 0x180055A70` count within the function |
|---|---|---|---|---|
| 0–25 | the 26 same-template wrappers | 1 each (26 total) | at `+0x3E`, an `lea rcx` pointing to **its own slot** | 1 each |
| 26 / 27 / 28 | the 3 auxiliary wrappers | 1 each (3 total) | self-referential slot `lea rcx` → table A slots 30 / 31 / 32 | 1 each |
| 64 | `[0x180007030, 0x1800076AC)` | 1 | read site, `lea rcx` @ `0x180007156` → table A slot 35 | 0 |
| 96 | `[0x1800095B0, 0x18000975F)` | 1 | read site, `lea rcx` @ `0x18000969D` → table A slot 31 | 1 |
| 122 | `[0x18000DD60, 0x18000F5DA)` | 2 | read sites, `lea rcx` @ `0x18000DF5C` → table A slot 30, @ `0x18000EF7F` → slot 32 | 2 |
| **136** | `[0x180010810, 0x180010F77)` | **34** | **filler** | 0 |
| 230 | `[0x180019880, 0x180019A1C)` | 1 | read site, `lea r9` @ `0x1800199C5` → table A slot 33 | 0 |
| 327 | `[0x18001DBE0, 0x18001DD7C)` | 1 | read site, `lea r9` @ `0x18001DD25` → table A slot 33 | 0 |
| **332** | `[0x18001E090, 0x18001E9FF)` | 4 | **reader** | 4 |
| **334** | `[0x18001F740, 0x180022232)` | 13 | **reader** | 12 |
| 351 | `[0x180022FD0, 0x18002302D)` | 1 | the 27th same-template instance, pointing to its own slot `0x180058A48` | 1 |
| **359** | `[0x180023C40, 0x18002444B)` | 7 | **reader** | 1 |
| **361** | `[0x1800244B0, 0x1800250CA)` | 11 | **reader** | 6 |
| 365–368 | the 28th–31st same-template instances | 1 each (4 total) | pointing to their own slots `0x180058A50/A58/A60/A68` | 1 each |
| 369 | `[0x1800256D0, 0x18002586C)` | 1 | read site, `lea r9` @ `0x180025815` → table A slot 33 | 0 |
| **Total** | — | **110** | full table A caliber | — |

**Caliber discipline (both calibers must be recomputable)**:

| Caliber | Definition | Result |
|---|---|---|
| narrow caliber | table A slots 0–25 window `[0x180056170, 0x180056250)` ∪ table B slots 0–4 window `[0x180058A40, 0x180058A80)` | **97** |
| **wide caliber** | full table A window `[0x180056170, 0x1800562E0)` (items 0–45) ∪ table B window `[0x180058A48, 0x180058A88)` (items 0–7) | **110** |

The difference **13** = idx 136's **+3** (three registration sites → table A slots 30/31/32) plus **+10** from idx 26/27/28/64/96/122 (×2)/230/327/369.

**Table access shape**: all 110 are **`lea reg, [slot address]` (taking the address), not `mov reg, [slot]` (taking the value)** — `lea` = **110**, `mov` / `cmp` / others = **0**.

⇒ The precise boundary of "whether the handle value in the slot is passed as a `hipLaunchKernel` argument" is therefore: **passing the address is proven, passing the value is not proven**.

Example: idx 332's `lea rcx, [0x180056228]` @ `0x18001E32F` and its subsequent `call 0x180055A70` @ `0x18001E341` are `0x12` bytes apart.

---

## 6. The kernel Registration Mechanism

### 6.1 The Complete Pairing of the 34 Registration Calls and Slots

| # | Registration `call` VA | Slot (`rdx`) | kernel name (ASCII pointed to by `r8`, C++ mangled name) |
|---|---|---|---|
| 1 | `0x18001086E` | `0x180056170` | `_Z16k_swin_1h_32_fp810SwinParams` |
| 2 | `0x1800108A2` | `0x180056178` | `_Z21k_pre_block_1h_32_fp89PreParams` |
| 3 | `0x1800108D6` | `0x180056180` | `_Z22k_post_block_1h_32_fp810PostParams` |
| 4 | `0x18001090A` | `0x180056188` | `_Z6k_ffwd10FfwdParams` |
| 5 | `0x18001093E` | `0x180056190` | `_Z10k_conv_res10ConvParams` |
| 6 | `0x180010972` | `0x180056198` | `_Z10k_qkv_attn10AttnParams` |
| 7 | `0x1800109A6` | `0x1800561A0` | `_Z7k_ffwd211Ffwd2Params` |
| 8 | `0x1800109DA` | `0x1800561A8` | `_Z11k_conv_res211Conv2Params` |
| 9 | `0x180010A0E` | `0x1800561B0` | `_Z11k_qkv_attn210AttnParams` |
| 10 | `0x180010A42` | `0x1800561B8` | `_Z8k_expand12ExpandParams` |
| 11 | `0x180010A76` | `0x1800561C0` | `_Z13k_conv_splitk12ConvParams1d` |
| 12 | `0x180010AAA` | `0x1800561C8` | `_Z5k_qkv9QkvParams` |
| 13 | `0x180010ADE` | `0x1800561D0` | `_Z11k_attention12AttnParams1d` |
| 14 | `0x180010B12` | `0x1800561D8` | `_Z9k_expand212ExpandParams` |
| 15 | `0x180010B46` | `0x1800561E0` | `_Z11k_contract212ConvParams1d` |
| 16 | `0x180010B7A` | `0x1800561E8` | `_Z6k_qkv29QkvParams` |
| 17 | `0x180010BAE` | `0x1800561F0` | `_Z12k_attention212AttnParams1d` |
| 18 | `0x180010BE2` | `0x1800561F8` | `_Z14k_ffwd_inpview12FfwdPlParams` |
| 19 | `0x180010C16` | `0x180056200` | `_Z16k_conv_res_views12ConvPlParams` |
| 20 | `0x180010C4A` | `0x180056208` | `_Z12k_final_head10HeadParams` |
| 21 | `0x180010C7E` | `0x180056210` | `_Z8k_repack12RepackParams` |
| 22 | `0x180010CB2` | `0x180056218` | `_Z14k_dec_upsample11DecUpParams` |
| 23 | `0x180010CE6` | `0x180056220` | `_Z6k_mean10MeanParams` |
| 24 | `0x180010D1A` | `0x180056228` | `_Z8k_import12ImportParams` |
| 25 | `0x180010D4E` | `0x180056230` | `_Z8k_export12ExportParams` |
| 26 | `0x180010D82` | `0x180056238` | `_Z11k_reproject12ReprojParams` |
| 27 | `0x180010DB6` | `0x180056260` (table A slot 30) | `_Z11k_flag_waitPjjj` |
| 28 | `0x180010DEA` | `0x180056268` (table A slot 31) | `_Z13k_align_probePh` |
| 29 | `0x180010E1E` | `0x180056270` (table A slot 32) | `_Z10k_flag_setPjj` |
| 30 | `0x180010E52` | `0x180058A48` | `_Z10k_swin_varILi32ELb1EEv9VarParams` |
| 31 | `0x180010E86` | `0x180058A50` | `_Z10k_swin_varILi32ELb0EEv9VarParams` |
| 32 | `0x180010EBA` | `0x180058A58` | `_Z10k_swin_varILi64ELb0EEv9VarParams` |
| 33 | `0x180010EEE` | `0x180058A60` | `_Z10k_swin_varILi128ELb0EEv9VarParams` |
| 34 | `0x180010F22` | `0x180058A68` | `_Z10k_swin_varILi256ELb0EEv9VarParams` |

**Collision**: the names of the 34 pairing sites **34/34** all fall among the 34 names of the `.hip_fat` metadata ⇒ **34 = 29 (table A: slots 0–25 + 30–32) + 5 (table B: slots 0–4) = 34/34 full coverage**.

### 6.2 The Static Boundary Reached

> **kernel name ↔ wrapper function ↔ handle table slot is 34/34 statically closed.**

Three supports: 34 `lea rdx` pairing chains at 34/34 + 34 `lea r8` name arguments + the self-referential slots `lea rcx` of the 3 auxiliary wrappers.

### 6.3 The wrapper Structure Template

**31 same-template instances** = W1..W26 (`.pdata` idx 0–25) + idx 351 / 365 / 366 / 367 / 368.

Structure (starting `push rsi ; push rdi ; sub rsp,0x68`):

```
push rsi ; push rdi ; sub rsp,0x68 ; mov [rsp+0x30],rcx   ; save the 1st argument
lea rsi,[rsp+0x58] ; lea rdi,[rsp+0x48] ; lea r8,[rsp+0x40] ; lea r9,[rsp+0x38]
mov rcx,rsi ; mov rdx,rdi
call 0x180055930            ; +0x25  __hipPopCallConfiguration (obtain the kernel launch configuration)
mov rax,[rsp+0x40] ; mov rcx,[rsp+0x38] ; mov [rsp+0x28],rcx ; mov [rsp+0x20],rax
lea rcx,[rip+disp]          ; +0x3E  points to the handle table entry (kernel handle slot)
call 0x180055A70            ; +0x50  hipLaunchKernel
add rsp,0x68 ; pop rdi ; pop rsi ; ret
```

**Byte-by-byte evidence** (W1 = `0x180001000`, file `0x400`, first 12 bytes `56 57 48 83 EC 68 48 89 4C 24 30`):

| Offset | VA | Raw bytes | Target |
|---|---|---|---|
| `+0x25` | `0x180001025` | `E8 06 49 05 00` | `0x180055930` (26/26 hits) |
| `+0x3E` | `0x18000103E` | `48 8D 0D 2B 51 05 00` | `0x180056170` (table A slot 0) |
| `+0x50` | `0x180001050` | `E8 1B 4A 05 00` | `0x180055A70` |

- the `.pdata` segment length of each of W1–W26 is `0x5D` (93 bytes), and within the segment the `hipLaunchKernel` call appears exactly **1** time (`+0x50`);
- after zeroing the three `disp32` values, the SHA256 dedup count of the 31 same-template instances = **1** (i.e. 31 instances of the same code).

**`lea rcx` examples for W2 / W26**: W2 `48 8D 0D D3 50 05 00`; W26 `48 8D 0D 93 48 05 00`.

### 6.4 The 60 Call Sites of `hipLaunchKernel`

The number of sites in the whole `.text` whose direct `call` target is `0x180055A70` is exactly **60** (minimum VA `0x180001050`, maximum VA `0x1800256C0`).

**The correct layering of the containing functions**:

> **60 = 31 same-template instances (idx 0–25 + idx 351/365/366/367/368) of "length 93 (`0x5D`) + a single `hipLaunchKernel` call site at `+0x50`" + 29 sites distributed across 9 non-same-template functions, covering 31 + 9 = 40 functions in total.**

The complete address list of the 60 call sites:

```
0x180001050 0x1800010B0 0x180001110 0x180001170 0x1800011D0 0x180001230
0x180001290 0x1800012F0 0x180001350 0x1800013B0 0x180001410 0x180001470
0x1800014D0 0x180001530 0x180001590 0x1800015F0 0x180001650 0x1800016B0
0x180001710 0x180001770 0x1800017D0 0x180001830 0x180001890 0x1800018F0
0x180001950 0x1800019B0 0x180001B5A 0x180001BCA 0x180001C4B 0x1800096AF
0x18000DF6D 0x18000EF9A 0x18001E341 0x18001E568 0x18001E675 0x18001E9DF
0x18001FE2E 0x18002089F 0x1800209FA 0x180020B60 0x180020C7B 0x180020D68
0x180020E55 0x180020F70 0x180021166 0x18002129F 0x180021BEF 0x180021D66
0x180023020 0x180024431 0x18002475C 0x18002489D 0x1800249AC 0x180024CAE
0x180024F4B 0x180025066 0x1800255A0 0x180025600 0x180025660 0x1800256C0
```

**One abandoned statement**: "all 60 `hipLaunchKernel` call sites are inside W1..W26 wrapper bodies".

- the original text of the source material only wrote `Found 60 callers` and listed the first 10 addresses (`0x180001050`–`0x1800013B0`), and **never asserted the containing functions**;
- determining the containing function of each site one by one, using all 1167 `RUNTIME_FUNCTION` entries of `.pdata` as the closed set of function boundaries, gives the layering in the table above.

**Another note**: within the export stub region `0x1800019D0`–`0x180001AE0` the number of `hipLaunchKernel` call sites = **0**; `0x1800019B0` is the `+0x50` call site of W26 (`.pdata` `0x180001960`–`0x1800019BD`).

### 6.5 The Initialization Chain

The wrapper body `0x180001EB0` (an independent `.pdata` function, entry `55 41 57 41 56 41 55 41 54 56 57 53 48 81 EC A8 02 00 00`) has exactly **2** direct callers: `0x18002CF29`, `0x18002CF45`.

---

## 7. Open Question: The Enumeration Semantics of the `71 block`

### 7.1 The Shape of the Problem

The network structure's topology constants are defined in the **workspace source** (`NUM_BLOCKS = 71`, `ENCODER_END = 22`, `BOTTLENECK_START = 23`, `BOTTLENECK_END = 47`, `DECODER_START = 48`), and the weight file's entry names also cover `block0` … `block70`, **71 blocks with no missing number**.

But these constants **only define the topology**; they do not define "which kernel a given block calls".

### 7.2 block Renumbering Semantics (settled)

Inside `.text` there are comparisons with the **same signature** (`cmp r32, 0x1A`, encodings `83 F8 1A` / `83 F9 1A` / `83 FA 1A`), **6** in total. Of them, **4 are inline copies of the block renumbering**:

| # | VA | RVA | file | reg | Owning `.pdata` (idx / Start–End / len) | Where the mapping result is written |
|---|---|---|---|---|---|---|
| 1 | `0x18000B06B` | `0xB06B` | `0xA46B` | eax | 108 / `0x18000A0B0–0x18000C3E0` / 9008 | `mov [rbp+0x120], eax` (`0x18000B09E`) |
| 2 | `0x18000CD9D` | `0xCD9D` | `0xC19D` | eax | 117 / `0x18000CC30–0x18000D022` / 1010 | `mov [rsp+0xB8], eax` (`0x18000CDD0`) |
| 3 | `0x180013117` | `0x13117` | `0x12517` | edx | 174 / `0x1800130B0–0x180013A6C` / 2492 | `mov [rip+0x63244], eax` → global VA `0x180076394` (`0x18001314A`) |
| 4 | `0x18001A24F` | `0x1A24F` | `0x1964F` | ecx | 238 / `0x18001A220–0x18001A43C` / 540 | `mov [rip+0x5C10C], ecx` → global VA `0x180076394` (`0x18001A282`) |

**Raw bytes of site 3** (VA `0x180013117`, file `0x12517`, 32 bytes):

```
83 FA 1A 7F 11 83 FA 09 74 1D 83 FA 17 75 2A B8 18 00 00 00 EB 1D 83 FA 1B 74 13 83 FA 5A 75 19
```

**Comparison sequence**: `cmp edx,0x1a`(26) → `jg`; `cmp edx,9` → `je`; `cmp edx,0x17`(23) → `jne`; `mov eax,0x18`; `cmp edx,0x1b`(27) → `je`; `cmp edx,0x5a`(90) → `jne`.

**Semantics settled: these 4 are "renumbering", not "index testing"**:

| Input | Output |
|---|---|
| `9` | `0x0A` (10) |
| `0x17` (23) | `0x18` (24) |
| `0x1B` (27) | `0x1C` (28) |
| `0x5A` (90) | `0x57` (87) |
| all other values (**including `0x1A` = 26**) | **kept unchanged** |

The four sites' branch orders differ pairwise (sites 1/2 test `0x5A` before `0x1B`; sites 3/4 test `0x1B` before `0x5A`), but the branch semantics are exactly the same; this is **one function inlined four times**.

⇒ The early statement "the determined block values are only 5: 9, 23, 26, 27, 90" must therefore be rewritten semantically as:

> **`26` is only the comparison bound of the `jg` and is not renumbered; the four that are actually specially tested and renumbered are 9 / 23 / 27 / 90.**

**Branch targets (site 3)**: `jg` → `0x18001312D`; `je` → `0x18001313E`; `jne` → `0x180013150`; `jmp` → `0x18001314A`; all three paths ultimately call `0x1800152A0` (a setup function, legitimate function entry `41 57 41 56 41 55 41 54 56 57 55 53 48 81 EC E8 00 00 00`, looping 96 times over `cmp r12d,0x5f`).

**The call sequence of the two renumbering functions: "store the original value first, then store the renumbered result"**:

| Site | Sequence |
|---|---|
| 3 | `0x18001310B` (original value → `0x180076398`), `0x180013111` (`mov [rip+0x6327D],edx` → `0x180076394`) → renumber → `0x18001314A` (result → `0x180076394`) |
| 4 | `0x18001A249` (original value → `0x180076398`) → renumber → `0x18001A282` (result → `0x180076394`) |

**The `dispatcher` (idx 167) does not write these two globals** — the write sites belong to three different functions, idx 174 / 238 / 135 (`0x180076394` 4 sites, `0x180076398` 2 sites, **6** in total).

### 7.3 The Other 2 Sites with the Same Signature Encoding

`83 FA 1A` appears exactly **2** times in the whole file: `0x180013117` and `0x180048ECC` (file `0x482CC`). `83 F9 1A` and `83 F8 1A` likewise appear **2** times each.

The distribution of the 6 sites is: 4 inline copies of the renumbering (`.pdata` idx 108 / 117 / 174 / 238), and the other 2 are:

| VA | `.pdata` idx | Raw bytes |
|---|---|---|
| `0x180048A44` | 949 | `83 F9 1A 74` |
| `0x180048ECC` | 951 | `83 FA 1A 0F` |

**The semantics of these 2 sites are undetermined** (this project does not claim they are renumbering copies).

### 7.4 dispatcher Structure

| Item | Value |
|---|---|
| Entry | `0x180012380` |
| `.pdata` | idx 167 / `0x180012380–0x180012D26` / length **2470** |
| Entry bytes (file `0x11780`) | `55 41 57 41 56 41 55 41 54 56 57 53 48 81 ec 28 03 00 00 48 8d ac 24 80 00 00 00` |
| Disassembly | `push rbp; push r15; push r14; push r13; push r12; push rsi; push rdi; push rbx; sub rsp,0x328; lea rbp,[rsp+0x80]` |
| **38 `call`s / 19 distinct targets** | see below |
| Whether it calls `hipLaunchKernel` or a wrapper | **no** |

**The 19 targets of the 38 `call`s (with counts)**:

| Target | Count |
|---|---|
| `0x18002C354` | **7** |
| `0x180054370` | **6** |
| `0x18002C390` | **5** |
| `0x180015720` | **3** |
| `0x180011560` | **2** |
| `0x180054A20` | **2** |
| `0x180039000` / `0x180026750` / `0x180055AB0` / `0x180011780` / `0x18001AB80` / `0x18001D990` / `0x18001DBE0` / `0x180038DA4` / `0x180055A80` / `0x180055A90` / `0x18001DF40` / `0x18001B100` / `0x1800291A0` | **1** each |
| **Sum of counts** | **38** ✅ |

**Cross-check**: within the function body interval `[0x180012380, 0x180012D26)` the raw byte `E8` gets **48** hits = a **superset** of the 38 `call`s parsed by instruction boundary; the difference set of 10 non-call-start sites (`0x18001258F`, `0x18001260A`, `0x1800126D2`, `0x180012797`, `0x180012834`, `0x180012879`, `0x180012997`, `0x180012AC5`, `0x180012D13`, `0x180012D22`) all fall inside existing instructions (they do not constitute new calls).

**Thunk targets contained in the dispatcher**: `hipMemcpyToSymbol` (`0x180055AB0` → IAT `0x18006BD28`), `hipMalloc` (`0x180055A80` → IAT `0x18006BD10`), `hipMemcpy` (`0x180055A90` → IAT `0x18006BD18`), `hipMemcpyAsync` (`0x180055AA0` → IAT `0x18006BD20`).

**Other structure**:

- the stack frame saves xmm6–xmm15; floating-point constants are loaded from `[rip+disp]` (`0x43c0d`, `0x4562c`, `0x45633`, `0x4558e`, `0x45612`);
- loop structure (`+0x160`–`+0x187`): `movdqa xmm0,xmm8; pextrw eax,xmm0,0; mov [rbp+rsi*2-0x50],ax; inc rsi; cmp rsi,0x100`;
- magic detection: `movabs rax, 0x3157524e53534c44` (little-endian = ASCII `DLSSNRW1`), byte string `48 B8 44 4C 53 53 4E 52 57 31`, **unique in the whole file**, paired with `cmp qword ptr [r15],rax; jne`.

**Settled: which VA the magic refers to**: the byte string is inside the `movabs` instruction at file `0x119A2` — `48 B8` is the **instruction start** (VA `0x1800125A2`), and the immediate is `44 4C 53 53 4E 52 57 31` (**immediate start** VA `0x1800125A4`, file `0x119A4`). The two annotations refer respectively to that instruction's instruction start and its immediate start; this is **not a reading conflict**.

### 7.5 Three Repeatedly Mis-Labeled Addresses

| Mis-labeled address | Byte evidence | True function entry |
|---|---|---|
| `0x1800124B0` | `0x1800124AE` = `48 8D 55 B0` = `lea rdx,[rbp-0x50]`; that 4-byte instruction spans `0x1800124AE–0x1800124B1`, and `0x55` is exactly the ModRM (mod=01, reg=010=rdx, rm=101=rbp+disp8); `0x1800124B0` lies at the `+0x130`th byte of the function `0x180012380–0x180012D26`; in the whole `.text` the number of `E8`/`E9` pointing to it = 0 and of `0F 8x` conditional jumps = 0 | **`0x180012380`** (`.pdata` length 2470) |
| `0x1800120B0` | first 16 bytes = `55 55 55 55 55 05 48 39 47 08 74 5F B9 30 00 00 00` (5 consecutive `0x55`, not an instruction boundary); falls at the `+0x80` of the `.pdata` segment `0x180012030–0x180012121` | **`0x180012030`** (`.pdata` length `0xF1`) |
| `0x180012EBC` | bytes `E4 B2 01 00 CC 66 66 66` (the trailing `CC` is inter-function padding); the `.pdata` entry is `0x180012E70–0x180012EC1` (length `0x51`) | **`0x180012E70`** |

### 7.6 The `.pdata` Lengths of Four Functions

| Function entry | `.pdata` interval | Length |
|---|---|---|
| `0x180012380` (the dispatcher body) | `0x180012380–0x180012D26` | 2470 bytes |
| `0x180011780` (auxiliary function 1) | `0x180011780–0x18001182C` | 172 bytes |
| `0x18001AB80` (auxiliary function 2) | `0x18001AB80–0x18001AE32` | 690 bytes |
| `0x18001D990` (auxiliary function 3) | `0x18001D990–0x18001DAB6` | 294 bytes |

None of the three auxiliary functions contains a call to `0x180055A70`.

### 7.7 Why the `71 block` Question Stops Here

The block-level scheduling logic inside `.text` **could not be located**; the boundary conditions established (see `06-未解缺口与限制.md` (in Chinese) §2 for details):

| # | Boundary condition | Measured |
|---|---|---|
| ① | comparisons of this signature within the dispatcher function body `[0x180012380, 0x180012D26)` | **0 hits** |
| ② | total instruction count under the caliber "linear disassembly of each of the 1167 `.pdata` function bodies" | **82,170** instructions (a single linear disassembly of the whole `.text` gives only 76,661; the last instruction is interrupted by non-code bytes after `0x180049EBE`) |
| ③ | immediates `70` / `71` / `72` within that set | **91** hits (`0x48`=72, 85 of them; `0x46`=70, 4; `0x47`=71, 2), **none of which is a block index comparison**; 55 of them are of the `sub`/`add rsp,0x48` stack-adjustment shape and 36 are of the non-stack-adjustment shape |
| ④ | location of the dispatch points | only inside the 4 renumbering functions, and **all outside the dispatcher** |
| ⑤ | dispatcher's 38 `call` targets ∩ the 14 function entries containing `hipLaunchKernel` | **= 0** |
| ⑥ | where the renumbering result is written | only into BSS-type globals (`0x180076394` / `0x180076398`, **no file initial value**); statically there are only write sites, no initial-value table |
| ⑦ | the 3 read sites | they write the value into a write-only stack-frame field and then hand it to a virtual call (the vtable is filled at runtime) |
| ⑧ | the 34 wrapper entries (31 same-template instances + 3 auxiliary wrappers) | **no direct `E8` call** (they are called indirectly through the handle table) |
| ⑨ | compatibility | the input set contains `0x5A = 90` and the output set contains `0x57 = 87`, **both > 70**, **incompatible** with "block indices 0–70" |

⇒ **The dispatch binding between the `71 block` and the 34 kernels cannot be obtained from the static bytes of this DLL.** See `06-未解缺口与限制.md` (in Chinese) for details.
