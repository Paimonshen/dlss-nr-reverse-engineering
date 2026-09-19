# DLSS NR 逆向工程研究（AMD 模块 → Intel Arc 可行性）

本仓库是对 **AMD 侧 DLSS NR 模块**（`dlssnr_amd_pass1.dll`）的**独立静态逆向工程研究**成果，目标是回答一个具体的互操作性问题：

> **能否把 DLSS NR 从 AMD HIP（`amdgcn`）侧重编/移植到 Intel Arc（Xe / XMX）上运行？**

研究结论、未解缺口与所需外部资料均在文档中如实记录，**不隐瞒限制**。

---

## 仓库内容

| 目录 | 内容 |
|---|---|
| [`docs/`](docs/) | 六份分析文档：项目背景、方法论、DLL 结构分析、34 内核参数规格、Intel 可行性评估、未解缺口与限制 |
| [`tools/`](tools/) | 三个可复用的只读分析工具：PE 解析器、AMDGPU msgpack 元数据提取器、通用字节扫描器 |
| [`team-methodology/`](team-methodology/) | 本研究所用的协作方法论：多智能体协作流程、质量门禁与验收链、已确立的定规 |
| [`binaries/`](binaries/) | 第三方二进制（经 Git LFS 跟踪），用于复现分析；来源与许可见 [`EXTERNAL_BINARIES.md`](EXTERNAL_BINARIES.md) |

## 快速开始

```bash
git clone <this-repo>
cd <this-repo>

# 二进制用 Git LFS 跟踪，克隆后请确保拉取真实内容
git lfs install
git lfs pull
```

### 复现分析（示例）

```bash
# 1) 查看 DLL 的节表、导出表、导入表、重定位与异常表
python tools/pe_parser.py binaries/dlssnr_amd_pass1.dll --sections --exports --imports
python tools/pe_parser.py binaries/dlssnr_amd_pass1.dll --reloc
python tools/pe_parser.py binaries/dlssnr_amd_pass1.dll --pdata | head

# 2) 提取 HIP fat binary 内的 AMDGPU 内核元数据（8 个 device 目标 × 34 内核）
python tools/msgpack_extract.py binaries/dlssnr_amd_pass1.dll --json out/kernels.json

# 3) 扫描字节模式 / 统计权重载荷的字节分布
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --hex "44 4C 53 53 4E 52 57 31"
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --byte-histogram --range 0x1629:end
```

三个工具均为**只读**：除显式指定的输出路径外不写入任何文件。依赖 `pefile`、`msgpack`，Python 3.11+。详见 [`tools/README.md`](tools/README.md)。

## 主要发现（摘要）

### 模块形态
- `dlssnr_amd_pass1.dll` 是一个 **`version.dll` 代理**：17 个导出**全部是 `version.dll` 的 API 名**，每个是一段 16 字节 `FF 25` 跳转桩。
- 导入面共 **194 条 / 10 个 DLL**，其中 `amdhip64_7.dll` **29 条**为 HIP API；其余为系统与图形侧。
- 文件 **7,156,224 字节**，PE32+，12 个节。

### 设备代码
- `.hip_fat` 内为 clang offload bundle（魔数 `__CLANG_OFFLOAD_BUNDLE__`），含 **9 个 bundle = 1 个 host 占位 + 8 个 device 目标**，**全部为 `amdgcn-amd-amdhsa`**。
- 每个 device 目标含 **34 个内核**；内核元数据（kernarg 布局、资源字段）可完整解析。
- 8 个目标间 **16 个资源字段中有 8 个不一致**；`wavefront_size` 在目标 #1–#7 为 32、在 #8 为 64。

### 内核与分派
- **34 个内核名可静态恢复**，来自 kernel 注册调用的实参。
- 两张 **8 字节步长**的函数指针表（位于 `.rdata`），**注册调用与表槽位的配对为 34/34**，可回溯到「内核名 ↔ 包装函数 ↔ 表槽位」。
- **`71 block` 的枚举上界未定**：该数字仅见于文档转述；`block` 重编号逻辑有 4 处内联副本，均位于调度函数之外；**逐 block → kernel 的分派未见实现**。

### 权重容器
- `dlssnr_on_amd_weights.bin`（147,689,451 字节）容器**已完整解析**：
  `8B 魔数 "DLSSNRW1"` + `uint32` 条目数(153) + `uint32` 索引区结束偏移(0x1629) + 153 条变长描述符 `(uint8 nameLen, name, uint64 offset, uint64 size)` + 连续载荷区(147,683,778 字节)。
- 三条恒等式闭合到 0。**容器内不含 `shape` / `dtype` / 算子类型 / `block` 索引 / `kernel` 名五类字段**，且**无第二张表 / 无隐藏元数据区**（索引区逐字节归属：未归属 = 0）。

### Intel Xe 可行性
- 34 内核分类：**A 类 7 / B 类 20 / C 类 7**（阈值为此研究自设，非规范值）。
- 资源面最大 `group_segment_fixed_size` = **64,640 字节**，距 64 KiB 上限 **896 字节**。
- host 侧 **需替换 29 / 194 = 14.9%**（全部为 `amdhip64_7.dll`）。
- 路线图 **S0–S7 八阶段 + 23 个里程碑**。

## 未解缺口（诚实声明）

- **「层 → kernel 绑定」不可取得**：四条路径全部封死 —— ① DLL 静态分析已到边界；② 工作区内源码为空壳且与 DLL 不同构；③ 权重文件已穷尽（无相关字段、无第二张表）；④ **运行期观测不可用**（本环境无 AMD 硬件）。
- **`VarParams`（168 字节）内部布局** 与 **`SwinParams`（40 字节 `by_value`）内部构成** 未解。
- `71` 的上界与 `block` 重编号的语义边界未定。
- 涉及 Intel Xe / SPIR-V / XMX 的具体能力问题，文档中**一律标注为「需查外部资料」**，未作推断。

详见 [`docs/06-未解缺口与限制.md`](docs/06-未解缺口与限制.md)。

## 法律与许可

- 第三方二进制的来源、许可与用途见 [`EXTERNAL_BINARIES.md`](EXTERNAL_BINARIES.md)。
- 项目性质、权利主张、移除承诺见 [`LEGAL.md`](LEGAL.md)。
- 原创内容（文档、脚本）的许可证**待所有者选定**，见 [`LICENSE`](LICENSE)。

**本仓库为互操作性研究，不包含任何规避 DRM 的代码，也不包含 NVIDIA 的任何受版权保护的二进制。**
