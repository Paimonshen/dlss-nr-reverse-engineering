# Kernel Parameter Specification

This document gives the parameter and resource specifications for the **34 kernels** inside the `.hip_fat` metadata. These specifications are a **reference baseline** for recompiling the kernels on the Intel platform; they are not a loadable binary.

## 0. Scope and Conventions

### 0.1 What This Document Is and Is Not

- **This document is a "recompilation reference baseline"**: the 8 device bundles can only be used to read the parameter and resource metadata on the AMDGPU side, as specification input when recompiling the kernels on the Intel platform.
- **This document does not describe host-side runtime replacement**: the host side (proxy exports, thunks, wrappers, handle table, launch chain) is covered in `03-DLL-Structure-Analysis.md`.
- **This fat binary contains no Intel / Xe / SPIR-V target whatsoever** (in the full set of triples across the 9 bundle entries there is no `spirv`, no `intel`, no `xe`).

### 0.2 Numbering and Coordinate Conventions (consistent throughout)

| Item | Convention |
|---|---|
| **bundle numbering** | `entry#0` = host placeholder; `device#1..#8` = the 8 devices (`#8` is always `gfx9-generic`) |
| **baseline table taken from** | `device#1` (`gfx10-3-generic`) — the parameter surface of the 8 devices is identical item by item (see the final note of §2.2), so a single table can represent all 8 targets |
| **VA conversion** | `.hip_fat` section VA = `0x18007F000`, RAW = `0x78200` → `file = VA − 0x18007F000 + 0x78200` |
| **msgpack document start** | `bundle + 0x24C` |

Derivation of `bundle + 0x24C`: the `.note` section has `sh_offset = +0x238`; note header `namesz` @ `+0x238`, `descsz` @ `+0x23C`, `type` @ `+0x240` = **32** = `NT_AMDGPU_METADATA`, name `AMDGPU` @ `+0x244`; hence desc start = `0x238 + 12 + 8 = 0x24C`.

### 0.3 Coordinate Table of the 9 Bundle Entries

| Entry | triple | offset (in section) | size | file range | `.note` sh_size | descsz | msgpack document start (file / VA) |
|---|---|---|---|---|---|---|---|
| `#0` | `host-x86_64-unknown-linux-gnu-` | `0x1000` | **`0x0`** (placeholder, empty range) | `[0x79200, 0x79200)` | — (no entity) | — | — |
| `#1` | `hipv4-amdgcn-amd-amdhsa--gfx10-3-generic` | `0x1000` | `0x89728` | `[0x79200, 0x102928)` | `0x8B88` | `0x8B72` | `0x7944C` / `0x18008024C` |
| `#2` | `hipv4-amdgcn-amd-amdhsa--gfx11-generic` | `0x8B000` | `0x11E0A0` | `[0x103200, 0x2212A0)` | `0x8B98` | `0x8B84` | `0x10344C` / `0x18010A24C` |
| `#3` | `hipv4-amdgcn-amd-amdhsa--gfx1100` | `0x1AA000` | `0x11C068` | `[0x222200, 0x33E268)` | `0x8B90` | `0x8B7C` | `0x22244C` / `0x18022924C` |
| `#4` | `hipv4-amdgcn-amd-amdhsa--gfx1101` | `0x2C7000` | `0x11C068` | `[0x33F200, 0x45B268)` | `0x8B90` | `0x8B7C` | `0x33F44C` / `0x18034624C` |
| `#5` | `hipv4-amdgcn-amd-amdhsa--gfx1102` | `0x3E4000` | `0x11E0A0` | `[0x45C200, 0x57A2A0)` | `0x8B94` | `0x8B7D` | `0x45C44C` / `0x18046324C` |
| `#6` | `hipv4-amdgcn-amd-amdhsa--gfx1200` | `0x503000` | `0x67B88` | `[0x57B200, 0x5E2D88)` | `0x8B8C` | `0x8B78` | `0x57B44C` / `0x18058224C` |
| `#7` | `hipv4-amdgcn-amd-amdhsa--gfx1201` | `0x56B000` | `0x67B88` | `[0x5E3200, 0x64AD88)` | `0x8B8C` | `0x8B78` | `0x5E344C` / `0x1805EA24C` |
| `#8` | `hipv4-amdgcn-amd-amdhsa--gfx9-generic` | `0x5D3000` | `0x844A8` | `[0x64B200, 0x6CF6A8)` | `0x87F0` | `0x87DA` | `0x64B44C` / `0x18065224C` |

**The `.hip_fat` section**: VA `0x18007F000`, RVA `0x7F000`, RAW `0x78200`, magic `__CLANG_OFFLOAD_BUNDLE__` (**unique in the whole file**); `numBundles` = 9.

**One correction**: `descsz` deduplicated across bundles gives **6 distinct values** (`0x8B72` / `0x8B84` / `0x8B7C` / `0x8B7C` / `0x8B7D` / `0x8B78` / `0x8B78` / `0x87DA`), **max − min = 938** (`0x3AA`). The "1,410 bytes" recorded in earlier material was an arithmetic error. The consequence of this fact is: **one must not assume the metadata of the 8 targets is byte-identical**; cross-target consistency must be established item by item.

### 0.4 Totals

| Item | Value |
|---|---|
| 8 targets × 34 kernels | **272 kernel entries** |
| parameters per target | **440** (3,520 ÷ 8) |
| total parameters across the whole library | **3,520** |

---

## 1. Parameter Surface

### 1.1 Fields and Semantics of Parameter Entries

`.args` is the parameter array inside each kernel map. Each parameter is a map; two key sets were measured:

| Key set | Count |
|---|---|
| `{.offset, .size, .value_kind}` | **3,496** |
| `{.address_space, .offset, .size, .value_kind}` | **24** |

That is, of the 3,520 parameters in the whole library, **only these 24** `global_buffer` parameters carry `.address_space`, whose measured value is the string `"global"`, raw bytes `A6 67 6C 6F 62 61 6C`.

- `.offset`: the byte offset of that parameter within the kernarg segment;
- `.size`: byte length;
- `.value_kind`: the parameter category string.

Each kernel entry additionally carries `.kernarg_segment_size` (total kernarg segment length).

### 1.2 The 34-Row Baseline Table

Kernel names are verbatim as in the metadata (C++ mangled names). Parameter items are written `offset/size/value_kind`, separated by `;`.

| # | kernel name (`.name`, mangled) | `.kernarg_segment_size` | `.args` count | per-parameter (`.offset`/`.size`/`.value_kind`) |
|---|---|---|---|---|
| 0 | `_Z16k_swin_1h_32_fp810SwinParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 1 | `_Z21k_pre_block_1h_32_fp89PreParams` | 336 | 14 | `0/80/by_value`; `80/4/hidden_block_count_x`; `84/4/hidden_block_count_y`; `88/4/hidden_block_count_z`; `92/2/hidden_group_size_x`; `94/2/hidden_group_size_y`; `96/2/hidden_group_size_z`; `98/2/hidden_remainder_x`; `100/2/hidden_remainder_y`; `102/2/hidden_remainder_z`; `120/8/hidden_global_offset_x`; `128/8/hidden_global_offset_y`; `136/8/hidden_global_offset_z`; `144/2/hidden_grid_dims` |
| 2 | `_Z22k_post_block_1h_32_fp810PostParams` | 336 | 14 | `0/80/by_value`; `80/4/hidden_block_count_x`; `84/4/hidden_block_count_y`; `88/4/hidden_block_count_z`; `92/2/hidden_group_size_x`; `94/2/hidden_group_size_y`; `96/2/hidden_group_size_z`; `98/2/hidden_remainder_x`; `100/2/hidden_remainder_y`; `102/2/hidden_remainder_z`; `120/8/hidden_global_offset_x`; `128/8/hidden_global_offset_y`; `136/8/hidden_global_offset_z`; `144/2/hidden_grid_dims` |
| 3 | `_Z6k_ffwd10FfwdParams` | 288 | 14 | `0/32/by_value`; `32/4/hidden_block_count_x`; `36/4/hidden_block_count_y`; `40/4/hidden_block_count_z`; `44/2/hidden_group_size_x`; `46/2/hidden_group_size_y`; `48/2/hidden_group_size_z`; `50/2/hidden_remainder_x`; `52/2/hidden_remainder_y`; `54/2/hidden_remainder_z`; `72/8/hidden_global_offset_x`; `80/8/hidden_global_offset_y`; `88/8/hidden_global_offset_z`; `96/2/hidden_grid_dims` |
| 4 | `_Z10k_conv_res10ConvParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 5 | `_Z10k_qkv_attn10AttnParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 6 | `_Z7k_ffwd211Ffwd2Params` | 304 | 14 | `0/48/by_value`; `48/4/hidden_block_count_x`; `52/4/hidden_block_count_y`; `56/4/hidden_block_count_z`; `60/2/hidden_group_size_x`; `62/2/hidden_group_size_y`; `64/2/hidden_group_size_z`; `66/2/hidden_remainder_x`; `68/2/hidden_remainder_y`; `70/2/hidden_remainder_z`; `88/8/hidden_global_offset_x`; `96/8/hidden_global_offset_y`; `104/8/hidden_global_offset_z`; `112/2/hidden_grid_dims` |
| 7 | `_Z11k_conv_res211Conv2Params` | 320 | 14 | `0/64/by_value`; `64/4/hidden_block_count_x`; `68/4/hidden_block_count_y`; `72/4/hidden_block_count_z`; `76/2/hidden_group_size_x`; `78/2/hidden_group_size_y`; `80/2/hidden_group_size_z`; `82/2/hidden_remainder_x`; `84/2/hidden_remainder_y`; `86/2/hidden_remainder_z`; `104/8/hidden_global_offset_x`; `112/8/hidden_global_offset_y`; `120/8/hidden_global_offset_z`; `128/2/hidden_grid_dims` |
| 8 | `_Z11k_qkv_attn210AttnParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 9 | `_Z8k_expand12ExpandParams` | 280 | 14 | `0/24/by_value`; `24/4/hidden_block_count_x`; `28/4/hidden_block_count_y`; `32/4/hidden_block_count_z`; `36/2/hidden_group_size_x`; `38/2/hidden_group_size_y`; `40/2/hidden_group_size_z`; `42/2/hidden_remainder_x`; `44/2/hidden_remainder_y`; `46/2/hidden_remainder_z`; `64/8/hidden_global_offset_x`; `72/8/hidden_global_offset_y`; `80/8/hidden_global_offset_z`; `88/2/hidden_grid_dims` |
| 10 | `_Z13k_conv_splitk12ConvParams1d` | 304 | 14 | `0/48/by_value`; `48/4/hidden_block_count_x`; `52/4/hidden_block_count_y`; `56/4/hidden_block_count_z`; `60/2/hidden_group_size_x`; `62/2/hidden_group_size_y`; `64/2/hidden_group_size_z`; `66/2/hidden_remainder_x`; `68/2/hidden_remainder_y`; `70/2/hidden_remainder_z`; `88/8/hidden_global_offset_x`; `96/8/hidden_global_offset_y`; `104/8/hidden_global_offset_z`; `112/2/hidden_grid_dims` |
| 11 | `_Z5k_qkv9QkvParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 12 | `_Z11k_attention12AttnParams1d` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 13 | `_Z9k_expand212ExpandParams` | 280 | 14 | `0/24/by_value`; `24/4/hidden_block_count_x`; `28/4/hidden_block_count_y`; `32/4/hidden_block_count_z`; `36/2/hidden_group_size_x`; `38/2/hidden_group_size_y`; `40/2/hidden_group_size_z`; `42/2/hidden_remainder_x`; `44/2/hidden_remainder_y`; `46/2/hidden_remainder_z`; `64/8/hidden_global_offset_x`; `72/8/hidden_global_offset_y`; `80/8/hidden_global_offset_z`; `88/2/hidden_grid_dims` |
| 14 | `_Z11k_contract212ConvParams1d` | 304 | 14 | `0/48/by_value`; `48/4/hidden_block_count_x`; `52/4/hidden_block_count_y`; `56/4/hidden_block_count_z`; `60/2/hidden_group_size_x`; `62/2/hidden_group_size_y`; `64/2/hidden_group_size_z`; `66/2/hidden_remainder_x`; `68/2/hidden_remainder_y`; `70/2/hidden_remainder_z`; `88/8/hidden_global_offset_x`; `96/8/hidden_global_offset_y`; `104/8/hidden_global_offset_z`; `112/2/hidden_grid_dims` |
| 15 | `_Z6k_qkv29QkvParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 16 | `_Z12k_attention212AttnParams1d` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 17 | `_Z14k_ffwd_inpview12FfwdPlParams` | 288 | 14 | `0/32/by_value`; `32/4/hidden_block_count_x`; `36/4/hidden_block_count_y`; `40/4/hidden_block_count_z`; `44/2/hidden_group_size_x`; `46/2/hidden_group_size_y`; `48/2/hidden_group_size_z`; `50/2/hidden_remainder_x`; `52/2/hidden_remainder_y`; `54/2/hidden_remainder_z`; `72/8/hidden_global_offset_x`; `80/8/hidden_global_offset_y`; `88/8/hidden_global_offset_z`; `96/2/hidden_grid_dims` |
| 18 | `_Z16k_conv_res_views12ConvPlParams` | 328 | 14 | `0/72/by_value`; `72/4/hidden_block_count_x`; `76/4/hidden_block_count_y`; `80/4/hidden_block_count_z`; `84/2/hidden_group_size_x`; `86/2/hidden_group_size_y`; `88/2/hidden_group_size_z`; `90/2/hidden_remainder_x`; `92/2/hidden_remainder_y`; `94/2/hidden_remainder_z`; `112/8/hidden_global_offset_x`; `120/8/hidden_global_offset_y`; `128/8/hidden_global_offset_z`; `136/2/hidden_grid_dims` |
| 19 | `_Z12k_final_head10HeadParams` | 280 | 14 | `0/24/by_value`; `24/4/hidden_block_count_x`; `28/4/hidden_block_count_y`; `32/4/hidden_block_count_z`; `36/2/hidden_group_size_x`; `38/2/hidden_group_size_y`; `40/2/hidden_group_size_z`; `42/2/hidden_remainder_x`; `44/2/hidden_remainder_y`; `46/2/hidden_remainder_z`; `64/8/hidden_global_offset_x`; `72/8/hidden_global_offset_y`; `80/8/hidden_global_offset_z`; `88/2/hidden_grid_dims` |
| 20 | `_Z8k_repack12RepackParams` | 288 | 14 | `0/32/by_value`; `32/4/hidden_block_count_x`; `36/4/hidden_block_count_y`; `40/4/hidden_block_count_z`; `44/2/hidden_group_size_x`; `46/2/hidden_group_size_y`; `48/2/hidden_group_size_z`; `50/2/hidden_remainder_x`; `52/2/hidden_remainder_y`; `54/2/hidden_remainder_z`; `72/8/hidden_global_offset_x`; `80/8/hidden_global_offset_y`; `88/8/hidden_global_offset_z`; `96/2/hidden_grid_dims` |
| 21 | `_Z14k_dec_upsample11DecUpParams` | 296 | 14 | `0/40/by_value`; `40/4/hidden_block_count_x`; `44/4/hidden_block_count_y`; `48/4/hidden_block_count_z`; `52/2/hidden_group_size_x`; `54/2/hidden_group_size_y`; `56/2/hidden_group_size_z`; `58/2/hidden_remainder_x`; `60/2/hidden_remainder_y`; `62/2/hidden_remainder_z`; `80/8/hidden_global_offset_x`; `88/8/hidden_global_offset_y`; `96/8/hidden_global_offset_z`; `104/2/hidden_grid_dims` |
| 22 | `_Z6k_mean10MeanParams` | 288 | 14 | `0/32/by_value`; `32/4/hidden_block_count_x`; `36/4/hidden_block_count_y`; `40/4/hidden_block_count_z`; `44/2/hidden_group_size_x`; `46/2/hidden_group_size_y`; `48/2/hidden_group_size_z`; `50/2/hidden_remainder_x`; `52/2/hidden_remainder_y`; `54/2/hidden_remainder_z`; `72/8/hidden_global_offset_x`; `80/8/hidden_global_offset_y`; `88/8/hidden_global_offset_z`; `96/2/hidden_grid_dims` |
| 23 | `_Z8k_import12ImportParams` | 304 | 14 | `0/48/by_value`; `48/4/hidden_block_count_x`; `52/4/hidden_block_count_y`; `56/4/hidden_block_count_z`; `60/2/hidden_group_size_x`; `62/2/hidden_group_size_y`; `64/2/hidden_group_size_z`; `66/2/hidden_remainder_x`; `68/2/hidden_remainder_y`; `70/2/hidden_remainder_z`; `88/8/hidden_global_offset_x`; `96/8/hidden_global_offset_y`; `104/8/hidden_global_offset_z`; `112/2/hidden_grid_dims` |
| 24 | `_Z8k_export12ExportParams` | 320 | 14 | `0/64/by_value`; `64/4/hidden_block_count_x`; `68/4/hidden_block_count_y`; `72/4/hidden_block_count_z`; `76/2/hidden_group_size_x`; `78/2/hidden_group_size_y`; `80/2/hidden_group_size_z`; `82/2/hidden_remainder_x`; `84/2/hidden_remainder_y`; `86/2/hidden_remainder_z`; `104/8/hidden_global_offset_x`; `112/8/hidden_global_offset_y`; `120/8/hidden_global_offset_z`; `128/2/hidden_grid_dims` |
| 25 | `_Z11k_reproject12ReprojParams` | **384** | 14 | `0/128/by_value`; `128/4/hidden_block_count_x`; `132/4/hidden_block_count_y`; `136/4/hidden_block_count_z`; `140/2/hidden_group_size_x`; `142/2/hidden_group_size_y`; `144/2/hidden_group_size_z`; `146/2/hidden_remainder_x`; `148/2/hidden_remainder_y`; `150/2/hidden_remainder_z`; `168/8/hidden_global_offset_x`; `176/8/hidden_global_offset_y`; `184/8/hidden_global_offset_z`; `192/2/hidden_grid_dims` |
| 26 | `_Z11k_flag_waitPjjj` | **16** | 3 | `0/8/global_buffer`; `8/4/by_value`; `12/4/by_value` |
| 27 | `_Z13k_align_probePh` | **8** | 1 | `0/8/global_buffer` (**no `by_value` parameter**) |
| 28 | `_Z10k_flag_setPjj` | **12** | 2 | `0/8/global_buffer`; `8/4/by_value` |
| 29 | `_Z10k_swin_varILi32ELb1EEv9VarParams` | 424 | 14 | `0/168/by_value`; `168/4/hidden_block_count_x`; `172/4/hidden_block_count_y`; `176/4/hidden_block_count_z`; `180/2/hidden_group_size_x`; `182/2/hidden_group_size_y`; `184/2/hidden_group_size_z`; `186/2/hidden_remainder_x`; `188/2/hidden_remainder_y`; `190/2/hidden_remainder_z`; `208/8/hidden_global_offset_x`; `216/8/hidden_global_offset_y`; `224/8/hidden_global_offset_z`; `232/2/hidden_grid_dims` |
| 30 | `_Z10k_swin_varILi32ELb0EEv9VarParams` | 424 | 14 | same as #29 (identical field by field) |
| 31 | `_Z10k_swin_varILi64ELb0EEv9VarParams` | 424 | 14 | same as #29 (identical field by field) |
| 32 | `_Z10k_swin_varILi128ELb0EEv9VarParams` | 424 | 14 | same as #29 (identical field by field) |
| 33 | `_Z10k_swin_varILi256ELb0EEv9VarParams` | 424 | 14 | same as #29 (identical field by field) |

**Cross-target consistency (basis for one table representing 8 targets)**: 34 kernels × 7 non-baseline targets = **238/238 judgement cells consistent**; the ordered kernel-name list is **7/7 identical**; the `.args` array byte-level SHA256 is identical **272/272** (12 distinct byte strings); differing entries **0**.

> **Scope limitation (must accompany any citation)**: the cross-target consistency conclusion above **covers only** `.kernarg_segment_size`, the `.args` element count, and the per-parameter `.offset` / `.size` / `.value_kind`. **Resource-class fields have separate cross-target differences**; see §3.3.

### 1.3 The Three Exception Kernels

31 kernels (idx 0–25, 29–33) satisfy the composition identity; **3 exception kernels** have no hidden parameters and no tail, the end of the last parameter == `kernarg_segment_size`, difference +0 (24 records in total = 3 kernels × 8 targets):

| Kernel | `kernarg_segment_size` | Parameter composition | Characteristics |
|---|---|---|---|
| `_Z11k_flag_waitPjjj` | **16** | `0/8/global_buffer` + `8/4/by_value` + `12/4/by_value` | no hidden parameters, no tail |
| `_Z13k_align_probePh` | **8** | `0/8/global_buffer` | no hidden parameters, no tail, and **no `by_value` parameter** |
| `_Z10k_flag_setPjj` | **12** | `0/8/global_buffer` + `8/4/by_value` | no hidden parameters, no tail |

**Citation discipline (`k_align_probe`)**: the wording "**no `by_value` parameter**" must be used; one **must not** write "its `by_value` size is 0".

**Citation discipline (`k_flag_set`)**: its `kernarg_segment_size` = **12**, **not a multiple of 8** (mod 8 = 4) — it is the **only** entry among the 272 whose mod 8 ≠ 0.

### 1.4 Composition Identity: `kernarg = by_value + 66 + 190`

**31 kernels** (idx 0–25, 29–33) were measured to satisfy:

```
.kernarg_segment_size = user by_value parameter size + 66 (13 hidden-parameter span) + 190 (trailing region not enumerated in .args)
```

This formula holds for each of the 31 kernels individually.

**The 66 B hidden-parameter span contains a 16-byte hole** (31 kernels × 8 targets value set = {16}):

| Relative offset (relative to hidden region start = that kernel's `by_value` size B) | Parameter | size |
|---|---|---|
| `+0x00` | `hidden_block_count_x` | 4 |
| `+0x04` | `hidden_block_count_y` | 4 |
| `+0x08` | `hidden_block_count_z` | 4 |
| `+0x0C` | `hidden_group_size_x` | 2 |
| `+0x0E` | `hidden_group_size_y` | 2 |
| `+0x10` | `hidden_group_size_z` | 2 |
| `+0x12` | `hidden_remainder_x` | 2 |
| `+0x14` | `hidden_remainder_y` | 2 |
| `+0x16` | `hidden_remainder_z` | 2 |
| **`+0x18`–`+0x28`** | **hole (16 B, no corresponding `.args` entry)** | **16** |
| `+0x28` | `hidden_global_offset_x` | 8 |
| `+0x30` | `hidden_global_offset_y` | 8 |
| `+0x38` | `hidden_global_offset_z` | 8 |
| `+0x40` | `hidden_grid_dims` | 2 |

The 13 hidden parameters' sizes sum to 4+4+4+2+2+2+2+2+2+8+8+8+2 = **50 B**; plus the **16 B hole** = **66 B**.

**The actual concatenation formula**:

```
Σ(parameter size) + 206 = kernarg      (206 = 50 hidden size + 16 hole + 190 tail)
⇔ Σsize = by_value + 50, kernarg = Σsize + 206
```

Holds for each of the 31 kernels individually.

**The correct way to assemble kernarg from the table**: place the user parameter at `by_value` (offset 0, length = the table's `size/by_value`), then place the 13 hidden parameters at the **absolute offsets** of the table above; when writing, retain both the 16 B at `+0x18`–`+0x28` and the 190 B tail (the 31-kernel case).

### 1.5 `.value_kind` Value Set and Counts (3,520 parameters)

| `.value_kind` | occurrences (out of 3,520) | per-target count | note |
|---|---|---|---|
| `by_value` | 272 | 34 | one per each of the 34 kernel entries (exception: `k_align_probe` has none) |
| `hidden_block_count_x` / `_y` / `_z` | 248 each | 31 each | one per each of the 31 kernels with hidden parameters |
| `hidden_group_size_x` / `_y` / `_z` | 248 each | 31 each | as above |
| `hidden_remainder_x` / `_y` / `_z` | 248 each | 31 each | as above |
| `hidden_global_offset_x` / `_y` / `_z` | 248 each | 31 each | as above |
| `hidden_grid_dims` | 248 | 31 | as above |
| `global_buffer` | **24** | 3 | only `k_flag_wait` / `k_align_probe` / `k_flag_set` (and these 24 are the only parameters in the whole library carrying `.address_space` = `"global"`) |

The value set has **15** members in total; the sum is 272 + 248×13 + 24 = **3,520** ✅.

### 1.6 Three Structural Self-Checks (full 8 targets × 34 kernels)

| Check | Result | Quantitative evidence |
|---|---|---|
| ① `.offset` strictly increasing | **strictly increasing, 0 exceptions** | for every kernel all adjacent parameters have `offset[j+1] > offset[j]`; all 3,248 adjacent pairs pass |
| ② `[offset, offset+size)` pairwise non-overlapping | **no overlap, 0 overlapping pairs** | pairwise interval comparison over all 272 kernels, 0 overlapping pairs |
| ③ relation between the last parameter's `offset+size` and `kernarg_segment_size` | **trailing padding exists (not equality)** | difference `+190` × 248, `+0` × 24 |

**Parse-closure verification (preliminary boundary self-check, passed first)**:

- 8/8 bundles satisfy `e_shoff + e_shnum × e_shentsize == size` (difference 0);
- the identity `0x1000 + Σsize(0x6514F0) + Σgap(0x4FB8) = 0x6574A8` == `.hip_fat` VirtualSize holds;
- the 7 gaps and the section head `+0x230`..`+0x1000` are all zero.

**Locator read-back verification**: 4,080 ranges were read back and compared one by one with a msgpack reference implementation, **0 failures**.

---

## 2. Resource Surface

### 2.1 Fields and Key Sets (bytes are authoritative)

**Union of the kernel map keys across the 8 targets = 18 keys**:

`.args`, `.name`, `.group_segment_fixed_size`, `.private_segment_fixed_size`, `.kernarg_segment_align`, `.kernarg_segment_size`, `.language`, `.language_version`, `.max_flat_workgroup_size`, `.sgpr_count`, `.sgpr_spill_count`, `.symbol`, `.uniform_work_group_size`, `.uses_dynamic_stack`, `.vgpr_count`, `.vgpr_spill_count`, `.wavefront_size`, `.workgroup_processor_mode`

**Key count per target**:

| Target | Key count | Note |
|---|---|---|
| `#1`–`#7` | **18** | the key-name set is identical per target |
| **`#8` `gfx9-generic`** | **17** | **`.workgroup_processor_mode` entirely absent** |

**Raw byte evidence**: map16 header `DE 00 12` (`#1`–`#7`) vs `DE 00 11` (`#8`); the missing key itself gets **0** hits in `#8`.

**Number of field entities other than `.args` / `.name` = 16** (18 keys − `.args` − `.name`). The "16 fields" in this document refers to these 16 field entities.

**Two scope clarifications**:

1. The "device enqueue symbol" key named in an early contract gets **0 hits** across the whole library of 8 targets × 34 kernels —— **that key does not exist in the metadata** and must not be used as an actual field;
2. `.value_kind` **is not a kernel-level field**; it appears only inside parameter maps (one per each of the 3,520 parameters; the kernel map has no such key).

### 2.2 Full Table of the 16 Field Entities

Source scope: 272 kernel entries.

| Field | deduplicated value-set size | frequency summary (over 272 entries) | 8 targets consistent | seven targets consistent after excluding `#8` |
|---|---|---|---|---|
| `.kernarg_segment_size` | **12** | 296×72; 424×40; 288×32; 304×32; 280×24; 320×16; 336×16; 12×8; 16×8; 328×8; 384×8; 8×8 | **yes** | yes |
| `.kernarg_segment_align` | 1 | 8×272 | **yes** | yes |
| `.max_flat_workgroup_size` | 2 | 256×208; 1024×64 | **yes** | yes |
| `.uniform_work_group_size` | 1 | 1×272 | **yes** | yes |
| `.uses_dynamic_stack` | 1 | False×272 | **yes** | yes |
| `.language` | 1 | OpenCL C×272 | **yes** | yes |
| `.language_version` | 1 | [2, 0]×272 | **yes** | yes |
| `.symbol` | 34 | `_Z…kd` form, 8 occurrences each (34 symbols) | **yes** | yes |
| `.group_segment_fixed_size` | **21** | 0×84; 15616×24; 24576×18; 16384×16; 4096×16; 62592×16; 8192×12; 1024×8; 12800×8; 15632×8; 19200×8; 21504×8; 6144×8; **64640×8**; 19456×6; 23808×6; 28928×6; 58368×6; 16640×2; 17152×2; 20480×2 | **no** | no |
| `.private_segment_fixed_size` | **11** | 0×208; **24×38**; 64×12; 100×2; 216×2; 244×2; 40×2; 80×2; 88×2; 404×1; 84×1 | **no** | no |
| `.sgpr_count` | **58** | 18×23; 20×17; 3×12; 28×10; 32×9; 69×9; 43×8; 49×8; 70×8; … (58 distinct values, maximum **107**) | **no** | no |
| `.sgpr_spill_count` | **8** | 0×262; 43×2; 45×2; 64×2; 133×1; 29×1; 6×1; 69×1 | **no** | no |
| `.vgpr_count` | **84** | 2×16; 194×12; 64×9; 112×8; 21×8; 26×8; … (84 distinct values, maximum **202**) | **no** | no |
| `.vgpr_spill_count` | **8** | 0×258; 17×4; 20×2; 7×2; 75×2; 88×2; 100×1; 23×1 | **no** | no |
| `.wavefront_size` | 2 | 32×238; 64×34 | **no** | **yes** |
| `.workgroup_processor_mode` | 2 | 1×238; **absent ×34 (all `#8`)** | **no** | **yes** |

### 2.3 Cross-Target Consistency

**Fields whose values are identical across all 8 targets (8 fields)**:

`.kernarg_segment_size`, `.kernarg_segment_align`, `.max_flat_workgroup_size`, `.uniform_work_group_size`, `.uses_dynamic_stack`, `.language`, `.language_version`, `.symbol`

**Fields whose values are not identical across the 8 targets (8 fields, with scope 1's "number of kernels not fully identical / 34")**:

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

**Grouping the 8 targets by their 16-field vector gives 6 groups**: {gfx10-3-generic}, {gfx11-generic, gfx1102}, {gfx1100}, {gfx1101}, {gfx1200, gfx1201}, {gfx9-generic}.

### 2.4 Three Counting Scopes for Cross-Target Inconsistency

> **Do not mix the three scopes.**

| Scope | Definition | Measured value |
|---|---|---|
| **Scope 1: field × kernel pair** | among the 16 fields × 34 kernels = 544 (field, kernel) pairs, the number of pairs whose value is not identical across the 8 targets | **163** |
| **Scope 2: cell count (compared with `#1`)** | taking `#1` as baseline, the number of cells where each non-`#1` target differs from `#1` within the inconsistent fields (7 non-`#1` targets) | **605** |
| **Scope 3: cell count (8 targets compared pairwise)** | the sum, per cell, of the number of pairwise-distinct pairs among the 8 targets | **2183** |
| Reference: total number of cells | 34 kernels × 16 fields × 8 targets = **4352**; when compared with `#1` it is 34 × 16 × 7 = **3808** | 4352 / 3808 |

**Per-field breakdown for scope 2 (computed 605)**:

| Field | cell count |
|---|---|
| `.vgpr_count` | 209 |
| `.sgpr_count` | 207 |
| `.group_segment_fixed_size` | 66 |
| `.wavefront_size` | 34 |
| `.workgroup_processor_mode` | 34 |
| `.private_segment_fixed_size` | 32 |
| `.vgpr_spill_count` | 14 |
| `.sgpr_spill_count` | 9 |
| **total** | **605** |

**Warning**: **163 is not a cell count**. Estimating as "163 × 7" gives 1141 (actual scope 2 = 605), and estimating as "163 × 28" gives 4564 (actual scope 3 = 2183) —— **both are wrong**. Wherever these three numbers are cited, the scope from which they came must be stated.

### 2.5 Hard Constraint List

#### (a) `group_segment_fixed_size` (LDS / SLM requirement)

| Criterion | Measured |
|---|---|
| `>= 65536` (64 KiB) | **0 hits** (0 of the 272 entries) |
| maximum over all 272 entries | **64,640 B (`0xFC80` = 63.125 KiB)** |
| difference between the maximum and 65,536 B | **896 B (0.875 KiB)** |
| `>= 60000` band | 64,640 × 8, 62,592 × 16 (24 entries in total) |

**Three high-risk kernels**:

| Kernel | Value | 8-target values |
|---|---|---|
| k1 `_Z21k_pre_block_1h_32_fp89PreParams` | **64,640 B (`0xFC80` = 63.125 KiB)** | consistent `[64640]×8` |
| k0 `_Z16k_swin_1h_32_fp810SwinParams` | 62,592 B (`0xF480` = 61.125 KiB) | consistent `[62592]×8` |
| k2 `_Z22k_post_block_1h_32_fp810PostParams` | 62,592 B (`0xF480` = 61.125 KiB) | consistent `[62592]×8` |

**Scope discipline**: under the 272-entry scope, 64,640 occurs **8 times** (one entry each for `#1`…`#8`); one **must not** write "`k_pre_block_1h_32_fp8` = 64,640" without stating the scope. Likewise 58,368 occurs 6 times and 28,928 occurs 6 times; these are also in the "value + occurrence count" scope and **must not be attributed to a single point**.

**One phrasing that must be avoided**: one **must not** write "64,640 B exceeds the SLM limit of a single Xe-core on Xe" —— that statement contradicts the bytes (`>=65536` gets 0 hits, margin 896 B).

#### (b) Per-target distribution of `private_segment_fixed_size = 24`

This quantity varies with target; **there is no single set of kernels uniform across the 8 targets**:

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
| — | **total** | — | **38** ✅ |

**Only 2 kernels are 24 across all 8 targets**: k8 (`k_qkv_attn2`), k33 (`k_swin_var<256,false>`).

**Same kernel with different values across targets (raw byte evidence, bundle `#1`)**: k5 `_Z10k_qkv_attn10AttnParams` is 24 in `#1` (value byte `18`), 0 in `#2` (value byte `00`), and 24 in `#8` (value byte `18`).

#### (c) `.wavefront_size` = 32 vs 64

| Value | Record count | Distribution |
|---|---|---|
| **32** | **238** | all 34 kernels of `#1`–`#7` (7 × 34) |
| **64** | **34** | all 34 kernels of `#8` `gfx9-generic` only |

**Raw byte evidence**: bundle `#1` k0 value byte = `20` (fixint = 32); bundle `#8` k0 value byte = `40` (fixint = 64).

**Scope**: 8-target consistency = **no**; the seven targets are consistent after excluding `#8`.

**Important limitation**: this difference holds for **34/34** kernels, and the difference **lies entirely on the target axis** (there is no difference on the kernel axis). It is therefore **not** a distinguishing criterion for any kernel classification —— writing it as "some kernels fall into a certain class because `wavefront_size` = 64" contradicts the bytes (all 34 kernels of `#8` are 64).

#### (d) `.max_flat_workgroup_size` = 256 vs 1024

| Value | Kernels | Entry count |
|---|---|---|
| **1024** | k20, k22, k23, k24, k25, k26, k27, k28 (**8 kernels**) | 64 (8 × 8 targets) |
| **256** | the remaining **26 kernels** | 208 |

- 8-target consistency = **yes** (the difference is between kernels, not between targets);
- **the two scopes are equivalent, and a citation must state which**: 34-kernel scope = **256 × 26 / 1024 × 8**; 272-entry scope = **256 × 208 / 1024 × 64**.

**These 8 kernels form one semantic cluster**: `k_repack` / `k_mean` / `k_import` / `k_export` / `k_reproject` / `k_flag_wait` / `k_align_probe` / `k_flag_set` —— by name they all belong to the "data movement / view / reduction / synchronization" class, and **not one belongs to the Swin / convolution / attention class**.

#### (e) Register-pressure extremes (per target)

| Target | triple | max `.vgpr_count` (kernel) | max `.sgpr_count` (kernel) | `.sgpr_spill_count > 0` | `.vgpr_spill_count > 0` |
|---|---|---|---|---|---|
| 1 | gfx10-3-generic | 145 (k7) | 107 (k7) | [7] | none |
| 2 | gfx11-generic | 194 (**k0 / k1 / k2 tied**) | 107 (k7) | [7] | [29,30,31,32] |
| 3 | gfx1100 | 194 (**k0 / k1 / k2 tied**) | 107 (k7) | [7] | [31,32] |
| 4 | gfx1101 | 194 (**k0 / k1 / k2 tied**) | 107 (k7) | [7] | [31,32] |
| 5 | gfx1102 | 194 (**k0 / k1 / k2 tied**) | 107 (k7) | [7] | [29,30,31,32] |
| 6 | gfx1200 | 202 (k7) | 107 (k7) | [7] | none |
| 7 | gfx1201 | 202 (k7) | 107 (k7) | [7] | none |
| 8 | gfx9-generic | 122 (k14 only) | 104 (**k7 / k29 tied**) | [7,11,29] | [7,25] |

**Notes on ties**:

- the max `.vgpr_count` = 194 for `#2`–`#5` is **tied between k0 `k_swin_1h_32_fp810SwinParams` / k1 `k_pre_block_1h_32_fp89PreParams` / k2 `k_post_block_1h_32_fp810PostParams`**;
- the max `.sgpr_count` = 104 for `#8` is **tied between k7 `k_conv_res211Conv2Params` / k29 `_Z10k_swin_varILi32ELb1EEv9VarParams`**;
- the extremes of all other targets each belong to a unique kernel.

**Two scopes for the spill fields (each must be labelled separately)**:

| Scope | `.sgpr_spill_count` | `.vgpr_spill_count` |
|---|---|---|
| **number of non-zero entries** (272-entry scope) | **10** | **14** |
| **distinct values (including 0)** | **8** | **8** |
| **distinct non-zero values** | **7** | **7** |

**One correction**: the "8 non-zero entries" figure mistook the **number of distinct values** for the **number of entries**. The correct non-zero entry counts are 10 / 14 (obtained by summing the non-zero terms of the frequency rows: `43×2+45×2+64×2+133×1+29×1+6×1+69×1` = 10; `17×4+20×2+7×2+75×2+88×2+100×1+23×1` = 14).

**Per-target unique extremes**: `.private_segment_fixed_size` = **404 B** (k7 in `#8`) and **84 B** (k25 in `#8`) are extremes that **occur only in `#8`**, and each occurs **exactly once** among the 272 entries.

#### (f) Fixed values of the remaining fields (272-entry scope, 8 targets consistent)

| Field | Value |
|---|---|
| `.kernarg_segment_align` | 8 × 272 |
| `.uniform_work_group_size` | 1 × 272 |
| `.uses_dynamic_stack` | False × 272 |
| `.language` | OpenCL C × 272 |
| `.language_version` | [2, 0] × 272 |

---

## 3. Per-Kernel Resource and `codesz` Summary

Column definitions: `kernarg` = `.kernarg_segment_size`; `group` = the 8-target value set of `.group_segment_fixed_size` (`k` denotes the repetition count); `priv` = the 8-target value set of `.private_segment_fixed_size`; `vgpr_max` / `sgpr_max` = the 8-target maximum (reference for pressure only); `maxWG` = `.max_flat_workgroup_size` (8 targets consistent); `wave` = the 8-target `.wavefront_size` value set; `codesz` = that kernel's code symbol `st_size` (8-target values).

| # | semantics (name-based inference) | kernarg | group | priv | vgpr_max | sgpr_max | maxWG | wave | codesz |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `k_swin_1h_32_fp8(SwinParams)` | 296 | 62592 | {0, 64} | 194 | 35 | 256 | 32/64 | 40364 / 4152×4 / 14528×2 / 38184 |
| 1 | `k_pre_block_1h_32_fp8(PreParams)` | 336 | **64640** | {0, 64} | 194 | 79 | 256 | 32/64 | 45056 / 9764×4 / 19536×2 / 43276 |
| 2 | `k_post_block_1h_32_fp8(PostParams)` | 336 | 62592 | {0, 64} | 194 | 52 | 256 | 32/64 | 43088 / 7196×4 / 18164×2 / 41160 |
| 3 | `k_ffwd(FfwdParams)` | 288 | {0, 24576} | 0 | 112 | 28 | 256 | 32/64 | 688 / 19800 / 19612×2 / 19800 / 6044×2 / 660 |
| 4 | `k_conv_res(ConvParams)` | 296 | {0, 8192} | 0 | 87 | 29 | 256 | 32/64 | 4580 / 8732 / 8512×2 / 8732 / 3516×2 / 4308 |
| 5 | `k_qkv_attn(AttnParams)` | 296 | {20480, 58368} | **{0, 24}** | 102 | 62 | 256 | 32/64 | 35392 / 87752×4 / 9192×2 / 33560 |
| 6 | `k_ffwd2(Ffwd2Params)` | 304 | {0, 21504} | 0 | 90 | 54 | 256 | 32/64 | 1712 / 30660 / 30340 / 30336 / 30660 / 7460×2 / 1376 |
| 7 | `k_conv_res2(Conv2Params)` | 320 | 0 | **{0, 404}** | **202** | **107** | 256 | 32/64 | 27444 / 33996 / 33992×2 / 33996 / 23412×2 / 30552 |
| 8 | `k_qkv_attn2(AttnParams)` | 296 | {21504, 23808} | **24** | 144 | 49 | 256 | 32/64 | 16984 / 31212×4 / 8952×2 / 16000 |
| 9 | `k_expand(ExpandParams)` | 280 | {0, 16384} | 0 | 90 | 21 | 256 | 32/64 | 1288 / 13520 / 13364×2 / 13520 / 3908×2 / 1048 |
| 10 | `k_conv_splitk(ConvParams1d)` | 304 | 4096 | 0 | 82 | 42 | 256 | 32/64 | 3632 / 8992×4 / 7480×2 / 3508 |
| 11 | `k_qkv(QkvParams)` | 296 | 6144 | 0 | 119 | 106 | 256 | 32/64 | 41596 / 77136 / 77128×2 / 77136 / 6076×2 / 39724 |
| 12 | `k_attention(AttnParams1d)` | 296 | {16640, 28928} | 0 | 144 | 48 | 256 | 32/64 | 2060 / 43664 / 43656×2 / 43664 / 6664×2 / 1948 |
| 13 | `k_expand2(ExpandParams)` | 280 | 0 | 0 | 93 | 29 | 256 | 32/64 | 1300 / 19280 / 19356×2 / 19280 / 4928×2 / 1012 |
| 14 | `k_contract2(ConvParams1d)` | 304 | 16384 | 0 | 161 | 69 | 256 | 32/64 | 18740 / 26064 / 26108×2 / 26064 / 19404×2 / 15960 |
| 15 | `k_qkv2(QkvParams)` | 296 | 12800 | 0 | 119 | 34 | 256 | 32/64 | 12300 / 21768×5 / 8492×2 / 11208 |
| 16 | `k_attention2(AttnParams1d)` | 296 | {17152, 19456} | 0 | 107 | 49 | 256 | 32/64 | 3564 / 10228 / 10008×2 / 10228 / 7564×2 / 3424 |
| 17 | `k_ffwd_inpview(FfwdPlParams)` | 288 | {0, 24576} | 0 | 112 | 28 | 256 | 32/64 | 688 / 18600 / 18412×2 / 18600 / 4788×2 / 660 |
| 18 | `k_conv_res_views(ConvPlParams)` | 328 | {16384, 24576} | 0 | 137 | 68 | 256 | 32/64 | 6012 / 13304 / 13140×2 / 13304 / 7304×2 / 5628 |
| 19 | `k_final_head(HeadParams)` | 280 | {0, 8192} | 0 | 84 | 18 | 256 | 32/64 | 384 / 7184 / 6956×2 / 7184 / 2936×2 / 288 |
| 20 | `k_repack(RepackParams)` | 288 | 0 | 0 | 18 | 30 | **1024** | 32/64 | 856 / 1000×5 / 1032×2 / 796 |
| 21 | `k_dec_upsample(DecUpParams)` | 296 | 4096 | 0 | 81 | 29 | 256 | 32/64 | 1248 / 15128 / 15120 / 15116 / 15128 / 3348×2 / 1184 |
| 22 | `k_mean(MeanParams)` | 288 | 1024 | 0 | 11 | 22 | **1024** | 32/64 | 1084 / 1256×5 / 1272×2 / 1028 |
| 23 | `k_import(ImportParams)` | 304 | 0 | 0 | 21 | 22 | **1024** | 32/64 | 4324 / 5200×5 / 5520×2 / 4588 |
| 24 | `k_export(ExportParams)` | 320 | 0 | 0 | 26 | 19 | **1024** | 32/64 | 5440 / 6592×5 / 6960×2 / 5628 |
| 25 | `k_reproject(ReprojParams)` | **384** | 0 | **{0, 84}** | 72 | 48 | **1024** | 32/64 | 10036 / 12260 / 12272×2 / 12260 / 12992×2 / 11376 |
| 26 | `k_flag_wait(Pjjj)` | **16** | 0 | 0 | 2 | 12 | **1024** | 32/64 | 112 / 116×4 / 124×2 / 112 |
| 27 | `k_align_probe(Ph)` | **8** | 0 | 0 | 3 | 4 | **1024** | 32/64 | 4 / 52×4 / 56×2 / 4 (smallest of all 34 kernels) |
| 28 | `k_flag_set(Pjj)` | **12** | 0 | 0 | 2 | 10 | **1024** | 32/64 | 92×5 / 124×2 / 72 |
| 29 | `k_swin_var<32,true>(VarParams)` | 424 | 15616 | {24, 100} | 96 | 104 | 256 | 32/64 | 35156 / 81756 / 80128×2 / 81756 / 29580×2 / 34020 |
| 30 | `k_swin_var<32,false>(VarParams)` | 424 | **15632** | {24, 40} | 91 | 102 | 256 | 32/64 | 38044 / 84880 / 83724×2 / 84880 / 29256×2 / 36568 |
| 31 | `k_swin_var<64,false>(VarParams)` | 424 | 15616 | {24, 88, 244} | 120 | 70 | 256 | 32/64 | 29552 / 91924 / 90116×2 / 91924 / 23148×2 / 27856 |
| 32 | `k_swin_var<128,false>(VarParams)` | 424 | 15616 | {24, 80, 216} | 120 | 69 | 256 | 32/64 | 28584 / 86900 / 84572×2 / 86900 / 25876×2 / 26948 |
| 33 | `k_swin_var<256,false>(VarParams)` | 424 | **19200** | **24** | 136 | 70 | 256 | 32/64 | 28640 / 83736 / 83676×2 / 83736 / 22592×2 / 26976 |

### 3.1 Statistical Summary

| Statistic | Value |
|---|---|
| number of kernels with `group` **non-zero** and consistent across all 8 targets | **14** |
| number of kernels with `group` = 0 across all 8 targets | **9** |
| number of kernels whose `group` varies across targets | **11** |
| number of kernels with non-zero `priv` in any target | **12** |
| number of kernels with `priv` = 0 across all 8 targets | **22** |
| number of kernels with `maxWG` = 1024 | **8** |
| number of kernels whose `priv` contains a unique extreme (404 or 84) | **2** |
| identity | `14 + 9 + 11 = 34` ✅; `P + p = 12` ✅ |

---

## 4. Summary of Cross-Target Consistency Conclusions

### 4.1 Parameter Surface (consistent)

| Item | Result |
|---|---|
| judgement cells for 34 kernels × 7 non-baseline targets | **238/238 consistent** |
| ordered kernel-name list | **7/7 identical** |
| `.args` array byte-level SHA256 | identical **272/272** (12 distinct byte strings) |
| differing entries | **0** |

### 4.2 Resource Surface (8 fields inconsistent)

Of the 16 field entities:

- **8 are fully consistent across the 8 targets**: `.kernarg_segment_size`, `.kernarg_segment_align`, `.max_flat_workgroup_size`, `.uniform_work_group_size`, `.uses_dynamic_stack`, `.language`, `.language_version`, `.symbol`;
- **8 are not consistent across the 8 targets**: `.sgpr_count`, `.wavefront_size`, `.workgroup_processor_mode`, `.vgpr_count`, `.group_segment_fixed_size`, `.private_segment_fixed_size`, `.vgpr_spill_count`, `.sgpr_spill_count`.

### 4.3 Three Limitations That Must Accompany Any Citation

1. **Consistency of the parameter surface does not equal consistency of the resource surface** (the limitation of §4.1).
2. **The `.wavefront_size` 32 / 64 difference lies on the target axis, not the kernel axis** —— 32 is `#1`–`#7` (238 records), 64 is `#8` (34 records).
3. **`#8 gfx9-generic` is a systematic outlier target**:
   - `.wavefront_size` = 64 (unique to it);
   - both `priv` unique extremes (404 / 84) occur only in `#8`;
   - `.workgroup_processor_mode` is **entirely absent** (`#8` has 17 keys);
   - the kernel with `group` = 20480 (k5) falls into two different bands: `#1` / `#8` versus `#2`–`#7`.

   ⇒ **Taking parameters from a single target will go systematically wrong.**

### 4.4 Unified Strategy for Resource Fields (overview)

| Field | Strategy | Can it be retained as an execution parameter on the Intel side |
|---|---|---|
| `.group_segment_fixed_size` | **must be recomputed against the platform limit** | **yes** (as the SLM request amount), but the value must be re-verified |
| `.private_segment_fixed_size` | **must be recomputed against the platform granularity** | **yes** (as the private-memory request amount), but the value must be re-verified |
| `.sgpr_count` | **discard** (retain as pressure reference) | **no** |
| `.sgpr_spill_count` | **discard** (retain as reference) | **no** |
| `.vgpr_count` | **discard** (retain as pressure reference) | **no** |
| `.vgpr_spill_count` | **discard** (retain as reference) | **no** |
| `.wavefront_size` | **discard** (record the original value only) | **no** |
| `.workgroup_processor_mode` | **discard** (rebuild from the target platform's own mode) | **no** |

**Basis for the two classes of strategy**:

- **The six fields are discarded without exception**: ① the four register fields are compiler-output counts and are **themselves mutually different across the 8 targets** (`.sgpr_count` 58 values, `.vgpr_count` 84 values) ⇒ **there is no unique value to take as cross-platform input**; ② the `.wavefront_size` difference **lies only on the target axis** ⇒ it is a **target property**, not a kernel property; ③ `.workgroup_processor_mode` is **entirely absent** in `#8` ⇒ "cross-target common input" does not hold.
- **Two fields must be re-verified against the platform limit**: ① both fields **have a value distribution** across the 8 targets (21 / 11 deduplicated values) and **no cross-target common value exists**; ② their semantics is a resource request amount (SLM / private segment), **directly coupled** with platform-side capacity constraints.

The detailed table and per-kernel adaptation advice are in `05-Intel-Feasibility-Assessment.md` §3.

---

## 5. Collisions with Established Hard Facts

### 5.1 `k_reproject`'s `kernarg_segment_size`: 128 → measured **384**

| Item | Value |
|---|---|
| existing documentation table | 128 |
| **measured (metadata)** | **384** (idx 25) |
| byte evidence | msgpack encoding **`CD 01 80`** (`CD` = **uint16**, big-endian `0x0180` = 384), located in blob `#1` `[28169, 28172)` → file `0x80255` / VA `0x180087055` (blob `#1` start file `0x7944C` / VA `0x18008024C`) |
| collision | `CD 01 80` gets **1** hit in blob `#1` and **9** hits in the whole DLL; whereas the encoding string constructed with the uint32 notation (`CE` + 4-byte big-endian 384) gets **0 hits in both** blob `#1` and the whole DLL |

**Encoding-width correction**: earlier material gave the encoding string in uint32 notation, which is an **encoding-width misrecord** (`CE` = uint32 should be `CD` = uint16).

**Scope note**: among `k_reproject`'s 14 parameters, `by_value` = 128 B, while `kernarg_segment_size` = 384 —— **the two are not the same quantity**.

### 5.2 `k_flag_set`'s `kernarg_segment_size`: 16 → measured **12**

| Item | Value |
|---|---|
| existing documentation table | 16 |
| **measured (metadata)** | **12** (idx 28) |
| byte evidence | msgpack encoding `0C` (positive fixint = 12) |

### 5.3 Misalignment of the `by_value` User-Parameter Size Column

**Explicit mapping: the user parameter value in row i of the existing documentation (the 34-row table) = the measured `by_value` value of the (i+1)-th kernel.**

**Shift scan (objective determination)**:

| offset s (doc row i ↔ measured kernel i+s) | hits | comparable rows | hit rate |
|---|---|---|---|
| s = 0 | 9 | 34 | 26.5% |
| **s = +1** | **31** | **33** | **93.9%** |
| s = +2 | 8 | 32 | 25.0% |
| s = +3 | 4 | 31 | 12.9% |

**The unique peak occurs at s = +1** → the one-row misalignment holds.

**Scope statement**: the table above uses the scope "`k_align_probe` has no `by_value` and participates in the comparison as 0" (hence the comparable row count is 34 for s = 0 and 33 for s = +1). If that kernel is excluded as non-comparable, then s = 0 gives 9/33 and s = +1 gives **30/32** (the other two bands are unchanged), and **the conclusion that the unique peak is at s = +1 is unchanged**; under the two scopes the hit rate at s = +1 is 93.9% (31/33) and 93.75% (30/32) respectively.

**The `kernarg` column is not misaligned**: the documentation's `kernarg` column equals the same-row measured `kernarg` in **32/34** cases (exceptions: rows 26 and 29) ⇒ **the misalignment occurs only in the `.by_value` user-parameter size column**; it is not a whole-table misalignment, nor a `kernarg` column misalignment.

**The 2 exception rows by name**: row 7 `k_ffwd2` (documentation 40; same row 48, next row 64); row 29 `k_flag_set` (documentation 12; same row 4, next row 168). Row 34 has no next row to compare with (hence the comparable row count for s = +1 is 33).

**Misalignment examples (two sources side by side in the same row)**:

| Documentation row | user value written in the doc | same-row measured kernel `by_value` | next-row measured kernel `by_value` | Conclusion |
|---|---|---|---|---|
| row 1 `k_swin_1h_32_fp8` | 80 | 40 | 80 | doc value = the measured value of the **next-row kernel** |
| row 3 `k_post_block` | 32 | 80 | 32 | as above |
| row 4 `k_ffwd` | 40 | 32 | 40 | as above |
| row 6 `k_qkv_attn` | 48 | 40 | 48 | as above |
| row 8 `k_conv_res2` | 40 | 64 | 40 | as above |
| row 26 `k_reproject` | 4 | 128 | 4 | as above |

**Raw byte corroboration (5 examples)**: blob = the msgpack document of bundle `#1`, start file `0x7944C` / VA `0x18008024C` / RVA `0x8024C`.

| # | kernel (idx) | `by_value` `.offset` | `by_value` `.size` | encoding bytes of `.size` | offset in blob | file / VA | whole parameter-map blob range | whole parameter-map raw bytes |
|---|---|---|---|---|---|---|---|---|
| 1 | `_Z16k_swin_1h_32_fp810SwinParams` (0) | 0 | 40 | `28` | `[45, 46)` | `0x79479` / `0x180080279` | `[29, 67)` | `83 A7 2E 6F 66 66 73 65 74 00 A5 2E 73 69 7A 65 28 AB 2E 76 61 6C 75 65 5F 6B 69 6E 64 A8 62 79 5F 76 61 6C 75 65` |
| 2 | `_Z21k_pre_block_1h_32_fp89PreParams` (1) | 0 | 80 | `50` | `[1151, 1152)` | `0x798CB` / `0x1800806CB` | `[1135, 1173)` | `83 A7 2E 6F 66 66 73 65 74 00 A5 2E 73 69 7A 65 50 AB 2E 76 61 6C 75 65 5F 6B 69 6E 64 A8 62 79 5F 76 61 6C 75 65` |
| 3 | `_Z22k_post_block_1h_32_fp810PostParams` (2) | 0 | 80 | `50` | `[2266, 2267)` | `0x79D26` / `0x180080B26` | `[2250, 2288)` | `83 A7 2E 6F 66 66 73 65 74 00 A5 2E 73 69 7A 65 50 AB 2E 76 61 6C 75 65 5F 6B 69 6E 64 A8 62 79 5F 76 61 6C 75 65` |
| 4 | `_Z6k_ffwd10FfwdParams` (3) | 0 | 32 | `20` | `[3387, 3388)` | `0x7A187` / `0x180080F87` | `[3371, 3409)` | `83 A7 2E 6F 66 66 73 65 74 00 A5 2E 73 69 7A 65 20 AB 2E 76 61 6C 75 65 5F 6B 69 6E 64 A8 62 79 5F 76 61 6C 75 65` |
| 5 | `_Z10k_swin_varILi256ELb0EEv9VarParams` (33) | 0 | 168 | `CC A8` | `[34526, 34528)` | `0x81B2A` / `0x18008892A` | `[34510, 34549)` | `83 A7 2E 6F 66 66 73 65 74 00 A5 2E 73 69 7A 65 CC A8 AB 2E 76 61 6C 75 65 5F 6B 69 6E 64 A8 62 79 5F 76 61 6C 75 65` |

---

## 6. Three Independent Corroborations of the 34 Kernels (cross-check)

| Corroboration | Measured | Relation to metadata |
|---|---|---|
| (a) code entries in table A `0x180056170..0x1800562A8` (inclusive endpoints, counted as 40 slots) that point into `.text` | **34** items (idx 0–25 + 30–32 + 35–39) | equal |
| (b) calls to `0x180055960` (the `__hipRegisterFunction` thunk) within all of `.text` | `call` → **34** sites, `jmp` → **0** sites (`E8` = 34, `E9` = 0; all 34 fall inside the `.pdata` function `0x180010810..0x180010F77`, first `0x18001086E`, last `0x180010F22`) | equal |
| (c) metadata kernel entry count | 272 ÷ 8 = **34** | equal |

**Boundary scope note**: `0x180056170..0x1800562A8` counted with inclusive endpoints is **40** slots; counted as 39 slots (excluding idx 39) the items pointing into `.text` are 33 —— this boundary ambiguity **does not affect** the "34 code entries" conclusion (34 = 0–25 + 30–32 + 35–39).
