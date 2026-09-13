# MaleCNS 路线图交接（2026-09-13）

## 接手先读

目标是执行完整的 `MaleCNS_realism_roadmap.md`，不是仅完成软件演示。当前交付为三轮部分实现，**整份路线图未完成，生理闭环未通过验收**。

按顺序阅读：本文件 → [原始路线图](MaleCNS_realism_roadmap.md) → [逐项状态](REALISM_STATUS.md) → [公开数据接入实录](validation/PUBLIC_DATA_STATUS.md)。路线图为上级工作区原文快照，其中提到的原始审计附件不随此快照补造；最新事实以本仓库执行记录和证据为准。

本次交接基于 `main`，原始基线提交为 `7d33b2f`。交接提交包含此前三轮代码、报告和本文件。当前机器仓库为 `C:\Users\77\Desktop\lab\malecns-language-world`。

## 已实现与证据

| 模块 | 已实现 | 验证边界 |
|---|---|---|
| `connectome/` | 逐身份编译、原始行分区、端点审计、来源哈希 | 165,122 个 Traced 候选、25,563,197 内部边；集合仍待审核，非完整生理图 |
| `physiology/` | 有单位电导核、异质参数、延迟、局部可塑性、慢状态、快照 | 参数参考实现；没有独立生理校准 |
| `interfaces/` | 接口证据模式、官方候选、MANC 补充表关联 | 正式批准端口为 0；不得把候选当审核结果 |
| `body/` | FlyGym 左前腿肌肉适配、15 肌肉刺激、步长与重启检查 | 225 帧 mocap 重放仍有 0.019602 mm RMSE / 0.0650035 mm 最大偏差 |
| `experiments/` | 多时钟闭环、7 对照、拟合/观测工具、公共下载和 FeCO 离线入口 | 闭环使用 6 个 fixture 神经元；不是 MaleCNS 生理闭环 |
| `world/` | 物理刺激场参考 | 尚未完成全身、多模态和长期生理耦合 |
| `habitat3d/` | 历史核使用 dt、移除自主摆腿/振翅动画、显式工程模式 | 旧 GUI 尚未接入经验证的新身体/神经模型 |

`validation/realism-evidence.json`：最近实际运行 43 项软件测试（18 历史 + 25 新增）通过，JavaScript 语法检查通过。`body-evidence.json`、`closed-loop-evidence.json`、`full-neuron-evidence.json` 分别保存此前实跑结果。本次交接不把这些基准冒充再次执行；修改相关源文件后应重跑对应基准。历史 `full-acceptance.json` 不对应当前源码，不能用于当前全图验收。

## 公共数据与关键发现

`validation/public-data-availability.json` 保存实际 URL、下载状态、哈希及本机路径；路径不是远程仓库附带资产。

- MANC `elife-96084-supp3-v1.csv` / `supp6-v1.csv` 已下载。7 个左前腿候选中 5 个类型一致；MaleCNS **819384 → MANC 17885** 为 Ti flexor / Acc. ti flexor 冲突；**815344 → 10256** 缺少补充表身份。所有候选缺可用匹配置信度，MANC 版本对应仍须核实。见 `validation/manc-crosswalk-evidence.json`。
- FeCO 作者说明、滤波代码已下载；原始 `hook_flexion_01_magnet.parquet` **未下载成功**。Dryad 公共下载 HTTP 403，API 文件下载 401；元数据可访问。不要重复将此描述为“没有公开数据”。
- 运动侧 Zenodo 4527659 的 README、探针标定及分析入口已下载并校验发布者 MD5；它是分析代码记录，不是原始试次压缩包。
- `experiments/feco.py` 只读取实测 `calcium`，排除 `predicted_calcium`；按动物冻结分组后进行训练集仿射校准。当前只做软件测试；`validation/feco-run-status.json` 明确记录缺文件而未运行。尚未建立生理阈值，不能称盲测通过，也不能用真实轨迹驱动的离线拟合替代闭环。

## 本机资产与新机器恢复

以下目录被 Git 忽略，**推送不包含它们**：`data/raw/`、`data/graph_full/`、`data/graph_neurons/`、`data/physiology_raw/`、`.venv/`、`.venv-body/`、`habitat3d/state/`。远端包含代码和较小证据报告，不包含大型图、实验原始文件、模型依赖或运行存档。

本机 `.venv` 复用相邻 `fly_language_lab/.venv`；新机器应自行创建 Python 3.12 环境并安装 `requirements.txt`。身体环境单独创建并安装 `requirements-body.lock.txt`；身体网格及上游资源还需依照 FlyGym 安装流程取得。不要覆盖本机已有图或状态。

仓库根目录常用命令：

```powershell
# 小规模软件回归；不重编大型图
.venv/Scripts/python.exe -m validation.run_realism
# 大型图：先恢复官方原始表，输出目录必须不存在
.venv/Scripts/python.exe -m connectome.compiler --out data/graph_neurons_new
.venv/Scripts/python.exe -m connectome.audit --graph data/graph_neurons_new
# 以下入口使用现有 data/graph_neurons；更换图目录须先核查各入口路径
.venv/Scripts/python.exe -m interfaces.evidence_inventory
.venv/Scripts/python.exe -m experiments.public_data
.venv/Scripts/python.exe -m interfaces.manc_crosswalk
.venv/Scripts/python.exe -m experiments.feco
# 有身体依赖与资源时执行
.venv-body/Scripts/python.exe -m body.benchmark
.venv-body/Scripts/python.exe -m experiments.closed_loop_benchmark
.venv/Scripts/python.exe -m validation.full_neuron_benchmark
```

## 下一步顺序与退出条件

1. 解决 Dryad 合法下载访问，校验目录中发布者摘要；取得 FeCO 原始文件后先核实真实列结构、单位、动物/试次条件和缺失值，再运行适配器。不得用合成记录补足实测文件。
2. 审核 MaleCNS 感觉细胞集合和运动候选的身份、侧别、版本、实验 driver/ROI、靶肌肉；解决上述冲突并记录审核者。不要直接复用 MANC/FANC 的数值 ID 或强制把多细胞 ROI 对应到单细胞。
3. 取得运动 MAT 试次及细胞笔记，识别对应探针和标定；统一时间、角度、力及荧光观测模型，预先锁定独立分组和有依据的误差阈值。
4. 解释 FlyGym mocap 偏差，并校准质量、力、负载和募集曲线。上游 XML 与 4 个 mocap 文件已做 5/5 哈希一致检查，不要重复归因于下载损坏。
5. 审核接口和参数后才接真实 MaleCNS 左前腿回路，完成感觉/运动分项、自主闭环与干预对照，再扩展六足、摄食、飞行和长期行为。逐工作包退出条件见 `REALISM_STATUS.md`，没有完成的项继续保留未完成。

## 必须保持的约束

主动动作只能由神经输出产生；不恢复目标规划、自动导航、随机探索、自动喂食或预设词义。结构连接与个体可塑状态分离，观测不得改变仿真，断点续跑应精确。模拟、软件检查、公开动物记录和生理验收必须明确区分。现有旧服务不会因为 Git 推送而更新，运行中的服务和存档未在此交接中替换。
