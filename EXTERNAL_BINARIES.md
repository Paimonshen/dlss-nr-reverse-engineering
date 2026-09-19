# 外部二进制清单（EXTERNAL_BINARIES）

本仓库收录的第三方二进制文件均为**公开分发渠道**获得的文件，用于互操作性研究。**本仓库不对其主张任何权利**，版权归各自所有者。详见 [`LEGAL.md`](LEGAL.md)。

所有文件均通过 **Git LFS** 跟踪（见 [`.gitattributes`](.gitattributes)）。

---

## 1. `binaries/dlssnr_amd_pass1.dll`

| 项 | 值 |
|---|---|
| 文件名 | `dlssnr_amd_pass1.dll` |
| 大小 | 7,156,224 字节 |
| SHA256 | `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| 来源 | OptiScaler AMD PreSR Multipass 公开发布包（`OptiScaler-AMD-PreSR-Multipass-v1.7.3.zip`）中的 `dlssnr_amd_pass1.dll` |
| 原始许可证 | 随 OptiScaler 分发；版权归 OptiScaler 项目及其上游作者所有 |
| 用途 | 本项目的主要分析对象：一个 `version.dll` 代理模块，内含 HIP 设备代码（`amdgcn`）与 kernel 注册逻辑 |

## 2. `binaries/dlssnr_amd_pass2.dll`

| 项 | 值 |
|---|---|
| 文件名 | `dlssnr_amd_pass2.dll` |
| 大小 | 7,156,224 字节 |
| SHA256 | `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| 来源 | 同上发布包 |
| 原始许可证 | 同上 |
| 用途 | 与 `pass1` 对照分析 |

> **注意（重要）**：`pass2.dll` 与 `pass1.dll` 在字节层面**完全相同**（SHA256 一致）。经逐字节比对，同发布包中的三个 `pass*.dll` 互为同一文件，**并非三个不同的处理阶段**。此处保留三份文件名是为了忠实反映发布包结构。

## 3. `binaries/dlssnr_amd_pass3.dll`

| 项 | 值 |
|---|---|
| 文件名 | `dlssnr_amd_pass3.dll` |
| 大小 | 7,156,224 字节 |
| SHA256 | `3C9CA13F0F5FC36A690BA424C457003BCFCC1080B4B785974CDD7E9AE2BC1DD8` |
| 来源 | 同上发布包 |
| 原始许可证 | 同上 |
| 用途 | 与 `pass1` 对照分析 |

> **注意**：与 `pass1.dll` / `pass2.dll` **逐字节相同**（同一 SHA256）。见上条说明。

## 4. `binaries/dlssnr_on_amd_weights.bin`

| 项 | 值 |
|---|---|
| 文件名 | `dlssnr_on_amd_weights.bin` |
| 大小 | 147,689,451 字节 |
| SHA256 | `6BF8DC931EF3CCFFE18C82DE26AB374156E7F19539FFCF8EABAA25DCA5CF15AB` |
| 来源 | 同为 OptiScaler AMD 分发工程中的权重文件（工程内路径 `Engine/weights/`） |
| 原始许可证 | 随上游工程分发；版权归上游作者所有 |
| 用途 | 神经渲染网络的权重容器本体。其容器结构已在本仓库文档中完整解析（见 `docs/05-Intel可行性评估.md` 与 `docs/04-内核参数规格.md`） |

> **容器格式（供复现，来自本项目分析）**：`8 字节魔数 "DLSSNRW1"` + `uint32` 条目数(153) + `uint32` 索引区结束偏移(0x1629) + 153 条变长描述符 `(uint8 nameLen, name, uint64 offset, uint64 size)` + 连续载荷区(147,683,778 字节)。三条恒等式闭合到 0。

## 5. `binaries/OptiScaler/OptiScaler.dll`

| 项 | 值 |
|---|---|
| 文件名 | `OptiScaler.dll` |
| 大小 | 25,961,472 字节 |
| SHA256 | `061F15F86671772A278B69B744355E203EFF9A929A360E225F7B3DC8491F7186` |
| 来源 | OptiScaler 公开发布包 v1.7.3（`OptiScaler-v1.7.3` 目录） |
| 原始许可证 | 版权归 OptiScaler 项目及其作者所有 |
| 用途 | 上游加载器/代理组件，用于理解 `dlssnr_amd_pass*.dll` 的加载与调用上下文 |

---

## 未收录（明确排除）

| 文件 | 原因 |
|---|---|
| `nvngx_dlssnr.dll`（NVIDIA 原版） | **NVIDIA 受版权保护的二进制**，不在本仓库收录范围（见 `LEGAL.md` 第 8 条） |
| 任何 API key / token / 凭证 | 与本研究无关，且不得公开 |
| 第三方 SD 分析工具（反汇编库等） | 非本项目产出，通过正常依赖渠道获取 |

## 完整性校验

下载后可用如下命令核对每个文件的 SHA256（与上表逐一比对）：

```bash
# 逐个文件
sha256sum binaries/dlssnr_amd_pass1.dll
sha256sum binaries/dlssnr_on_amd_weights.bin
sha256sum binaries/OptiScaler/OptiScaler.dll

# 或在仓库根目录批量生成清单（需 Git LFS 已拉取真实内容）
find binaries -type f -print0 | xargs -0 sha256sum
```

> 若使用 Git LFS，克隆时请确保 LFS 内容已拉取（`git lfs pull`），否则上述哈希对应的是 LFS 指针文件而非真实内容。
