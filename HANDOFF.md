# MaleCNS 路线图交接（2026-09-14 第六轮更新）

> **v1.0.0 定版**：本仓库以当前状态作为 v1.0.0 归档——六轮路线图执行、67 项软件测试全绿、
> 27 份验证证据、6 个经签核的生产运动端口、含已发表身份 FeCO 链的真实回路五条件闭环。
> 生理验收（biological_acceptance）按证据边界保持 false；剩余开放项见文末。
> 未完成的批量选拉代码与部分下载已于定版前清除，工作树干净。

## 接手先读

目标是执行完整的 `MaleCNS_realism_roadmap.md`，不是仅完成软件演示。当前为六轮部分实现：缺失模块已补齐、突触级审计完成、FeCO 实测已运行、生产端口已签核、真实回路五条件闭环已实跑（含**已发表身份的 hook 感觉端口与 9A/DN 链**）、运动试次实测校准落地、前瞻预注册测试完成（2 过 1 败 1 不可评）、六足上游缺口定案。整份路线图仍未完成：生理验收未通过，剩余边界均为需要新数据或新实验的项（见文末）。

按顺序阅读：本文件 → [原始路线图](MaleCNS_realism_roadmap.md) → [逐项状态](REALISM_STATUS.md) → [公开数据接入实录](validation/PUBLIC_DATA_STATUS.md)。路线图为上级工作区原文快照，其中提到的原始审计附件不随此快照补造；最新事实以本仓库执行记录和证据为准。

本次交接基于 `main`；第六轮提交包含新模块、审核、签核与证据文件。当前机器仓库为 `C:\Users\77\Desktop\lab\malecns-language-world`。

## 已实现与证据（含第六轮）

| 模块 | 已实现 | 验证边界 |
|---|---|---|
| `connectome/` | 逐身份编译、原始行分区、端点审计、来源哈希；**突触级审计全部实跑**：3.58 亿突触侧按 146 ROI（93.4% 前/41.8% 后，与论文表计数一致）+ 3.12 亿伙伴对连接级分区（internal 与编译图逐位一致）+ tbar 递质概率入 MN 回路剖析 | 七表全部本地就位（含哈希回执）；递质加权的全图受体假设升级仍待做 |
| `physiology/` | 电导核、延迟、可塑性、慢状态、快照；第四轮新增 AdEx 脉冲层、多室电缆参考、电突触、调质池+受体映射、MB 分区多巴胺可塑性、昼夜钟/唤醒门、文献先验（雌性来源已标注） | 参数参考实现；实测值仅覆盖屈肌 MN 漏电导/静息与 KC 三参数；无独立生理校准 |
| `interfaces/` | 证据模式、官方候选、MANC 补充表关联；自动证据审核 + **ZhangTingjia 人工签核：6 个生产运动端口已写入 `motor_map.parquet`** | 819384 跨源冲突仍排除在端口外；感觉侧 = 3 个已发表身份 hook 端口（SNpp38）+ 12 个结构直连伙伴（声明假设）；MANC 13157 双映射一处待人工复核 |
| `body/` | 15 肌肉刺激、续跑/步长检查；第四轮 mocap 偏差根因（录制根位姿漂移，刚体对齐后 ≤0.6 µm）、雄性质量校准回执（模型 2.49 mg vs 实测雄 0.81/雌 1.13 mg，因子 0.325）、尺寸原理运动单元池、逐腿能力审计（仅 LF 肌肉驱动）、飞行单位脚手架 | 力/负载/能量实验未做；按质量重标定的模型未验证 |
| `experiments/` | 多时钟闭环、7 对照、拟合/观测工具；FeCO **实测数据已运行**（test 动物 4/4 优于恒定基线）；**真实 LF 胫节回路五条件闭环已实跑**（98 节点/741 边，含 22 个已发表身份节点，`experiments/lf_tibia_circuit.py`）；前瞻预注册感觉测试 2 过/1 败/1 不可评 | 感觉传递与募集参数仍为声明夹具；无预注册阈值，生通过未宣称 |
| `world/` | 物理刺激场参考；第四轮补光子场、可摄取底物、接触/温湿度/风 | 尚未完成全身、多模态和长期生理耦合 |
| `habitat3d/` | 历史核使用 dt、移除自主摆腿/振翅动画、显式工程模式 | 旧 GUI 仍未接入经验证的新身体/神经模型 |

软件测试现为 67 项通过（18 历史 + 49 validation，其中 24 项为第四至六轮新增），JavaScript 语法检查通过。历史 `full-acceptance.json` 不对应当前源码；修改相关源文件后应重跑对应基准。

## 公共数据与关键事实

`validation/public-data-availability.json` 保存实际 URL、下载状态、哈希及本机路径。

- **Dryad**：用户 token 已投入使用（仅经环境变量，绝不落盘），6 个 FeCO 资产全部下载并通过发布者 SHA-256 校验；`hook_flexion_01_magnet.parquet` 实测结构已核实（14 列/7 动物/200 Hz/R21D12），FeCO 离线分析已实跑。运动侧试次包：50 个 zip 中 1 个（180222_F1_C1）已取得校准；其余 49 个（约 48 GB）在 v1.0.0 定版时选拉中止——Merritt 资产主机出现每连接约 12 KB/s 的服务端限速（并发 Range 分段可部分缓解但仍不可行），token 流程保持可用，可日后重试。
- **MaleCNS 突触级数据全部本地就位并审计完成**：syn-points（3.58 亿侧）、syn-partners（3.12 亿对，internal 与编译图逐位一致）、tbar（45.7M T 杆递质概率）、body-stats；论文仓库逐 ROI 质量 CSV 已交叉核对一致。
- MANC 补充表 3/6 已下载。7 个左前腿候选：6 个已生产（ZhangTingjia 签核）；819384 的 MaleCNS↔MANC 跨源类型冲突仍排除。
- FeCO 细胞（club/hook/claw、9A、DNg74/DNg100）驱动系已核实；**逐细胞身份已接入**（第六轮）：Dallmann 2025 补充表 2 → MANC ID/类型 → MaleCNS（chief 9A T1L=805450、左 hook=809437/809543/810043 等 22 个）；club 逐细胞 ID 未发表（定案）。真实回路感觉端口 = 3 个已发表身份 hook + 12 个结构直连伙伴（声明假设）。
- 文献先验（`physiology/literature_priors.py`）：Azevedo 2020（实为 eLife 9:e56754，非 2022 Nature 系）屈肌 MN Rin 150–900 MΩ、Vrest −68…−48 mV、力/脉冲 10/1/0.013 µN、传导延迟 0.6–1.3 ms；Zumstein 2004 雄 0.81 mg；Gu & O'Dowd 2006 KC 参数；MB 可塑性 80–90% 抑郁（Hige 2015）等。**多数为雌性测量，雄性迁移是显式假设。**

## 本机资产与新机器恢复

以下目录被 Git 忽略，**推送不包含它们**：`data/raw/`、`data/graph_full/`、`data/graph_neurons/`、`data/physiology_raw/`、`.venv/`、`.venv-body/`、`habitat3d/state/`。远端包含代码和较小证据报告，不包含大型图、实验原始文件、模型依赖或运行存档。

本机 `.venv` 复用相邻 `fly_language_lab/.venv`；新机器应自行创建 Python 3.12 环境并安装 `requirements.txt`。身体环境单独创建并安装 `requirements-body.lock.txt`；身体网格及上游资源还需依照 FlyGym 安装流程取得。不要覆盖本机已有图或状态。

仓库根目录常用命令：

```powershell
# 小规模软件回归；不重编大型图
.venv/Scripts/python.exe -m validation.run_realism
# 突触级表（官方公开桶；20+ GB，断点续传）
.venv/Scripts/python.exe download_data.py --profile all-tables
.venv/Scripts/python.exe -m connectome.synapse_coverage --points data/raw/syn-points-male-cns-v1.0-minconf-0.5.feather
.venv/Scripts/python.exe -m connectome.roi_crosscheck
.venv/Scripts/python.exe -m connectome.partner_coverage --partners data/raw/syn-partners-male-cns-v1.0-minconf-0.5.feather
.venv/Scripts/python.exe -m experiments.motor_transmitters
# 大型图：先恢复官方原始表，输出目录必须不存在
.venv/Scripts/python.exe -m connectome.compiler --out data/graph_neurons_new
.venv/Scripts/python.exe -m connectome.audit --graph data/graph_neurons_new
.venv/Scripts/python.exe -m experiments.motor_circuit_extract
.venv/Scripts/python.exe -m physiology.literature_priors
.venv/Scripts/python.exe -m connectome.receptor_hypotheses
.venv/Scripts/python.exe -m experiments.motor_unit_prediction
# Dryad 原始数据（免费 token 经环境变量；见 PUBLIC_DATA_STATUS.md）
$env:DRYAD_API_TOKEN = '<token>'; .venv/Scripts/python.exe -m experiments.public_data
.venv/Scripts/python.exe -m experiments.feco
# 生产签核与真实回路闭环（prepare 用 .venv，run 用 .venv-body）
.venv/Scripts/python.exe -m interfaces.review            # 查看自动审核；--approve "姓名" 写生产端口
.venv/Scripts/python.exe -m experiments.lf_tibia_circuit prepare
.venv-body/Scripts/python.exe -m experiments.lf_tibia_circuit run
# 身体独立环境
.venv-body/Scripts/python.exe -m body.benchmark
.venv-body/Scripts/python.exe -m body.mocap_diagnosis
.venv-body/Scripts/python.exe -m body.six_leg_inventory
.venv-body/Scripts/python.exe -m experiments.closed_loop_benchmark
.venv/Scripts/python.exe -m validation.full_neuron_benchmark
```

## 下一步顺序与退出条件

1. **运动侧扩展标定**：其余 49 个试次 zip（~48 GB）待资产主机限速解除后选拉（token 流程已验证；单连接已观察到 ~12 KB/s 限速，需并发分段策略）；逐驱动类别汇总 Rin/rheobase/力-脉冲；用 Piezo/force 通道做感觉-运动响应标定；替换 lf_tibia_circuit 中声明的感觉/募集夹具。逐细胞类别→MaleCNS body ID 对应仍无发表依据，需新实验。
2. **FeCO 深化**：claw 前瞻测试失败提示需非线性/迟滞位置模型——注册 v2 协议（模型变更需重新预注册）；club 逐细胞 ID 任何连接组均未发表（定案）；`rna-seq.xlsx` 受体表达可接入 receptor_hypotheses。
3. **回路扩展**：lf_tibia_circuit 扩到 844 个 premotor 伙伴、加调质/学习层长期实验；接入 calibration.py 的预注册盲测流程。
4. 身体侧：按 0.325 质量因子生成标定模型副本并重跑被动/负载/能量实验；力/负载单位校准仍缺。
5. 六足/飞行/求偶：上游解剖数据缺口已定案（见 `validation/six-leg-inventory.json`）；除非 FlyMimic 作者发布中/后腿模型，六足闭环需自建肌肉附着数据。逐工作包退出条件见 `REALISM_STATUS.md`，没有完成的项继续保留未完成。

## 必须保持的约束

主动动作只能由神经输出产生；不恢复目标规划、自动导航、随机探索、自动喂食或预设词义。结构连接与个体可塑状态分离，观测不得改变仿真，断点续跑应精确。模拟、软件检查、公开动物记录和生理验收必须明确区分。Dryad token 只经环境变量传入且绝不落盘。现有旧服务不会因为 Git 推送而更新，运行中的服务和存档未在此交接中替换。
