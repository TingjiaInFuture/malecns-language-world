# 路线图执行记录（2026-09-13）

**总体状态：部分实施，未完成全部路线图，未通过生理生产验收。**
这里的 PASS 只适用于明确运行过的软件检查；没有真实动物盲测或经人工审核的神经—肌肉映射，不能把单回路/全身数字雄蝇标为完成。

## 第三轮：公开数据接入

- 两组 Dryad 版本/文件目录已保存；MANC 补充表3/6已下载并与 MaleCNS 候选关联。7 个候选中 5 个类型一致、1 个类型冲突、1 个没有补充表身份；均未批准为生产端口。
- FeCO 作者数据说明和观测模型源码已下载；运动实验 Zenodo 分析代码、README 和探针标定脚本已下载并通过发布者 MD5 校验。这些不是原始神经—运动同步记录。
- Dryad 元数据正常，但原始文件公开下载返回 HTTP 403，API 下载返回 401；目前是下载与身份审核障碍，不是没有公开来源。失败项保持 `local_path=null`。
- 实现严格区分实测 calcium/预测字段的离线感觉分析入口、按动物划分与训练集校准、来源回执及跨数据集审核表；原始数据未取得，未产生生理分数。最新软件测试 43 项通过。
- 详细资产、发现、命令和阻塞见 [公开数据接入实录](validation/PUBLIC_DATA_STATUS.md)。完整路线图仍未完成，其他未完成条件仍见下表。

## 第二轮继续执行

- 新增 `experiments/embodied.py`，将关节感觉、传入延迟、神经核、传出延迟、肌肉募集、FlyGym、局部可塑性及慢状态记账串成独立多时钟执行器。显式注入电流与局部调制用于实验干预；没有目标规划器。慢状态目前仅接通记账，尚未实现经校准的摄食/神经调质耦合。
- `experiments/closed_loop_benchmark.py` 已实跑七种条件：完整、无连接、保度数重连、打乱 I/O、无本体反馈、运动输出夹零、无调制。**这里用的是 6 个明确以 `fixture:` 命名的软件神经元，不是 MaleCNS 生理模型。** 每条件保存全部采样轨迹、事件数和子系统计时。膜电位、关节角和可塑效能的断点续跑误差均为 0；1000 次观测读取及修改返回副本不影响仿真。
- 七种条件都如实保留，未挑选最好轨迹；重连和打乱 I/O 可产生接近原条件的终点。因此这些结果不能支持已找到真实回路机制，也没有生物阈值意义上的“显著削弱”结论。
- `validation/full_neuron_benchmark.py` 已让 **165,122 节点、25,563,197 边**通过电导参考核执行 5 次 0.1 ms 更新，约 1.278 亿次边计算。神经计算耗时约 4.37 秒/0.5 ms 模拟时间；状态数组约 413 MB，结构/参数数组约 1.023 GB，临时数组另计。使用明确标记的统一受体极端与工程电导比例，仅是全规模数值资源基准，不是未知递质的生理定性。
- `physiology/parameter_tables.py` 新增有来源、单位、适用条件的类型/类别先验采样；支持逐神经元膜参数，参数可按类型共享但状态不合并。缺失先验会拒绝运行，不默认填入已测生理值。
- `experiments/calibration.py` 新增有界多起点参数拟合、先验约束、预注册时序/条件/单位校验及组间泄漏拒绝。工具的解析夹具可以通过；尚没有可据以完成生理盲测的数据集。
- 官方注释筛出 7 个 T1/L 胞体的胫节屈伸运动候选：800636、807165、809912、815344、818057、819384、909831。保存在 `data/graph_neurons/interfaces/lf_tibia_candidates.parquet`，**未加入生产接口**。类型、胞体侧别、MANC 字段不足以替代外周侧别、具体肌肉、募集曲线和版本一致的独立审核；模型肌肉名的数字后缀不得直接当 MaleCNS ID。
- 对 FlyMimic 官方仓库重新下载 XML 与 qpos/qvel/xipos/xivel 进行哈希比对，5/5 与安装包一致，证据在 `validation/upstream-body-source-audit.json`。这排除了这些文件的下载/打包变化，不能解释或消除运动学偏差。
- 第二轮后的软件测试为原有 18 项 + 新增 21 项；闭环身体基准另外运行。新证据为 `closed-loop-evidence.json`、`full-neuron-evidence.json`、`interface-research.json`，均明确 `biological_acceptance=false`。

## 已落地

- `connectome/compiler.py`：冻结并校验三份 MaleCNS v1.0 源文件 SHA-256，流式扫描全部 151,856,684 条原始记录。以官方 `Traced` 状态作**待审核首版集合**，保留无胞体/类型名的 Traced 身份，不推测片段归属。
- 本地 `data/graph_neurons/`：165,122 个候选神经元身份；25,563,197 条内部连接记录，结构计数合计 124,025,046。4,802,106 条传入边界记录、112,538,237 条传出边界记录、8,953,144 条双端未映射记录；总计与原始记录数守恒。这里的结构计数不是实测电导，也不直接等于独立突触位点数。
- `connectome/audit.py`：校验旧原始图端点清单的哈希和版本，导出 88,219,733 个唯一未决分割端点；内部边无重复对。46,455 个未纳入首版的注释条目单列供审核；其中有胶质、片段、边界和潜在神经元，**不能全称为应排除细胞**。165,122 个身份中也有不出现在原始边表的孤立身份，所以不能直接用两个节点数相减解释所有端点。
- 按细胞记录内部/边界输入输出结构计数。`coverage_by_soma_neuromere.csv` 仅按胞体所在区域聚合，**不是突触 ROI 覆盖**。
- `interfaces/registry.py`：感觉/运动证据表模式与校验，拒绝空表、跨数据集 ID、缺失证据、非运动神经元肌肉输出。候选表已从官方注释导出；审核表为空，未伪造器官—细胞—肌肉对应。
- `physiology/reference.py`：CPU 级电位电导核，有显式 ms/mV/pF/nS/pA、受体反转电位、延迟、适应及独立个体状态。拒绝未知反转电位；解剖/电导先验与个体功能效能分离；快照核验拓扑、参数和时钟。
- `FullBrains.forward` 的 dt 实际参与更新：历史工程 tau=0.25/log(2) 秒，dt=.25 时保持原递推；dt=0 不推进，非法 dt 拒绝。这不是生理时间常数，也不将历史段图核升级成生物核。
- `physiology/clock.py`：整数多时钟；`plasticity.py`：显式局部掩码的调制资格迹参考规则；`homeostasis.py`：接触摄入、吸收、消耗和水分守恒。规则尚未经雄蝇数据校准，未部署为已知生物学习机制。
- `world/stimuli.py`：SI 单位平流扩散脉冲参考场、接触味觉及受体饱和函数。`experiments/measurement.py`：独立测量滤波/噪声和动物/轨迹组间数据泄漏校验。
- 前端已移除自行产生的摆腿/振翅，仅接受显式关节字段；缺少关节物理状态时保持静止。现有外形仍不是 FlyGym 解剖渲染适配器。
- 旧服务器明确要求 `--engineering-sandbox`；桌面启动脚本显式使用此标记。旧存档、全图数据、历史测试不覆写。正在运行的旧服务不会自动变成新代码。
- `body/flygym_adapter.py` 和 `body/benchmark.py`：已在隔离的 `.venv-body` 安装并锁定 FlyGym 2.1.0 / MuJoCo 3.9.0，依赖检查通过；官方 72 个肌骨网格已下载。15 个左前腿肌肉均独立刺激 50 ms 并与被动对照比较，全部产生非零关节差异；续跑关节误差为 0。dt=0.1/0.05/0.025 ms 的相邻终点误差为 0.00309375 / 0.000172750 rad，误差随步长细化下降。这只是此工作负载的局部收敛证据。
- 全部 225 帧公开 mocap 已做强制角度的前向运动学重放，**不是肌肉控制跟踪成功**。发现文件名 `xipos` 实际在上游奖励实现中对应 MuJoCo `xpos`（身体坐标原点）；错误使用质心 `xipos` 会得到 0.12093 mm RMSE。修正到上游定义后仍有 0.0196020 mm RMSE、0.0650035 mm 最大误差，尚未解释，未通过运动学校准。误差和原始数据哈希完整保留在 `validation/body-evidence.json`。
- 当前 18 项旧回归 + 14 项新增测试全部通过；JavaScript 语法检查通过。独立读取官方本地 Arrow 源表，对 256 条编译输出的原始行地址进行 ID/方向/计数比较，均匹配；这不是 neuPrint API 的独立交叉查询。

## 路线图逐项未完成条件

| 工作包 | 状态 | 尚缺的交付/退出条件 |
|---|---|---|
| P0 逐神经元图 | 部分 | 外周/边界身份人工核验、可信片段合并清单、官方独立查询抽样；当前 Traced-only 集合不是最终身份规则 |
| P0 ROI 审计 | 部分 | 带 ROI 的突触伙伴/点数据及按突触脑区的覆盖与损失 |
| P0 感觉/运动接口 | 部分 | 审核者、器官/肌肉、单位、募集/传递函数、侧别和来源齐全的非空接口表及打乱对应对照 |
| P0/P1 神经动力学 | 全规模软件参考已运行 | 缺实测膜/突触参数、输入输出/适应/时延独立对照；全图资源基准是工程参数夹具；脉冲/多室机制仍需按实验需要实现 |
| P0/P1 左前腿 | 软件/身体基线已运行，校准未通过 | 15 肌肉刺激、被动对照、精确续跑和三步长已运行；225 帧重放仍有 0.0650 mm 最大位置误差；缺雄性质量/力单位校准及负载/能量实验 |
| P1 神经—肌肉闭环 | 软件夹具闭环已运行；生理闭环未完成 | 仍缺审核后的本体细胞—VNC—运动细胞—肌肉链路、募集曲线及独立生物干预数据 |
| P1/P2 可塑性与内稳态 | 软件参考 | 蘑菇体局部机制实验约束、能量/水分参数、睡眠/唤醒/昼夜节律与神经调质连接 |
| 数据与校准 | 校准/协议工具已实现；缺真实实验输入 | 明确品系、性别、日龄、温度、光照与营养的训练/验证/盲测数据；由重测可靠性决定的预注册容差 |
| 生理/行为/因果矩阵 | 未通过 | 未拟合刺激与细胞干预、真实运动行为分布、度数保持重连/无连接组/反馈消融等完整对照 |
| 性能 | 软件规模/闭环基准已运行 | 已记录软件夹具闭环的每模拟秒耗时、峰值工作集和子系统计数；校准后的真实生理模型性能仍未知 |
| 六足、摄食、飞行、求偶 | 未完成 | 各工作包独立解剖/物理/实验数据；不能用当前 8 维推力和匿名信号顶替 |
| 全身/长期/遗传/多室 | 未完成 | 路线图明确属于后续按实验误差驱动的独立研究工作包 |

## 复现

```powershell
# 输出目录必须不存在，防止覆盖已有审计。
.venv/Scripts/python.exe -m connectome.compiler --out data/graph_neurons_new
.venv/Scripts/python.exe -m connectome.audit --graph data/graph_neurons_new
.venv/Scripts/python.exe -m validation.run_realism
# 身体独立环境；完整依赖已锁定，避免影响旧虚拟环境
.venv-body/Scripts/python.exe -m pip install -r requirements-body.lock.txt
.venv-body/Scripts/python.exe -m body.benchmark
.venv-body/Scripts/python.exe -m experiments.closed_loop_benchmark
.venv/Scripts/python.exe -m validation.full_neuron_benchmark
.venv/Scripts/python.exe -m interfaces.evidence_inventory
# 历史 3D 工程对照，非生理生产模型
.venv/Scripts/python.exe habitat3d/server.py --engineering-sandbox --brain-mode full
```

当前软件证据输出 `validation/realism-evidence.json`。历史 `full-acceptance.json` 的源码哈希已不对应改后的文件，不冒充当前全图复验。

肌肉刺激图见 `validation/body-stimulation.png`。已实现独立软件夹具闭环，但未将它接入旧 3D 世界冒充生理模型；当前缺少经审核的运动/感觉接口。具备正式映射、多模态物理场、摄食、内稳态神经反馈并通过实验审核的闭环仍未完成。

官方资料已在本次重新读取：[MaleCNS 数据定义](https://male-cns.janelia.org/download/)、[FlyGym 左前腿实验性肌骨模型](https://neuromechfly.org/tutorials/6_muscle_imitation/)、[FlyGym 安装](https://neuromechfly.org/installation/)。官方左前腿示例本身不证明 MaleCNS 神经—肌肉对应，也不是完整六足肌肉实现。
