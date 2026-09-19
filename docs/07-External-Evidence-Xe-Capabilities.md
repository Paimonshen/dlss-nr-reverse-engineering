# External Evidence: Xe Capabilities for G-01 … G-04

## Preamble

This document records **externally-sourced findings** that answer four items of the external-documentation checklist in [`05-Intel-Feasibility-Assessment.md`](05-Intel-Feasibility-Assessment.md) §8.1 — the four **roadmap determination premises G-01 … G-04**.

**Target hardware, stated once so it is never ambiguous.** The device this project is assessing is the **Intel Arc B580**, which is **Xe2 / Battlemage** generation with **XMX engines**. Wherever this document says "Xe" without qualification it means *this part*; a generation table appears only because the vendor documents datatypes **per generation** and the requirement must be read off the **correct row** — the **B580's** row.

Four statements govern everything below.

1. **Every finding carries a citation.** Sources are given as markdown links, and primary sources (merged commits, vendor documentation, project documentation) are preferred over secondary ones.
2. **A finding that could not be confirmed from a primary source is marked explicitly** as **"reported (not independently verified)"**, **"reported"**, or **"still needs verification"**. Such a finding is recorded as a lead, not as an established fact.
3. **These findings have NOT been independently reproduced in this project's environment.** There is no Intel toolchain and no Xe hardware here (constraints E-3 and the absence of target hardware, `05` §0.1). Nothing in this document is a measurement made by this project. Every item is **external evidence**, quoted from its source and attributed to that source.
4. **This document does not change any measurement in `docs/04` or `docs/05`.** No byte-level number, kernel classification, resource count or parameter table is revised here. It only supplies external answers to questions that were previously open.

**Citation convention used below.** "Primary" means the source is the artefact itself (the merged change, the vendor's own documentation, the project's own documentation). "Reported" means the claim rests on a secondary or community report and has not been traced to a primary artefact.

**A caution this document records against itself.** Several Intel documentation pages are **JavaScript-rendered** and return only navigation chrome to a plain fetch, one vendor blog returned **HTTP 403**, and the Intel compiler repository (`DPAS.md`) is **unreachable from this environment**. Where a quotation could not be re-read directly, the citation says so and the finding is downgraded accordingly. **The sources that *were* read directly are the ones carrying "confirmed" labels.**

---

## G-01 — XMX primitives and precision modes

### Question as posed in the checklist

> **whether Intel XMX provides directly callable primitives for matrix multiply / convolution; the coverage of its precision modes (including FP8 / FP16 / BF16 / INT8)**

(`05` §8.1, G-01; affected scope stated there as **25 kernels**, k0–k19 and k29–k33.)

### Finding

**The primitive is DPAS, and it is a dot-product-accumulate — not a convolution.**

The XMX execution unit's instruction-level primitive is **DPAS (Dot Product Accumulate Systolic)**: a systolic-array dot-product-accumulate with the semantics `D = C + A×B`. **XMX does not expose a direct "convolution" instruction.** Convolution and matrix-multiply acceleration at the library level happens by **mapping** those operations onto DPAS — for example through oneDNN, whose Intel-GPU convolution and matmul implementations are built on the same DPAS primitive. The mapping layer is part of the finding, not an implementation detail: an operator is accelerated only once something has expressed it as a matrix multiply.

**Precision support — stated for the target hardware, not as an abstract generation table.**

> **The target hardware is the Intel Arc B580** (Xe2 / Battlemage). Every precision question below is therefore asked about **this GPU**, not about "Xe in general". A generation table is given only because the vendor documents datatypes **per generation**, and reading the requirement off the wrong row is exactly the mistake this framing prevents.

| Generation | XMX data types | Status for us |
|---|---|---|
| **Xe-HPG** (Arc A-series, Alchemist) | **FP16 / BF16 / INT8 / INT4 / INT2** — **no TF32** | **confirmed** (vendor per-product datatype table) — *not our hardware, listed for contrast* |
| **Xe2** (Battlemage) — **this includes the Arc B580** | **FP16 / BF16 / INT8 / INT4 / INT2**, with **TF32 added** | **reported, not independently confirmed** — see the residual gap below |

**What this means concretely for a B580 port.** The **confirmed** B580 statement is narrower than the full TF32 question:

- **Confirmed for the B580:** it is an **Xe2 / Battlemage** part with **XMX engines**; and the vendor's AI-datatypes article lists **Intel Arc B-Series Graphics in its product set** alongside the Xe-HPG row.
- **Not confirmed for the B580:** that **TF32 is available on this specific part**. The evidence for "TF32 added on Xe2" is a documentation sentence listing TF32 as a type supported **"depending on hardware generation"** (without naming which generation) plus a vendor **blog** post. **Neither is a B580-specific datatype statement.**

> **Practical consequence — plan the B580 port on the confirmed set.** **FP16 / BF16 / INT8 / INT4 / INT2** are the datatypes this project treats as **available on the B580**. Any TF32-based path must be treated as a **possible optimisation to verify on the actual device** (via a device capability query or a `joint_matrix`/oneAPI datatype test), **not as a porting assumption**. This changes nothing about the confirmed DPAS/mapping-layer findings above, all of which hold regardless of TF32.

Support is **generation-dependent**. The vendor's optimization guide states that XMX "supports numerous data types, **depending on hardware generation**, such as int8, fp16, bf16, and tf32"; the vendor's own per-product datatype table for **Xe-HPG (Arc A-Series)** lists **FP16 / BF16 / INT8 / INT4 / INT2 and no TF32**. Read together, the consistent reading is that **TF32 is not an Xe-HPG capability** and that its XMX support is a **later-generation** addition which would therefore include the B580 — but the two statements do not constitute a **B580-specific** datatype declaration, so the B580/TF32 row remains **reported**.

> **TF32 numeric note (reported).** TF32 uses the **same 8-bit exponent as FP32** with a reduced mantissa, which is why it is attractive as a higher-throughput path for FP32-shaped workloads. **This is recorded as a reported statement; it was not measured here.**

**Separate, independently-sourced fact — FP32 GEMM is commonly approximated on XMX.** The vendor's optimization guide documents oneMKL algorithms named **`bf16x2`** and **`bf16x3`** that accelerate **single-precision** `gemm`/`gemm_batch` on XMX by **converting FP32 inputs to BF16** and multiplying on the systolic array, trading accuracy for throughput in several variants. **This is useful on the B580 precisely because it does not depend on the TF32 question**: an FP32-shaped kernel has a **library-supported approximate path** on XMX even if TF32 turns out to be unavailable on the part.

**Operational consequence — XMX acceleration is not automatic.** Two conditions must both hold before DPAS is reached:

1. **the data type must be supported** by the generation in question (the table above is the support surface), and
2. **the operation must pass through a mapping layer** — either a library (oneDNN, or a compiler that emits the same path), or **explicit** `joint_matrix` / XMX intrinsics written by hand in the kernel.

The vendor's guide states that **oneDNN enables Intel XMX support by default on Xe 4th-generation processors and later**, provided the application is built with GPU support and uses XMX-supported datatypes. A negligible detail this records: **the acceleration is a property of the library path, not of the hardware alone.**

A scalar loop does not become DPAS merely by being compiled for Xe. There is no implicit upgrade from ordinary arithmetic to the XMX path; something must put the matrix-multiply shape into the IR — via `joint_matrix` (whose `joint_matrix_mad` is documented as the multiply-add operation), a library, or an intrinsic.

**Practical mapping guidance.** A candidate for XMX is an operator that is **compute-intensive and decomposable into a matrix multiply**. The following are **not** XMX candidates and belong on the **vector engine path**:

- elementwise operations,
- reductions,
- softmax,
- transposes.

### Citations

- [Intel oneAPI GPU Optimization Guide — Boost Matrix Multiplication Performance with Intel Xe Matrix Extensions (XMX), 2025.2](https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2025-2/boost-matrix-multiplication-performance-with-intel.html) — primary (Intel documentation, XMX section). *Page body is JavaScript-rendered and could not be retrieved in full from this environment; the quoted wording is recorded as supplied and **not** independently re-read here.*
- [Intel oneAPI GPU Optimization Guide — Programming Intel XMX using SYCL `joint_matrix`, 2025.2](https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2025-2/programming-intel-xmx-using-sycl-joint-matrix.html) — primary (Intel documentation). Documents `joint_matrix`, `joint_matrix_load` / `joint_matrix_store`, and `joint_matrix_mad`, and describes DPAS as the elementary XMX operation. *Same retrieval caveat as above.*
- [Intel oneAPI GPU Optimization Guide — XMX section, 2024.1](https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2024-1/xmx.html) — primary (Intel documentation). Source of the oneDNN-default-on statement and of the `bf16x2` / `bf16x3` single-precision GEMM description. *Same retrieval caveat.*
- [Intel — AI Engines and Supported Datatypes (Article 000098346, reviewed 2026-01-13)](https://www.intel.com/content/www/us/en/support/articles/000098346/graphics.html) — primary (Intel support knowledge base) — **this one was retrieved and read directly.** It gives the **Xe-HPG (Intel Arc A-Series)** XMX row as `FP16 / BF16 / INT8 / INT4 / INT2`, and lists **Intel Arc B-Series Graphics (Xe2)** in its product set. Localized mirror, also supplied: [Intel 中国 — Intel AI 引擎与支持的数据类型](https://www.intel.cn/content/www/cn/zh/support/articles/000098346/graphics.html).
- [Intel — Unified Joint Matrix SYCL extension (IXPUG take-out)](https://www.intel.com/content/www/us/en/developer/articles/technical/ixpug-sycl-joint-matrix.html) — primary (Intel technical article on the unified `joint_matrix` extension; the extension side of the mapping layer).
- [Intel community blog — Architecting for Accelerators: Intel AMX and Intel XMX](https://community.intel.com/t5/Blogs/Tech-Innovation/Artificial-Intelligence-AI/Architecting-for-Accelerators-Intel-AMX-and-Intel-XMX/post/1481022) — vendor-hosted blog. Quoted as listing `U8, S8, U4, S4, U2, S2, INT8, FP16, BF16, and TF32`, and as the source for the TF32-exponent statement. **This page returned HTTP 403 to this environment and could not be read directly**; it is recorded as supplied, and vendor blog posts are **not** specification-grade evidence.
- [Intel — Intel Graphics Compiler, VISA `DPAS` instruction documentation](https://github.com/intel/intel-graphics-compiler/blob/master/documentation/visa/instructions/DPAS.md) — **the closest thing to a primary instruction-level source** for DPAS datatypes, in Intel's own compiler repository. *Not retrievable from this environment (host unreachable); recorded as a lead to read next.*
- [Intel XPU backend for Triton — hardware reference](https://github.com/intel/intel-xpu-backend-for-triton/blob/ae4b45b7a4b4a1c23480f0bfb676313e11248f50/.claude/reference/hardware-reference.md) — project reference (Intel, pinned revision).

### Confidence

**High for the DPAS primitive, for the "no direct convolution instruction" finding, for the operator-class guidance, and for the Xe-HPG datatype row. Medium for the Xe2/TF32 row. Low for the TF32-throughput remark.**

**Residual gap — still needs verification.** The following must not be read as settled by this record:

1. **There is no B580-specific datatype declaration behind the TF32 row.** The datatype statements available are: (a) a per-**product-family** table that covers **Xe-HPG (Arc A-Series)** and **lists Arc B-Series in its product set** without giving a B-Series datatype row; (b) a documentation sentence listing TF32 only as a type supported **"depending on hardware generation"**, without naming the generation; (c) a vendor **blog** post — *not* specification-grade evidence — listing TF32 among DPAS datatypes. **None of these is a statement that "the Arc B580 supports TF32 in XMX".** The source that would settle it is the vendor's **compiler-level `DPAS` instruction documentation** (`intel-graphics-compiler/documentation/visa/instructions/DPAS.md`), which **could not be retrieved from this environment**. **Porting decision that follows: do not assume TF32 on the B580** — verify it on the device (capability query, or a `joint_matrix` datatype test) before relying on it. The **confirmed** B580 datatype set is **FP16 / BF16 / INT8 / INT4 / INT2**.
2. **The "TF32 throughput is about half of BF16/FP16" remark is not confirmed.** No source read for this record states that ratio. It is marked **Low** confidence and should be treated as a lead, not a figure. The *direction* — that FP32-shaped GEMM is commonly run via BF16 decompositions (`bf16x2` / `bf16x3`) rather than a native FP32 path — **is** documented and is recorded above; **that path is B580-relevant independent of TF32**.
3. **The datatype article is scoped to Windows 10 / 11 and to a product-family matrix**, not to a driver-independent architecture statement. Its row is quoted as the vendor's own support statement, and no claim is made here that it is exhaustive.
4. **Several quoted bodies could not be re-read from this environment** (JavaScript-rendered documentation pages, an HTTP 403 blog, an unreachable code host). They are recorded as **supplied**, with that limitation stated at each citation, rather than presented as independently verified.

---

## G-02 — Is split-K reduction order constrained by any specification?

### Question as posed in the checklist

> **whether a primitive exists on the Intel side that can substitute for the semantics of `k_conv_splitk` (split-K convolution); whether the floating-point accumulation order of split-K reduction is constrained by a specification** — **this decides numerical reproducibility**

(`05` §8.1, G-02; affected scope stated there as **4 kernels**, k4, k7, k10, k18.)

### Finding

**No Intel specification was found that mandates a particular split-K reduction order.** Within the material consulted for this record, the split-K reduction order appears to be an **implementation freedom** — a choice made by the compiler or the library, not a behaviour fixed by a specification. No clause was found in the consulted sources that pins the accumulation order, and no such clause is claimed to exist.

**Consequence — state it plainly.** Split-K introduces a **floating-point accumulation-order dependence**. Therefore:

> **Numerical results are not bit-identical across different split factors.**

This is a property of floating-point summation combined with a free reduction order, not a defect of any particular implementation. The practical rule that follows:

> **Numerical consistency must be established by testing, not assumed from a specification.**

This holds for the port as a whole: `k_conv_splitk` (k10) is the kernel whose name points directly at the split-K reduction, and k4 / k7 / k18 are the convolution-plus-residual kernels in the same affected set. Any numerical agreement milestone involving these four must be measured, not derived.

### Citations

- [Intel oneAPI GPU Optimization Guide — Boost Matrix Multiplication Performance with Intel Xe Matrix Extensions (XMX)](https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2024-1/xmx.html) — primary (Intel documentation). Consulted for the split-K / reduction treatment; **it does not state a mandated accumulation order**.
- [oneDNN — convolution / split-K primitives documentation](https://www.intel.com/content/www/us/en/docs/onednn/developer-guide-reference/2025-0/data-types-001.html) — primary (Intel oneDNN Developer Guide). Consulted as the library-level source for the convolution and split-K path.
- [oneDNN — Data Types](http://oneapi-src.github.io/oneDNN/v1/dev_guide_data_types.html) — primary (project documentation) for the data-type context in which split-K runs.

### Confidence

**Medium.**

**Residual gap — still needs verification.**

1. **oneDNN's internal split-K reduction strategy was NOT confirmed from a primary source.** How oneDNN orders the partial sums internally, and whether it is stable across shapes, drivers or versions, is **still needs verification**. This record does not assert that oneDNN's order is unspecified; it asserts that no primary source stating it was located, and that no specification mandating an order was found.
2. **"No specification mandates the order" is a negative result and carries the corresponding limitation.** The consulted set was the checklist's own direction of verification (`05` §8.1 G-02: oneDNN convolution / split-K chapters, the oneAPI Level Zero specification, the SYCL 2020 floating-point reduction-order clauses). A negative result over a finite consulted set is **not** a proof of absence across all Intel specifications; it is recorded as a lead with its search range stated.

---

## G-03 — Swin window / shift primitives

### Question as posed in the checklist

> **whether Intel Xe provides the window / shift class primitives required by the Swin transform; the feasible interval of the `swin_var` window parameters (32/64/128/256) on the Xe side**

(`05` §8.1, G-03; affected scope stated there as **8 kernels**, k0, k1, k2, k29–k33.)

### Finding

**There is no dedicated hardware primitive for Swin's window partition or cyclic shift.**

Swin's window partition and cyclic shift are **data movement and re-indexing** operations — reshape, roll, slice. They are a **memory-access-pattern problem, not a matrix-multiply problem**, and therefore they **do not map to XMX**. Neither operation is a candidate for DPAS; there is nothing to accumulate.

**What does map to XMX is the attention matrix multiplies that follow.** Once the window partition has produced its tiles, the window-attention computation contains the two matrix multiplies — **QK^T** and the **AV weighted sum** — and *those* are XMX DPAS candidates, subject to the precision constraints recorded under G-01 (the data type must be supported, and the operation must go through a mapping layer).

**Practical note — the shift can often be fused into the tile load.** Because the shift is an index computation over otherwise contiguous data, it can frequently be performed **at load time**, by computing the source index during the tile load, rather than requiring a separate kernel pass over the data. Fusing it this way removes the intermediate buffer and the extra launch; whether it is profitable for a given tiling is an implementation decision, not a hardware constraint.

**Recommendation for the mapping table.** Swin-related kernels should be described as **two sub-items** rather than one, because the two halves have different hardware targets:

| Sub-item | Operation | Target | XMX applicable |
|---|---|---|---|
| **(a)** | window shift / partition | **vector engine / DMA** | **not applicable** |
| **(b)** | window attention matmuls (QK^T, AV) | **XMX DPAS candidates** | **yes, subject to precision constraints** |

The affected set (k0, k1, k2, k29–k33) contains both halves; the mapping table in `05` §3.2 lists each kernel as a single row with a single `XMX direct support` cell. Under this finding, a single cell cannot represent a Swin kernel correctly.

### Citations

- [Intel oneAPI GPU Optimization Guide — Boost Matrix Multiplication Performance with Intel Xe Matrix Extensions (XMX)](https://www.intel.com/content/www/us/en/docs/oneapi/optimization-guide-gpu/2024-1/xmx.html) — primary (Intel documentation): consulted for what the XMX path accelerates.
- ['xegpu' Dialect — MLIR documentation](https://mlir.llvm.org/docs/Dialects/XeGPU/) — primary (LLVM/MLIR documentation). Documents the XeGPU dialect as modelling the Xe GPU ISA's special instructions — **DPAS and 2D block load and store** — and its tile-based programming model. This is the primary evidence that the matrix-multiply path and the block-load path are *separate* mechanisms, and that the block-load path is the load/data-movement side; there is no window or shift primitive in the dialect's operation list.
- [Intel XPU backend for Triton — hardware reference](https://github.com/intel/intel-xpu-backend-for-triton/blob/ae4b45b7a4b4a1c23480f0bfb676313e11248f50/.claude/reference/hardware-reference.md) — primary project reference, consulted for the Xe hardware surface.

### Confidence

**Medium-high for "no dedicated window/shift primitive exists; these are data-movement operations". Medium for the fusion guidance.**

**Residual gap — still needs verification.**

1. **The feasible window-parameter interval (32 / 64 / 128 / 256) on the Xe side is NOT answered.** The checklist asked this in the same item, and this record does not answer it. What bounds a window size on Xe is a combination of SLM capacity, work-group size and the tiling the compiler chooses; the relevant external items are G-06 (per-Xe-core SLM limit) and G-48 (maximum work-items per work-group), both of which remain open in `05` §8. **The window interval therefore stays open.**
2. **The claim that these operations do not map to XMX is an argument from the primitive's semantics** (a re-indexing operation has no multiply-accumulate to map), supported by the absence of any such operation in the XeGPU dialect's documented operation list. It is not a hardware measurement.

---

## G-04 — Feasibility boundary of the generic SPIR-V path

### Question as posed in the checklist

> **the feasibility and performance boundary of the generic SPIR-V path (non-XMX) for this workload**

(`05` §8.1, G-04; affected scope stated there as **all 34**.)

### Findings

#### (a) `SPV_INTEL_joint_matrix` was removed from MLIR/LLVM

**Merged PR #102332, August 2024**, drops support for `SPV_INTEL_joint_matrix`. The approving note on the commit thread states that **SPIR-V joint matrix merged into SPIR-V cooperative matrix at the Khronos level**, and that the project **is moving to cooperative matrix internally** — which is why SYCL joint matrix support is being removed.

**Consequence.** A hand-written **`SPV_INTEL_joint_matrix` path is not viable**: the extension is withdrawn and the compiler support for it has been deleted upstream. **The current path is `SPV_KHR_cooperative_matrix`.**

*Citations — both primary:*

- [MLIR commit thread — `[mlir][spirv] Drop support for SPV_INTEL_joint_matrix (PR #102332)`, 8 August 2024](https://lists.llvm.org/pipermail/mlir-commits/2024-August/068330.html) — primary (the merged-commit notification and its approving review note).
- [llvm/llvm-project PR #102332](https://github.com/llvm/llvm-project/pull/102332) — primary (the pull request itself).

*Confidence:* **High.**

#### (b) Intel's XeGPU dialect models Xe instructions and has a documented lowering path to SPIR-V

The MLIR **XeGPU dialect** "closely models a subset of the Xe GPU's ISA", and its operations are introduced **for special Xe instructions not modelled by the LLVM/SPIR-V dialect, such as DPAS and 2D block load and store**. It is documented as **a bridge dialect in the MLIR gradual lowering process**, and the lowering path **XeGPU → SPIR-V** is the documented route.

**The referenced IMEX GEMM end-to-end tests covered FP16 and BF16 only** — not TF32, not FP64. This is cited **as reported**.

*Citations:*

- ['xegpu' Dialect — MLIR documentation](https://mlir.llvm.org/docs/Dialects/XeGPU/) — primary (LLVM/MLIR documentation) for the dialect's purpose, its DPAS and 2D block load/store modelling, and its role as a bridge dialect in the gradual lowering process.
- [Intel MLIR extensions (IMEX) — releases](https://github.com/intel/mlir-extensions/releases) — primary project source, consulted for the XeGPU → SPIR-V lowering path and the IMEX GEMM end-to-end tests.

*Confidence:* **High for the dialect's existence, purpose and lowering path. The FP16/BF16-only test scope is reported (not independently verified).**

*Residual gap — still needs verification:* the **FP16/BF16-only** scope of the IMEX GEMM end-to-end tests is recorded **as reported**. It was not traced to the test sources themselves for this record. It must not be upgraded to "the XeGPU GEMM path supports only these types" — the tests' coverage and the path's capability are different claims, and only the former is being reported.

#### (c) Reported driver-level SPIR-V compatibility problems on Intel

There is a **report that Slang-generated SPIR-V produced a null pipeline handle on Iris Xe, while GLSL-generated shaders worked**. The implication is that the **SPIR-V producer choice can affect usability on Intel** — the same target, the same API call, different results depending on which toolchain emitted the module.

This is recorded as a **reported community finding**, and explicitly **not** an Intel statement. It is not a statement about DPAS, cooperative matrix, or XMX; it is a statement about SPIR-V module acceptance by the Intel driver.

*Citation:*

- [Intel Community — "Driver returns VK_SUCCESS on vkCreateGraphicsPipelines, but sets the pipeline to VK_NULL_HANDLE"](https://community.intel.com/t5/Graphics/Driver-returns-VK-SUCCESS-on-vkCreateGraphicsPipelines-but-sets/m-p/1721264) — **secondary / community report (not an Intel statement)**.

*Confidence:* **Low — reported (not independently verified).**

*Residual gap — still needs verification:* the report is a single community thread, it concerns the **graphics** pipeline path rather than compute, and it was not reproduced. **It is recorded as a lead, not as evidence about the compute SPIR-V path.** It is included because it supports a *procedural* conclusion — prefer official producer paths — not because it establishes a defect.

#### (d) ISPC can emit SPIR-V for Xe, but requires the `xe64` architecture

ISPC targets Xe GPUs and emits SPIR-V by default for those targets (`--target=xehpg-x8`, `--emit-spirv`). The ISPC for Xe documentation states:

> "When targeting Xe targets, **xe64 architecture must be used**. It corresponds to 64-bit host and has 64-bit pointer size. **We don't support 32-bit pointers for Xe targets.**"

*Cited as reported* — that is, quoted from the ISPC for Xe project documentation.

*Citation:*

- [Intel ISPC for Xe](https://ispc.github.io/ispc_for_xe.html) — primary project documentation (the ISPC project's own Xe guide), quoted directly.

*Confidence:* **High for the quoted statement (it is a direct quotation from the project's own documentation).**

*Residual gap:* none material. Note only that this is the project's own statement of its constraint, not an independent evaluation of ISPC's suitability for this workload.

### Practical guidance for the generic SPIR-V path

**Prefer official paths.** Three routes are supported and documented:

1. **SYCL `joint_matrix`** — the documented, unified extension route.
2. **oneDNN library calls** — the library route, which maps operations onto DPAS internally.
3. **MLIR XeGPU → SPIR-V** — the compiler route, via the bridge dialect.

**Avoid depending on the withdrawn Intel-proprietary extension.** A hand-written `SPV_INTEL_joint_matrix` path has no upstream compiler support and no forward path; `SPV_KHR_cooperative_matrix` is where the capability now lives.

### Confidence (item summary)

**High** for (a), (b) as to the dialect and lowering path, and (d). **Low / reported** for (c). **Reported** for the FP16/BF16-only test scope in (b).

---

## Summary table

| Item | Question | Finding | Confidence | Residual gap |
|---|---|---|---|---|
| **G-01** | Does XMX provide directly callable matrix-multiply / convolution primitives, and what precision modes are covered? | The primitive is **DPAS** (dot-product-accumulate, `D = C + A×B`); **no direct convolution instruction**. Convolution / matmul are accelerated by **mapping onto DPAS** (e.g. oneDNN, default-on for Xe 4th-gen and later; or `joint_matrix_mad`). Precision: **FP16 / BF16 / INT8 / INT4 / INT2** on Xe-HPG (**confirmed**); **TF32** is a **later-generation** addition (**reported, not confirmed**). FP32-shaped GEMM has a **documented approximate path** via `bf16x2` / `bf16x3`. Acceleration is **not automatic** — the data type must be supported and the op must go through a mapping layer. Only compute-intensive, matmul-decomposable ops are candidates; elementwise / reduction / softmax / transpose are **not** XMX candidates. | **High** (primitive, mapping guidance, Xe-HPG row); **Medium/Low** (Xe2/TF32 row and the TF32 throughput remark) | **No single authoritative per-generation table located.** The Xe-HPG row is confirmed; **"TF32 on Xe2" stays reported** pending Intel's compiler-level `DPAS` instruction documentation. The "TF32 ≈ half BF16 throughput" figure is **unconfirmed** and marked Low. |
| **G-02** | Does a primitive substitute for split-K convolution exist, and is the split-K reduction accumulation order spec-constrained? | **No Intel specification was found mandating a particular split-K reduction order**; it appears to be an implementation freedom. Split-K introduces a floating-point accumulation-order dependence, so **results are not bit-identical across split factors**; **numerical consistency must be established by testing, not assumed from a spec.** | **Medium** | **oneDNN's internal split-K reduction strategy was NOT confirmed from a primary source.** The "no specification mandates it" result is a **negative result over the consulted set**, not a proof of absence. |
| **G-03** | Does Xe provide the window / shift primitives Swin needs, and what is the feasible window interval (32/64/128/256) on Xe? | **No dedicated hardware primitive** for window partition / cyclic shift; these are **data movement and re-indexing** (reshape / roll / slice) — a memory-access-pattern problem, **not** a matmul problem, so **not XMX-mappable**. The **attention matmuls that follow (QK^T, AV) are XMX DPAS candidates**. The shift can often be **fused into the tile load**. Recommend describing Swin kernels as **two sub-items** in the mapping table: (a) shift/partition → vector engine / DMA, XMX N/A; (b) attention matmuls → XMX candidates subject to precision constraints. | **Medium-high** (no primitive / data movement); **Medium** (fusion guidance) | **The feasible window-parameter interval on Xe is NOT answered** — it depends on the still-open items G-06 (per-Xe-core SLM limit) and G-48 (max work-items per work-group). The "no XMX mapping" claim is an argument from primitive semantics plus the absence of such an op in the XeGPU dialect, not a hardware measurement. |
| **G-04** | What is the feasibility and performance boundary of the generic SPIR-V path for this workload? | (a) **`SPV_INTEL_joint_matrix` was removed from MLIR/LLVM** (merged PR #102332, Aug 2024); the approving note states joint matrix **merged into cooperative matrix at Khronos** and the project is moving to cooperative matrix internally ⇒ a hand-written `SPV_INTEL_joint_matrix` path is **not viable**; the current path is **`SPV_KHR_cooperative_matrix`**. (b) The MLIR **XeGPU dialect** models Xe instructions (DPAS, 2D block load/store) with a documented **XeGPU → SPIR-V** lowering path; the referenced IMEX GEMM end-to-end tests covered **FP16 / BF16 only**. (c) **Reported** driver-level SPIR-V compatibility problems on Intel (Slang-generated SPIR-V → null pipeline handle on Iris Xe while GLSL worked), so the **SPIR-V producer choice** can affect usability. (d) **ISPC** can emit SPIR-V for Xe but requires the **`xe64`** architecture (64-bit pointers) and does **not** support 32-bit pointers. **Guidance:** prefer official paths (SYCL `joint_matrix`, oneDNN, MLIR XeGPU → SPIR-V); avoid the withdrawn Intel-proprietary extension. | (a) **High**; (b) **High** for the dialect/lowering, **reported** for the FP16/BF16-only test scope; (c) **Low — reported**; (d) **High** (direct quotation) | (b) The **FP16/BF16-only** test scope is **reported (not independently verified)** and must not be generalised to the path's capability. (c) The driver report is a **single community thread**, concerns the **graphics** path, and was not reproduced; treat as a lead. |

---

## How this changes the checklist

**These four items move.** They can move from **"needs external documentation"** to **"answered by external evidence (with residual gaps noted)"**:

| Item | Was (`05` §8.1) | Now |
|---|---|---|
| **G-01** | no conclusion given | **answered by external evidence**; residual gap on the Xe2/TF32 row and the TF32 throughput remark |
| **G-02** | no conclusion given | **answered by external evidence** (medium confidence); residual gap on oneDNN's internal split-K strategy |
| **G-03** | no conclusion given | **partially answered**: the primitive question is answered; the **window interval remains open** |
| **G-04** | no conclusion given | **answered by external evidence**; residual gaps on the IMEX test scope and the driver report |

The move is a move of *classification*, not of *strength*. Each item carries its residual gaps forward, and none of these findings is this project's own measurement.

**The remaining checklist items should be re-classified by one question:**

> **Can this operator be decomposed into a matrix multiply?**

This replaces the previous approach of hunting for a **per-operation hardware primitive**. The reason is now established rather than assumed (G-01): **XMX only executes DPAS** — a dot-product-accumulate, `D = C + A×B`. There is no per-operator acceleration surface to search for. Consequently:

> **All matmul-class operators ultimately take the same path.**

Convolution, QKV projection, attention matmuls, feed-forward transforms and window attention — different names, different tile shapes, different memory layouts — all arrive at DPAS or they do not arrive at XMX at all. That collapses the mapping question from "which primitive does operator X need?" into a three-way split:

| Class | Test | Xe path |
|---|---|---|
| **matmul-class** | decomposable into a matrix multiply | **XMX DPAS** (subject to data-type support and a mapping layer) |
| **data-movement** | re-indexing / re-layout / partition / shift | **vector engine / DMA** — window shift and partition belong here (G-03) |
| **vector-class** | elementwise, reduction, softmax, transpose | **vector engine path** — never XMX candidates (G-01) |

Two further consequences for downstream work:

1. **The `XMX direct support` column of the 34-row operator mapping table (`05` §3.2) should be rewritten in these terms** — as a *decomposability* judgement against the three classes above, rather than as a pending per-kernel external lookup. For the Swin kernels (k0, k1, k2, k29–k33), that means **two sub-items per kernel** rather than one cell (G-03).
2. **Numerical milestones involving the split-K / convolution family (k4, k7, k10, k18) must be measurement-based.** G-02 removes the possibility of deriving bit-identity across split factors from a specification, so any numerical-agreement criterion must be tested — and this project cannot run that test here (no hardware, no toolchain).

**What this document is not.** It is not a verification result, and it is not a change to `docs/04` or `docs/05`. It supplies external answers to four previously-open questions, each with its citation and each with its residual gap named.
