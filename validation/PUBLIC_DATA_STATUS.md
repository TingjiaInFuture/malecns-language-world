# 公开数据接入实录（2026-09-14 第六轮更新）

本记录基于当前 Windows 工作区的实际下载与检查。总体为部分完成；生理闭环未验收。另一会话的 `/mnt/data/` 路径不是本机资产。

## 2026-09-14 第六轮：开放项收尾

- **Dallmann 2025 补充表 2**（`41586_2025_9554_MOESM4_ESM.xlsx`，Springer 开放 URL）已落库（`data/physiology_raw/feco-author/`，含 SHA-256 回执）：MANC chief 9A/DNg74/DNg100/DNg12 逐细胞 ID 与 hook=SNpp38 类型 → 经官方注释映射到 22 个 MaleCNS 身份（见 `validation/feco-identity.json`）。逐细胞 club ID 未发表于任何连接组（定案）。
- **Azevedo 逐类解剖工作簿** `MN_anatomy_confocal_measurements.xlsx` 已下载校验（发布者 SHA-256 匹配），逐类解剖汇总入 `validation/mn-anatomy-classes.json`。
- **前瞻预注册评估数据**：Mamiya2018 系 hook_flexion/claw/club parquet 均下载校验；hook_extension_magnet.parquet 已下载校验但其动物数 <5 不满足冻结划分规则。协议（SHA `0f6c28…`）先于数据冻结；评估结果 2 过 1 败 1 不可评（见 `validation/feco/prospective-results.json`），失败如实保留。
- 运动试次首包 `180222_F1_C1.zip` 已完成实测标定（中间类细胞 Rin 188.4 MΩ 等，见 `validation/motor-trial-analysis.json`）。

## 2026-09-14 第五轮：Dryad token 投入使用，FeCO 原始数据取得并运行

- 用户 Dryad token 经环境变量 `DRYAD_API_TOKEN` 传入（仅作请求头；重定向到资产存储时自动剥离 Authorization，避免向第三方主机泄漏）。6 个 FeCO 资产全部 `downloaded_verified`：`hook_flexion_01_magnet.parquet`（15 MB，发布者 SHA-256 `d4a8c10f…` 精确匹配）、`manc_v1_classifications.csv`、`manc_v1_connectivity.parquet`、`fanc_dn_information.csv`、`rna-seq.xlsx`、Dryad `README.md`。
- 实测结构核实（运行适配器前）：320,154 行 × 14 列；7 只动物、12 试次；200 Hz；驱动 R21D12（hook flexion 传入）；`L1C_flex` 单位度（2.5–179.7）；`analyze` 0/1；`predicted_calcium` 列存在但从未读取。
- `experiments.feco` 首次实跑（`validation/feco/sensory-results.json`、`feco-run-status.json`）：按动物冻结划分（动物身份先于目标读取）、训练集仿射校准 gain=40.48/offset=−1.23；**保留集 test 动物 4/4 试次 MSE 低于恒定基线**（例：动物 5 为 49.6 vs 98.1）。无预注册阈值，回溯性分析，`biological_acceptance=false`；不称盲测。
- `manc_v1_classifications.csv` 只有粗类（intrinsic/sensory/…），不含 FeCO 亚型名；FeCO club/hook/claw→MaleCNS 逐细胞身份仍开放。**运动侧试次包已开始选拉**：最小 zip `180222_F1_C1.zip`（200 MB）已下载并通过发布者 SHA-256（`c904f41…6e33`）；结构核实：IClamp 电流阶跃协议、10 kHz、62.5/125/250 pA、0.42 s 扫描、338 个条目，轨迹为 scipy 可读的纯数值矩阵（1240×70），细胞笔记 Table 为 MCOS（需 mat73/MATLAB）。见 `validation/motor-trial-acquisition.json`。**其余 49 个 zip（~48 GB）的批量选拉在 v1.0.0 定版时中止**：Merritt 资产主机对所有连接施加约 12 KB/s 的服务端限速（并发 Range 请求各自同速，单连接需 ~10 小时/包）；未保留任何部分下载。token 流程不变，日后可重试。

## 2026-09-14 第四轮：Dryad 障碍定性与突触级官方数据

- **Dryad 403/401 的根因是政策，不是故障**：Dryad API v2（服务器 `x-api-version: 2.1.0`）对匿名用户明确禁止下载文件字节（官方 API 页声明"Anonymous users ... are not allowed to download data files"）；`/api/v2/files/{id}/download` 返回 401"must have current bearer token"；网页端 `/downloads/file_stream/{id}` 受 Anubis 质询保护。第三方下载器（datahugger-ng 等）同样要求 token。
- **合法获取路径（已核实）**：在 datadryad.org 用 ORCID 免费注册 → 个人资料页 "Create a Dryad API account" 获得 client_id/secret → `POST https://datadryad.org/oauth/token`（grant_type=client_credentials）换取 10 小时有效的 access token → 携带 `Authorization: Bearer <token>` 访问 `stash:download` 链接。`experiments/public_data.py` 已支持 `DRYAD_API_TOKEN` 环境变量（token 不写入任何回执/报告）。没有镜像（Zenodo/OSF/figshare 均无；作者仓库明确 Dryad 为唯一分发点）。
- **MaleCNS 突触级数据公开存在**（此前未接入）：官方桶 `gs://flyem-male-cns/v1.0/connectome-data/flat-connectome/` 下 `syn-points`（12.7 GB，逐突触 x/y/z/body/kind/ROI）、`syn-partners`（6.8 GB，伙伴对+conf_pre/conf_post/primary_post）、`tbar-neurotransmitters`（2.7 GB）与 `body-stats`（780 MB）可经 HTTPS 免认证下载；本轮以 `download_data.py --profile all-tables` 启动（校验与断点续传内建）。neuPrint `male-cns:v1.0` 实例存在但 API 需另行注册 token。
- 论文仓库 `flyconnectome/2025malecns/supplemental_data` 的三份逐 ROI 质量 CSV（tbar 精度/召回、连接精度/召回、traced-synapse-capture）已下载到 `data/raw/quality/`，例如 ME(R) 0.823/0.902、LegNp(T1)(R) 0.706/0.907——这将用于交叉核对自算 ROI 审计。
- 论文定位修正：FeCO 数据集对应 Dallmann 等 2025, Nature 647:445–453（doi:10.1038/s41586-025-09554-2）；运动数据集为 Azevedo 等 2020, eLife 9:e56754（此前误记 2022/Nature 系）。FeCO 首选文件发布者 SHA-256 不变（`d4a8c10f…80abd`），等待 token 后下载验证。

## 已取得的资产

- MaleCNS 官方注释已在本地；保持 `male-cns:v1.0` 身份。7 个左前腿胫节运动候选来自官方注释，不是正式生产接口。
- [MANC 论文](https://elifesciences.org/articles/96084)的实际下载文件是 `elife-96084-supp3-v1.csv` 和 `elife-96084-supp6-v1.csv`。两表已保存于 `data/physiology_raw/manc/`，下载回执含 URL、字节数和本地 SHA-256；源站未提供独立 SHA-256，不能声称经过发布者哈希验证。
- [FeCO 作者仓库](https://github.com/chrisjdallmann/feco-inhibition)的数据说明、观测滤波 MATLAB 源码和配置已下载。它们是说明和代码，没有实测钙活动文件。
- [运动实验相关 Zenodo 记录](https://zenodo.org/records/4527659)的 README、探针标定及 force-per-spike 分析入口已保存于 `data/physiology_raw/motor-author/`。3 个文件均校验发布者 MD5，并记录本地 SHA-256。该 Zenodo 记录提供分析代码；没有取得原始细胞/试次压缩包。
- 两组 Dryad 版本和完整文件目录已保存于 `data/physiology_raw/*-catalog.json`，包括发布者摘要及字节数。

完整机器清单：`validation/public-data-availability.json`。下载失败项的 `local_path` 为 null。

**v1.0.1 封口说明**：逐 ROI 质量 CSV、Dallmann 补充表 2、运动解剖 xlsx 与已选试次 zip 的获取已并入 `experiments.public_data` 单入口（幂等、回执校验）；既有本地 CSV 的回执由提交的交叉核对证据哈希回填（回执内注明 bootstrap 来源）。运动试次 zip 的单流下载受 Merritt 每连接限速影响，大包耗时以小时计。

## 实际发现的身份问题

通过 MaleCNS 注释的 `mancBodyid` 字段关联，不把 MANC 数值 ID 当成 MaleCNS ID。所有结果保留为候选。

| MaleCNS ID | MANC ID | 检查结果 |
|---|---|---|
| 800636 | 12704 | Ti extensor MN 类型一致 |
| 807165 | 12134 | Ti flexor MN 类型一致，补充表6无对应行 |
| 809912 | 17133 | Ti flexor MN 类型一致 |
| 815344 | 10256 | 补充表3未找到身份 |
| 818057 | 15321 | Ti flexor MN 类型一致 |
| 819384 | 17885 | 类型冲突：MaleCNS 为 Ti flexor MN，MANC 为 Acc. ti flexor MN |
| 909831 | 14798 | Ti flexor MN 类型一致 |

7 个候选没有可用的补充表3匹配置信度数值；空值保持未知。类型一致不证明跨版本身份、外周侧别或实验 driver 对应；还需确认 MANC 引用版本。正式批准端口数仍为 0。

结果：`data/graph_neurons/interfaces/manc_lf_tibia_crosswalk.parquet`；逐行审核材料及源哈希：`validation/manc-crosswalk-evidence.json`。

## 原始记录的访问障碍（已于第五轮解除 FeCO 侧）

[FeCO Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.gqnk98t16)：已凭用户 token 下载并校验全部所选资产。[运动 Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.76hdr7stb)：48 GB 试次包未选拉，token 已可用、按需执行。没有使用凭据绕过或规避任何访问控制。

FeCO 首选文件 `hook_flexion_01_magnet.parquet` 的发布者字节数为 14,993,835，SHA-256 为 `d4a8c10f2700fe06f142da438e52797c99636fbbad2e1c04c1cc29c9fe080abd`，本地校验精确匹配；`validation/feco-run-status.json` 现记录 `run_retrospective_sensory_analysis`。

## 已实现的后续运行入口

在仓库根目录运行：

```powershell
.venv/Scripts/python.exe -m experiments.public_data
.venv/Scripts/python.exe -m interfaces.manc_crosswalk
.venv/Scripts/python.exe -m experiments.feco
.venv/Scripts/python.exe validation/run_realism.py
```

FeCO 入口要求发布者 SHA-256 验证回执；只读取 `calcium`，不读取 `predicted_calcium`。读取动物身份后冻结按动物划分的 train/validation/test，再读取实测目标；仿照作者 hook-flexion 角速度阈值和 30/300 ms 荧光滤波，仅在训练集拟合增益/偏移。时间异常、缺失运动学或空保留集会拒绝运行。

该入口是待用的离线感觉参考分析工具：没有生理通过阈值，没有 MaleCNS 细胞/ROI 对应，不能代替神经模型的自主闭环；公开研究后的划分也不称为前瞻盲测。实测文件结构适配尚须首次成功下载后确认。

运动侧下一步需要原始 MAT 试次、细胞笔记和对应探针身份，才能确定电压/电流及机械输出的单位与标定。已下载脚本提供多支探针的标定，不能据此套用统一转换常数。

软件验证：43 项测试通过（18 项历史、21 项此前新增、4 项本次新增），JavaScript 语法检查通过。新增测试覆盖动物分组稳定性、实测目标字段、滤波方向和卷积、跨表冲突/缺失/重复；全部属于软件夹具验证。
