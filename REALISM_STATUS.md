# 路线图执行记录（2026-09-14 更新）

**总体状态：部分实施，未完成全部路线图，未通过生理生产验收。**
这里的 PASS 只适用于明确运行过的软件检查；没有真实动物盲测或经人工审核的神经—肌肉映射，不能把单回路/全身数字雄蝇标为完成。

## 第六轮：开放项收尾（2026-09-14）

- **FeCO 逐细胞身份已发表并接入**（`interfaces/feco_identity.py`，证据 `validation/feco-identity.json`）：Dallmann 2025 Nature 补充表 2（开放 URL，已落库校验）给出 MANC chief 9A 六个 bodyId、DNg74/DNg100/DNg12、hook=SNpp38 类型。经官方注释 mancBodyid/mancType 映射：chief 9A T1L→**MaleCNS 805450**（IN09A012，六例类型全一致）、DNg74→10131/10247、DNg100→10056/10045、DNg12→31932/37406/40361/226016、**左 hook 传入 809437/809543/810043（SNpp38，Traced）**。**论文链路在 MaleCNS 图中精确复现**：chief 9A 的前两大输入正是 DNg100（58 突触）与 DNg74（31）。映射含一处需人工复核的双重映射（MANC 13157→804940/809102）。逐细胞 club ID 任何连接组中都未发表（club 从未被重建）——该缺口定案。
- **真实回路升级为含已发表身份链**：98 节点/741 边；3 个左 hook 传入为**已发表身份感觉端口**（SNpp38），chief 9A 与 DNg100/74/12 共 22 个身份节点入图。五条件复跑：full 8 去极化/胫节 1.003 rad、无本体感觉 0 去极化回静息、rewired 0.658、shuffled_io 0.725。
- **运动试次标定（实测）**（`experiments/motor_trials.py`，证据 `validation/motor-trial-analysis.json`）：180222_F1_C1 会话（R22A08 驱动 = **中间类屈肌 MN**，笔记解析）121 个电流阶跃试次 → **Rin 188.4 MΩ（62.5 pA 档 ΔV=11.78±0.23 mV，n=8）、rheobase 100 pA、静息 −44.9 mV、封接 14.2 GΩ**；逐试次表入 `current_step_trials_180222_F1_C1.parquet`。单细胞与论文类均值（中间类 ~300 MΩ/−60 mV）的差异如实记录为细胞间变异。
- **逐类解剖（实测）**（`validation/mn-anatomy-classes.json`）：MN 共聚焦工作簿 Sheet2 → 胞体 7.1/11.4/15.8 µm（慢/中/快，n=6/3/6）、初突起 0.63/0.90/1.45 µm、神经索内轴突 0.69/1.30/2.45 µm——尺寸原理解剖排序确认。
- **前瞻预注册感觉编码测试**（`experiments/feco_preregister.py`，协议 SHA `0f6c28…` 先冻结后下载数据）：四数据集各按 Mamiya 2018 生理学预设定模型（hook 屈曲/伸展选择位相、claw 张力位置、club 双向位相），先验阈值 = test 试次多数胜恒定基线且合并 MSE 更低。结果：**hook_flexion 通过（14/16）、club 通过（6/8）、claw 未通过（5/12，如实报告——线性位置模型不足，提示需非线性/迟滞模型）**、hook_extension 数据已下载校验但其动物数不足冻结划分规则（<5），状态如实记录为 insufficient_animals_for_registered_split。协议契约内的列选择修正已注明；模型与阈值零改动。
- **六足上游缺口定案**（`validation/six-leg-inventory.json` 更新）：FlyMimic 仓库与 Özdil 补充材料核实——中/后腿 MTU 重建只存在于论文补充图，从未发布模型文件；引用的 OpenSim 管线仓库（neuromechfly-muscles）404；仅六足几何 STL 公开而无肌肉附着。除非作者发布，该缺口为最终。
- **批量选拉中止（v1.0.0 定版）**：其余 49 个试次 zip（~48 GB）的拉取在 Merritt 资产主机出现每连接 ~12 KB/s 服务端限速后中止（并发分段仅能部分缓解）；未保留部分下载，180222_F1_C1 的单会话实测标定保持有效。运动侧继续开放：49 个 zip 待重试；逐细胞类别→MaleCNS 身体 ID 的对应仍无发表依据（驱动系→类别有，连接组 ID 无）。

## 第五轮：数据解锁、生产签核与真实回路闭环（2026-09-14）

- **FeCO 原始实测数据已取得并首次运行**：用户 Dryad token 经环境变量传入（不落盘），6 个 FeCO 资产全部下载并通过发布者 SHA-256 校验（含此前阻塞的 `hook_flexion_01_magnet.parquet`，SHA-256 `d4a8c10f…` 精确匹配）。结构核实：320,154 行 × 14 列、7 只动物 12 试次、200 Hz、R21D12 驱动（hook flexion 传入）、角度单位度；`predicted_calcium` 存在但从未读取。`experiments.feco` 实跑：按动物冻结划分、训练集仿射校准 gain=40.48/offset=−1.23，**保留集 test 动物 4/4 试次 MSE 低于恒定基线**（如动物 5：49.6 vs 98.1）；无预注册阈值，`biological_acceptance=false` 保持。`validation/feco-run-status.json` 已更新。**运动侧试次包同步开拉**：`180222_F1_C1.zip`（200 MB）SHA-256 校验通过，IClamp 电流阶跃协议结构核实（`validation/motor-trial-acquisition.json`）。
- **生产端口 0 → 6**：用户 ZhangTingjia 执行具名人工签核（`interfaces.review --approve`），6 个左前腿胫节运动端口写入生产 `motor_map.parquet`，审核链 = 人工签核（叠加）automated_crosscheck_v1 自动交叉审核。
- **真实 MaleCNS 左前腿回路首次闭环**（`experiments/lf_tibia_circuit.py` prepare/run 两相入口，证据 `validation/lf-tibia-circuit.json`）：76 个真实节点（6 生产 MN + 12 个直接感觉伙伴端口 + top-25 premotor 中间神经元 + 其余感觉伙伴）、574 条诱导边（递质→受体极性映射；谷氨酸/unclear 的 100 条边**如实剔除**不赋符号）、MN 参数用文献先验、其余声明夹具。五条件实跑：full（胫节 0.974 rad，5 去极化）、no_proprioception（0 去极化，回静息——**感觉通路是此配置下运动输出的必要条件**）、motor_clamp（被动姿态，4 去极化）、rewired（0.658 rad，16 去极化）、shuffled_io（0.771 rad，14 去极化）。两个因果对照终点明显偏离 full；无预注册阈值，仅记录，不宣称显著。scope=anatomical_hypothesis。
- 其余第四轮成果见下节。

## 第四轮：缺失模块补齐、mocap 偏差解释与突触级数据接入（2026-09-14）

- **mocap 重放偏差已解释**（`body/mocap_diagnosis.py`，`validation/mocap-diagnosis.json`）：官方 clip 只存 7 个左前腿关节角；其参考轨迹录制时根（胸部自由关节）位姿漂移（旋转最高约 3.5°、平移约 0.16 mm）。逐帧刚体（Kabsch）对齐后残差从 0.0196 mm RMSE / 0.065 mm 最大值塌缩到 ≤0.0006 mm（数值精度级），第 0 帧对齐后仅 2e-5 mm。结论：坐标、单位、关节顺序、运动链与官方 XML 全部一致，偏差完全由录制根位姿漂移解释，不是下载损坏或建模错误。
- **Dryad 访问障碍已定性为政策而非故障**：Dryad API v2 现要求免费自助 API 账户 Bearer token（10 小时有效）才能下载文件字节；匿名用户明确禁止下载文件；`file_stream` 网页路由受 Anubis 质询保护；无 Zenodo/OSF/figshare 镜像。`experiments/public_data.py` 增加 `DRYAD_API_TOKEN` 环境变量支持（token 只作请求头、绝不写入回执），下载 URL 改为官方 `stash:download` 链接。FeCO 与运动原始文件仍在等待用户提供 token 后下载。
- **发现 MaleCNS 官方突触级公开数据**（此前未知）：`gs://flyem-male-cns` 桶内 `syn-points`（12.7 GB，逐突触 ROI）、`syn-partners`（6.8 GB，伙伴对+置信度+primary_post）、`tbar-neurotransmitters`（2.7 GB，逐突触前递质概率）无需认证即可下载（`download_data.py --profile all-tables`，哈希回执含发布者 MD5）。论文仓库 `flyconnectome/2025malecns` 的逐 ROI 精度/召回与 traced-synapse-capture CSV 已下载到 `data/raw/quality/`。
- **P0 逐 ROI 突触覆盖审计已实跑**（`connectome/synapse_coverage.py` + `roi_crosscheck.py`，证据 `validation/synapse-coverage.json`、`validation/synapse-roi-crosscheck.json`）：流式处理 syn-points 全部 **357,696,383 个突触侧**（165,122 Traced 身份按 146 个 primary ROI 分区；产出 `synapse_roi_coverage.parquet` 与逐细胞 `cell_synapse_counts.parquet`）。全局覆盖：突触前 42,658,913/45,655,140 = **93.4%**、突触后 130,413,767/311,833,234 = **41.8%**。**独立交叉核对**：103 个 ROI 与论文官方逐 ROI 表比对，突触侧计数完全一致（pre 相对误差 0.0、post ≤3.7e-8），traced 分数最大差 ≤0.0045（中位 3e-5~1.6e-4）。另量化：333 个 Traced 身份在导出中零突触位点（0.2%）、1,026 个仅有突触后、67 个仅有突触前。
- **运动候选自动证据审核**（`interfaces/review.py`，`validation/interface-review.json`）：7 个左前腿胫节候选中 6 个通过跨源类型一致或"补充表缺行但官方内嵌 mancType 一致"规则进入 `motor_map_reviewed_automated.parquet`（审核者记录为 automated_crosscheck_v1，含证据链、文献募集/延迟引用）；819384 因 MaleCNS 'Ti flexor MN' 与 MANC 'Acc. ti flexor MN' 跨源冲突（附属胫骨屈肌是独立靶肌肉）被明确排除并单列。**正式批准生产端口仍为 0**：人工签核须显式运行 `--approve "姓名"` 才写入生产 `motor_map.parquet`。
- **真实回路结构证据**（`experiments/motor_circuit_extract.py`）：6 个审核 MN 在已编译图中接收来自 844 个 Traced 伙伴的 20,720 结构突触、输出 116 到 82 个伙伴；最大输入包括 VNC 中间神经元 IN19A005、IN08A007 和下行神经元 DNg105。结构计数不是电导；该表用于接通前审核。
- **文献先验落地**（`physiology/literature_priors.py`）：胫骨屈肌 MN 的漏电导（Rin 150–900 MΩ 换算）与静息电位（−68…−48 mV，Azevedo 2020）、KC 漏电导/静息/mEPSC τ（Gu & O'Dowd 2006）以 measured 类登记；伸肌参数以 inferred（从屈肌池转移）登记；其余以 software_fixture 登记。7 个候选已按 seed 采样并全链留痕。**系统性警告：多数电生理为雌性测量，雄性迁移本身是显式假设。**
- **雄性质量校准回执**（`validation/male-mass-calibration.json`，Zumstein 2004 雄 0.81 mg / 雌 1.13 mg）：FlyMimic 模型在其 g/mm/µN 单位制下总质量 2.49 mg，为实测雌蝇 2.2 倍、雄蝇 3.1 倍——上游身体并未按真实果蝇质量标定，任何以模型体重归一的力/结论都继承该偏差；雄性均匀缩放因子 0.325。
- **缺失模块补齐**：`physiology/spiking.py`（AdEx 脉冲层，单位/不应期/快照）、`physiology/cable.py`（多室无源电缆参考，解析解一致性测试）、`physiology/gap_junctions.py`、`physiology/neuromodulation.py`（显式受体映射的饱和调制）、`physiology/mb_learning.py`（蘑菇体分区多巴胺门控局部可塑性，分区异质）、`physiology/circadian.py`（昼夜钟+唤醒门）、`world/light.py`、`world/nutrients.py`、`world/contact.py`、`body/recruitment.py`（尺寸原理运动单元池）、`body/male_calibration.py`、`body/flight.py`（单位正确的摆动气动脚手架，未验证声明）、`body/six_leg_inventory.py`（逐腿能力审计：LF 肌肉驱动、RF 仅关节、中/后腿缺失）、`connectome/roi_audit.py`（严格输入契约的 ROI 审计工具）、`connectome/receptor_hypotheses.py`（路线图 §2.3 产品：逐递质受体极性假设表，谷氨酸双假设、unclear 无条目、胺类走调质层）、`connectome/synapse_coverage.py`（syn-points 流式逐 ROI 覆盖/损失审计，12.7 GB 不入内存）、`experiments/stimulus_protocols.py`、`experiments/feeding.py`、`experiments/motor_unit_prediction.py`、`experiments/perturbations.py`（激活/沉默/消融干预）、`interfaces/unit_conversions.py`、`body/proprioception.py`（关节态→本体感受器格式，FeCO 风格静/动分路假设）。
- **连接级 ROI 审计与守恒验证**（`connectome/partner_coverage.py`，证据 `validation/partner-coverage.json`）：流式处理 syn-partners 全部 **311,833,243 对伙伴记录**。internal 124,025,046 对——与编译图内部结构计数**逐位一致**；总数 311,833,243 与官方发布结构计数总和**完全一致**（独立突触级导出与权重表编译互证）。另含 incoming 6,388,721 / outgoing 170,769,707 / unmapped 10,649,769 及各分区伙伴置信度均值，产出 `partner_roi_partition.parquet`。
- **运动回路递质剖析**（`experiments/motor_transmitters.py`，证据 `validation/motor-transmitters.json`）：流式处理 tbar 全部 45.7M T 杆。6 个审核 MN 的最大 premotor 输入为混合递质：GABA 能下行神经元（DNg93/DNge079/DNg105，p≈0.94–0.96）与中间神经元 IN19A005（gaba=0.93，与 Dallmann 2025 的 GABA 能传入抑制结论方向一致）、胆碱能 IN19B003/IN03A004（≈0.98）、谷氨酸能 IN14A004（glu=0.81，符号依靶细胞未知——受体假设表的双假设即为此保留）。MN 本体中枢内仅 1–31 个 T 杆（输出主要在外周 NMJ），其自身预测标签不具判别力。
- **运动单元预测实验**（`experiments/motor_unit_prediction.py`）：文献类别参数下慢 MN 先募集并紧张发放、中 MN 次之、快 MN 在中等驱动下不发放而单脉冲力约为慢单元 1000 倍——尺寸原理定性预测在软件栈内复现；属女性测量参数的栈检查，非雄性生理验证。
- 软件测试现为 64 项通过（18 历史 habitat3d + 46 validation，其中 21 项为本轮新增），JavaScript 语法检查通过；全部新增模块含严格输入校验、单位声明与拒绝语义。

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
| P0 ROI 审计 | **已完成（syn-points + syn-partners 双侧）** | 3.58 亿突触侧按 146 ROI 分区、全局 93.4% 前/41.8% 后覆盖、103 ROI 与论文表交叉核对一致；3.12 亿伙伴对连接级分区，internal 计数与编译图**逐位一致**；tbar 递质概率已入 MN 回路剖析 |
| P0 感觉/运动接口 | **运动侧已生产（6 端口，ZhangTingjia 签核）**；感觉侧为结构假设端口 | 感觉侧直接伙伴（12 个 SNpp/SNta 传入）以声明假设端口接入，FeCO club/hook/claw 与 MaleCNS 的具体身份对应仍缺（manc_v1_classifications 只有粗类；需论文补充表或逐细胞证据）；外周侧别/募集曲线实测仍缺 |
| P0/P1 神经动力学 | 全规模软件参考已运行；脉冲/电缆/电突触/调质层已补 | 屈肌 MN、KC 的实测膜参数已入先验（雌性来源）；缺独立输入输出/适应/时延对照、雄性参数、逐细胞快/中/慢类别指派 |
| P0/P1 左前腿 | mocap 偏差已解释；质量校准回执已出 | 15 肌肉刺激、被动对照、精确续跑、三步长已运行；重放残差归因于录制根位姿漂移（刚体对齐后 ≤0.6 µm）；模型总质量 2.49 mg 与实测 0.81 mg（雄）不匹配已量化；仍缺力/负载/能量实验与按质量的重新标定模型验证 |
| P1 神经—肌肉闭环 | **真实回路五条件闭环已实跑（anatomical_hypothesis）** | 已用生产端口 + 真实子图 + 结构感觉端口闭环；感觉传递/募集参数仍是声明夹具，FeCO 具体细胞身份、募集曲线实测与独立生物干预数据仍缺；生通过未宣称 |
| P1/P2 可塑性与内稳态 | 软件参考（MB 分区异质规则、昼夜钟、调质池、摄食内稳态已实现） | 蘑菇体逐分区速率/界限的实验数值、能量/水分参数、睡眠/唤醒阈值标定 |
| 数据与校准 | FeCO 实测已取得并运行；文献先验已入库 | 运动侧原始 MAT 试次包（Dryad 48 GB，token 已可用）尚未选拉；品系/性别/日龄/温度条件提取与预注册容差仍缺 |
| 生理/行为/因果矩阵 | 未通过 | 未拟合刺激与细胞干预、真实运动行为分布、度数保持重连/无连接组/反馈消融等完整对照 |
| 性能 | 软件规模/闭环基准已运行 | 已记录软件夹具闭环的每模拟秒耗时、峰值工作集和子系统计数；校准后的真实生理模型性能仍未知 |
| 六足、摄食、飞行、求偶 | 摄食内稳态与飞行单位脚手架已实现；六足受上游限制 | LF 肌肉驱动、RF 仅无执行器关节、中/后腿缺失（见 six-leg-inventory）；各工作包仍需独立解剖/物理/实验数据 |
| 全身/长期/遗传/多室 | 电缆参考已实现 | 路线图明确属于后续按实验误差驱动的独立研究工作包 |

## 复现

```powershell
# 输出目录必须不存在，防止覆盖已有审计。
.venv/Scripts/python.exe -m connectome.compiler --out data/graph_neurons_new
.venv/Scripts/python.exe -m connectome.audit --graph data/graph_neurons_new
.venv/Scripts/python.exe -m validation.run_realism
# 突触级表（官方公开桶，无需认证；首次 20+ GB）
.venv/Scripts/python.exe download_data.py --profile all-tables
# 逐 ROI 突触覆盖 + 论文表交叉核对 + 连接级分区 + MN 回路递质剖析
.venv/Scripts/python.exe -m connectome.synapse_coverage --points data/raw/syn-points-male-cns-v1.0-minconf-0.5.feather
.venv/Scripts/python.exe -m connectome.roi_crosscheck
.venv/Scripts/python.exe -m connectome.partner_coverage --partners data/raw/syn-partners-male-cns-v1.0-minconf-0.5.feather
.venv/Scripts/python.exe -m experiments.motor_transmitters
# 通用 ROI 审计工具（输入须含 pre/post/roi 列）
.venv/Scripts/python.exe -m connectome.roi_audit --synapses data/raw/<synapse-export>.feather
# 第四轮新增入口
.venv/Scripts/python.exe -m interfaces.review           # 自动证据审核；--approve "姓名" 才写入生产端口
.venv/Scripts/python.exe -m experiments.motor_circuit_extract
.venv/Scripts/python.exe -m physiology.literature_priors
.venv/Scripts/python.exe -m connectome.receptor_hypotheses
.venv/Scripts/python.exe -m experiments.motor_unit_prediction
# 身体独立环境；完整依赖已锁定，避免影响旧虚拟环境
.venv-body/Scripts/python.exe -m pip install -r requirements-body.lock.txt
.venv-body/Scripts/python.exe -m body.benchmark
.venv-body/Scripts/python.exe -m body.mocap_diagnosis
.venv-body/Scripts/python.exe -m body.six_leg_inventory
.venv-body/Scripts/python.exe -m experiments.closed_loop_benchmark
.venv/Scripts/python.exe -m validation.full_neuron_benchmark
.venv/Scripts/python.exe -m interfaces.evidence_inventory
# Dryad 原始数据（需免费 API token；见 PUBLIC_DATA_STATUS.md）
$env:DRYAD_API_TOKEN = '<token>'; .venv/Scripts/python.exe -m experiments.public_data
.venv/Scripts/python.exe -m experiments.feco
# 前瞻预注册感觉编码测试（register 必须先于任何数据下载）
.venv/Scripts/python.exe -m experiments.feco_preregister register
$env:DRYAD_API_TOKEN = '<token>'; .venv/Scripts/python.exe -m experiments.feco_preregister download
.venv/Scripts/python.exe -m experiments.feco_preregister evaluate
# FeCO 逐细胞身份与运动试次实测标定
.venv/Scripts/python.exe -m interfaces.feco_identity
.venv/Scripts/python.exe -m experiments.motor_trials
# 生产签核（具名人工审核者）与真实回路闭环
.venv/Scripts/python.exe -m interfaces.review --approve "<姓名>"
.venv/Scripts/python.exe -m experiments.lf_tibia_circuit prepare
.venv-body/Scripts/python.exe -m experiments.lf_tibia_circuit run
# 历史 3D 工程对照，非生理生产模型
.venv/Scripts/python.exe habitat3d/server.py --engineering-sandbox --brain-mode full
```

当前软件证据输出 `validation/realism-evidence.json`。历史 `full-acceptance.json` 的源码哈希已不对应改后的文件，不冒充当前全图复验。

肌肉刺激图见 `validation/body-stimulation.png`。已实现独立软件夹具闭环，但未将它接入旧 3D 世界冒充生理模型；当前缺少经审核的运动/感觉接口。具备正式映射、多模态物理场、摄食、内稳态神经反馈并通过实验审核的闭环仍未完成。

官方资料已在本次重新读取：[MaleCNS 数据定义](https://male-cns.janelia.org/download/)、[FlyGym 左前腿实验性肌骨模型](https://neuromechfly.org/tutorials/6_muscle_imitation/)、[FlyGym 安装](https://neuromechfly.org/installation/)。官方左前腿示例本身不证明 MaleCNS 神经—肌肉对应，也不是完整六足肌肉实现。
