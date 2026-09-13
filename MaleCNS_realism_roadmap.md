# 从 MaleCNS Language World 到可验证数字雄果蝇：实施任务书

日期：2026-09-13。对象：用户上传的 `malecns-language-world-main.zip`。

## 0. 目标与证据边界

目标不是“会移动的果蝇外形代理”，而是在明确品系、性别、日龄、温度、光照、营养和实验任务下，同时预测神经活动、肌肉/关节响应、行为统计与干预结果的具身模型。这里不设无依据的“生物真实性百分比”，也不把整个动物生理等价当成90天交付承诺。

本次做了源码审计和18项原有小图/机制/历史测试，测试全部通过；没有原始全图数据，没有独立重跑完整图。随附全图报告的4个源码哈希与当前源码相符。具体源码行号、环境差异、运行日志和哈希见同目录 `MaleCNS_code_audit.md`、`audit_manifest.json`。

已核查的关键偏差：所有分割端点被当成动态节点；97个MBON上的人工I/O；未知递质默认正传播；神经更新不使用dt；8维推力身体；外形动画代替关节动力学；生产模式禁止可塑性。应保留数据溯源、独立状态、主动行为无旁路、环境干预和断点续跑，不应把现有大矩阵等同于完整生理脑。

## 1. 目标架构

```text
物理环境：光子/气味浓度/气流/接触/温湿度/可摄取物质
  → 外周感受器转导：视网膜、嗅觉、味觉、机械感受、本体感觉
  → 解剖对应的感觉神经元
  → MaleCNS 神经元级网络：视叶、中央脑、颈连接、腹神经索
  → 解剖对应的运动神经元/内分泌输出
  → 神经肌肉接头、肌肉激活、肌腱/力臂、关节、身体
  → 新的外部输入与本体反馈

慢变量：营养吸收、水分、疲劳、唤醒、昼夜节律、神经调质
学习变量：有证据的局部突触可塑性与必要的稳态调节
观测层：神经记录、实验装置与钙/电压指示器测量模型
渲染层：仅订阅物理和神经状态，不驱动腿/翅/动作
```

## 2. P0：把分割图编译成生物神经元图

### 2.1 输入

冻结 `male-cns:v1.0` 及其来源、校验和、下载日期。读取官方神经元注释、递质预测和分割连接表；必要时补充突触点/伙伴和局部骨架。不要一开始下载整个EM体数据。

官方明确区分全部分割段连接表与神经元注释。项目报告的88,384,522个端点和151,856,684条边是分割层计数；不能将前者视为生物神经元数，也不能把后者视为独立突触数。应以所选发布版本的神经元集合为准，大体对齐约166,700神经元的研究规模，实际数目由审计产生，不硬编码一个必须吻合的整数。

### 2.2 编译规则

- 根据官方身份和校对状态建立逐神经元集合，保留有充分证据的未定型神经元、外周传入轴突和边界相关细胞；不能仅凭是否有胞体或类型名称筛掉它们。
- 已有经过验证的片段归属才合并到同一神经元；不凭空间接近自行连成完整细胞。
- 未归属片段保留在原始数据/不确定性表中，不作为独立生理神经元批量模拟，也不声称这些信息已被恢复。
- 不按细胞类型压成一个节点。参数可以按类型共享，状态仍逐神经元保存。
- 原始计数、推定电导、可塑权重分开。连接数不是生理电导。
- 汇报神经元内部连接、跨边界连接、未映射连接，按脑区统计输入/输出覆盖与损失。不用“零额外删除行”替代生物真实性。

### 2.3 计划新增的数据产品

```text
neurons.parquet:
  dataset, body_id, neuron_type, class, side, nerve,
  proofreading_status, boundary_status, identity_evidence

edges.parquet:
  pre_body_id, post_body_id, structural_count, roi,
  synapse_confidence_summary, source_record

unresolved.parquet:
  segment_id, reason, candidate_parent_ids, mapping_evidence

neuron_type_params.parquet:
  type_or_class, parameter, value_or_distribution, unit,
  measured_or_inferred, source, applicable_sex_age_temperature

receptor_hypotheses.parquet:
  pre_type, post_type, transmitter, receptor_class,
  reversal_potential_or_polarity, probability, evidence
```

验收：ID、方向、重复边、计数、单位与官方抽样查询一致；每一条排除/合并规则可追溯；没有把分割碎片误当大量独立神经元。

## 3. P0：替换97个MBON上的随机感觉/运动端口

建立两张人工审核的接口表，禁止随机索引成为生产模型的I/O。

```text
sensory_map.parquet:
  modality, receptor_or_neuron_type, body_id, side,
  peripheral_location, receptive_field, transfer_function,
  gain, latency_ms, noise_model, evidence, confidence

motor_map.parquet:
  motor_body_id, side, nerve, target_muscle,
  anatomical_attachments, activation_model, recruitment,
  delay_ms, evidence, confidence
```

嗅觉：气味在触角/下颚须位置的浓度与时序，经过受体模型，进入相应嗅觉神经元。味觉：腿或口器接触溶液/食物时，才激活相应味觉神经元，不远程“闻到糖味”。视觉：局部视网膜输入和正确视野/视网膜拓扑，进入对应光感受器与视叶回路，不能用单一light变量。机械和本体感觉：把关节角度、角速度、负载、触觉等经过受体编码后送入对应感觉细胞，不能直接提供目标方向或最优动作。

运动输出必须最终来自运动神经元，经过神经肌肉接头与肌肉。下行神经元到预制步态控制器可以保留为明确标记的工程对照，但不能冒充脑—腹神经索—运动神经元完整实现。不同连接组中的细胞名称与ID必须交叉映射，不能复用数值ID。

验收：任何一个I/O通道都能说明“哪个器官、哪类细胞、哪个ID、什么单位、什么证据”；打乱这些对应关系的对照应显著削弱任务相关预测。

## 4. P0/P1：具有物理时间与受体机制的神经动力学

### 4.1 多精度原则

第一层先建立带时间常数、可复核的连续动力学参考实现。第二层按细胞性质使用带适应/突触电导的点神经元和脉冲模型；已知依赖级电位的通路不强制脉冲化。第三层只对验证误差确实来自树突/轴突分区计算的关键回路引入多室电缆模型。不能认为全体改成复杂离子通道模型就自动更真实。

可采用的电导模型框架：

```text
C_i dV_i/dt = -gL_i(V_i-EL_i)
             - Σ(j,r) g_ijr(t)(V_i-Er)
             - a_i + I_sens_i + I_mod_i + I_gap_i
```

其中C、g、E、适应、释放概率、传导延迟和背景活动必须有单位和来源。对未实测量使用分层先验和参数集合，而不是捏造逐神经元的精确值。

结构计数只作为初始约束，例如 `gbar_ijr = count_ij * scale(pre_type, post_type, receptor)`。接收细胞的受体与离子反转电位决定作用，不能把所有未知/调制递质指定+1，也不能把谷氨酸在全部组织中的作用固定为一种符号。调制递质需要与快突触电流区分。转录组表达可约束受体/通道候选，但不等同于实测蛋白数量或电导。

### 4.2 时钟方案（候选工程值，需收敛验证）

|子系统|初始设置|必须验证|
|---|---|---|
|快速神经动力学|0.1 ms；慢速率模型可单独配置|dt减半后的响应差异|
|步行身体/接触|0.05–0.2 ms候选范围|能量、接触稳定性、运动学收敛|
|神经—肌肉—本体反馈交换|0.5–1 ms候选范围|延迟对反射和相位的影响|
|代谢/慢调制|10–100 ms或经验证更慢|不改变快回路结果|
|界面|30–60 Hz|只读，不改变仿真轨迹|

这些不是果蝇生理时间常数的实测声明，飞行、快速机械反射与某些电导模型可能要求更小步长。

参考执行器采用Brian2或简单可审计的CPU实现；通过参考验证后，再用GeNN/PyGeNN等GPU代码生成后端加速。先固定模型方程与容差，再优化速度。对现有代码，立即修正 `FullBrains.forward` 不使用dt的问题。

验收：静息、输入—输出曲线、突触响应、适应和延迟符合选定实验；未知量附区间；无依赖GUI帧率的神经行为。

## 5. P0/P1：先做一个真实闭环的腿，再扩展整只身体

选择FlyGym作为主身体接口；优先锁定所需功能测试通过的版本。2026年官方FlyGym已发布2.x接口，与旧1.x不兼容。当前官方FlyMimic肌骨示例仍是实验性左前腿、15个Hill型肌肉驱动，其余腿并非完整肌肉驱动。这是很好的起点，不是已完成的全身神经肌肉映射。

建议顺序：

1. 复现左前腿已公开运动学，确认坐标和单位。先验证身体，不把模仿学习结果当成神经机制。
2. 补上所选关节运动神经元—肌肉对应与募集曲线，刺激单神经元/神经元组，测量肌肉力与关节响应。
3. 加入肌肉激活动力学、力—长度/速度关系、被动弹性、力臂和负载。
4. 把关节与负载反馈通过相应本体感觉细胞送回腹神经索，完成真实定义的感觉—神经—肌肉闭环。
5. 逐腿扩展，处理左右和前中后腿的解剖差异；再验证六足协调、转向和地形。
6. 口器和摄食另做子模型。飞行作为后续独立工作包：翅铰链、胸部/飞行肌、平衡棒反馈和气动力都需验证，不能复用一个“lift”数值。

对多种默认身体模型，要核查其雌性来源与雄性MaleCNS的差异；使用雄性体型、质量分布和目标肌肉数据校准后才能提高对应程度。利用flybody的行走/飞行基线做比较是合理的，但其运动控制器本身不证明所用神经机制真实。

验收：肢体不是前端正弦动画；运动神经元刺激与肌肉/关节响应可预测；本体感觉消融产生预期差异；物理效应与神经策略可分离检验。

## 6. P1/P2：内部状态、可塑性和高精度机制

### 6.1 不可变结构和可变功能分离

```text
共享、只读：解剖拓扑、突触结构计数、数据来源
个体独立：膜状态、适应、递质/调质、短时突触状态、学习权重
```

先在有实验证据的蘑菇体回路中增加受多巴胺等信号调制的局部可塑性与时间关系；不要对全脑统一套任意STDP。结构校验和不应阻止功能性突触效能改变。离线优化参数是科学校准；动物在生命周期内通过局部生理机制改变权重才是模型中的学习，两者分别记录。

### 6.2 内稳态

先建摄入—嗉囊/消化—营养吸收—活动消耗和水分收支，再建睡眠/唤醒、昼夜节律及有实验支持的调质影响。饥饿和口渴改变神经回路与感觉增益，不调用“寻找最近食物”的外部规划器。

允许由数据约束的神经背景活动和随机释放；可复现的随机种子不意味着可以随机选方向强制探索。零状态适合作为软件测试夹具，不应默认代表真实动物的生理初始状态。

两路任意信号从生理生产版本移除，或仅留在工程沙盒。需要社交时，另建立有来源的求偶声音、振动、信息素及其感受器和运动器官；不把无语义标量称为真实交流或语言。

### 6.3 更高保真度的扩展次序

按未解释的实验结果确定优先级：关键神经元多室计算与形态；电突触；受体/通道空间分布；慢调质与神经肽；胶质与离子稳态；更完整的消化、呼吸、代谢和内分泌。生殖、老化、发育和遗传需要独立数据与机制；随机复制或扰动连接矩阵不等于生物进化。

## 7. 实验数据与模型校准

优先补三类数据：

|数据包|关键字段/实验|作用|
|---|---|---|
|I/O身份和神经肌肉映射|细胞类型、body ID、侧别、外周器官、神经束、肌肉和光学匹配|先把模型接对|
|动力学和突触效能|代表性细胞膜参数/输入输出、突触前激活后的响应、释放与适应、神经调质条件|识别不能由连接数决定的参数|
|同步功能—运动数据|刺激时序、细胞活动、3D姿态、接触/负载，注明性别日龄品系温度|约束闭环并做独立预测|

已有转录组、细胞类型图谱和生理论文用于分层先验。新实验优先选择最能区分候选模型、最影响任务预测的细胞和连接，避免平均分配资源给全部神经元。

拟合目标同时包含神经响应、肌肉/运动学、行为分布、干预效应以及偏離生物先验的惩罚。钙成像数据先加入指示器响应/噪声模型，不能把膜电位或脉冲逐点当成荧光。

按动物、实验条件、刺激和部分神经元类别做训练/验证/测试划分，避免同一轨迹相邻片段泄漏。保留多个与现有证据同样相容的参数模型，用它们预测分歧指导下一轮实验。

## 8. 验收矩阵

|层级|应交付的证据|不能替代它的东西|
|---|---|---|
|软件正确性|数值对照、单位测试、因果边界、重启一致性|神经生理真实性|
|结构正确性|逐神经元身份/连接/边界覆盖和来源|全部分割行都被使用|
|细胞/回路功能|未用于拟合的刺激响应、时延、适应及活动分布|任意非零神经活动|
|身体|被动动力学、肌肉响应、关节/接触与运动学|看起来像果蝇的动画|
|行为|速度/转向/步态/停走等分布，指定感知任务的表现|一条成功轨迹或短暂存活|
|因果预测|未参与拟合的细胞激活/抑制、感觉阻断、负载变化效应|仅相关性或架构图|

设计无连接组、度数保持重连、打乱I/O、移除本体反馈和限制调质等对照。阈值由真实实验重测可靠性、个体差异和任务误差预注册，不用统一“95%真实”。对照差异是证据的一部分，不是充分证明整个动物等价。

## 9. 90天工作分解（规划估计，不是完成保证）

前提：2–3名计算/仿真人员，能获得神经科学审核与公开实验数据；只有单人时应缩小到数据审计和单回路基线。

|时段|交付|退出条件|主要风险|
|---|---|---|---|
|第1–2周|版本锁定、逐神经元编译器、未知边界报告、保留旧测试|节点身份可核查，不再以所有分割端点模拟脑|注释与版本映射不一致|
|第3–4周|I/O证据表、真实时间神经参考核、受体/符号假设分层|消除随机MBON生产端口、dt真正参与更新|映射不足不能造ID补齐|
|第5–6周|左前腿身体基线、一个感知回路离线基准|身体与神经各自通过独立测试|把预制控制器表现误当神经真实性|
|第7–10周|一条经审核的本体感觉—腹神经索—运动神经元—肌肉闭环|反馈与刺激实验结果可解释|运动神经元—肌肉映射不完整|
|第11–12周|盲测、消融、收敛、性能、未解释结果报告|能明确说明模型解释了什么、失败在哪里|只展示最好轨迹|

90天合理目标：一个架构正确、接口有依据、至少一个子系统闭环可验证的数字雄蝇平台；不是完整自主觅食、飞行、社交和全身生理复刻。

3–6个月阶段：在数据足够时扩展六足身体、转向/停走/简单感觉任务，并开始跨条件检验。6–18个月阶段：多模态、摄食内稳态与局部学习；飞行、求偶、全身肌骨和高精度细胞模型作为独立依赖明确的工作包。之后按预测误差继续细化，不预先宣称某日期能够达到全部生物等价。

## 10. 对现有仓库的修改位置

|现有位置|建议修改|
|---|---|
|`build_full_graph.py`|保留原始段图审计，新增神经元级编译器和映射覆盖审计|
|`habitat3d/brain.py`|随机MBON接口仅留为历史测试夹具，生产接口改为证据注册表|
|`habitat3d/full_brain.py`|后端可替换；有单位的多时钟动力学；结构/生理参数/个体状态分开|
|`habitat3d/ecology.py`|拆分受体、身体、慢生理；去除生产版本的左右推力等伪运动接口|
|`habitat3d/environment.py`|环境只生成物理刺激，逐步替换人工尺度/压缩日周期|
|`habitat3d/ui/scene.js`|仅显示模拟器输出的真实关节状态；无自行摆腿/振翅|
|`habitat3d/test_neural_control.py`|保留主动动作无旁路，但增加神经可塑性、受控生理噪声、真实时钟测试|
|`validation/`|区分软件、结构、生理、行为、因果和性能验证；记录失败与不确定性|

计划新增目录（这里只是设计，不代表模块已经实现）：

```text
connectome/   compiler, provenance, identity_map, graph_audit
physiology/  neurons, receptors, synapses, neuromodulation, plasticity
interfaces/  sensory_map, motor_map, unit_conversions
body/        flygym_adapter, muscles, proprioception, male_calibration
world/       light, odor_transport, contact, nutrients
experiments/ stimulus_protocols, perturbations, measurement_models
validation/  graph, numerical, neural, motor, behavior, causal, benchmarks
```

## 11. 资源与性能

先运行1只模型，再扩展到12只。只读结构可共享，可塑性与生理状态按个体独立保存。

规划资源可从64–128 GB内存、1–2 TB SSD、24–48 GB显存的单GPU开发环境开始；这只是原型资源预留，不是全功能实时性能保证。以约166,700神经元、每细胞10个float32变量计算，单只细胞状态约6.7 MB；每1,000万条神经元对连接，单独32位索引+32位权重约80 MB。延迟、每边可塑性/受体状态、反向传播、物理模型和日志另计，可能占主导。

记录真实计算秒/模拟秒、内存峰值、事件数、子系统耗时、精度和步长。不要用渲染帧率当神经仿真速度，也不能拿身体模拟器单独的GPU速度宣传整个具身脑速度。多室模型和参数拟合扩展前先做小基准，必要时再增加计算资源。

## 12. 核查过的外部资料（检索日期：2026-09-13）

1. Janelia Male CNS Connectome 项目主页和下载文档。入口：`www.janelia.org/project-team/flyem/male-cns-connectome`；`male-cns.janelia.org/download/`。官方下载文档明确连接表包含全部分割段。
2. Berg 等，Sexual dimorphism in the complete Drosophila male central nervous system connectome，Cell，2026；出版社条目标识 `S0092867426009426`。
3. Shiu 等，A Drosophila computational brain model reveals sensorimotor processing，Nature，2024。DOI：10.1038/s41586-024-07763-9。
4. Lappalainen 等，Connectome-constrained networks predict neural activity across the fly visual system，Nature，2024。DOI：10.1038/s41586-024-07939-3。
5. Wang-Chen 等，NeuroMechFly v2: simulating embodied sensorimotor control in adult Drosophila，Nature Methods，2024。DOI：10.1038/s41592-024-02497-y。
6. Vaxenburg 等，Whole-body physics simulation of fruit fly locomotion，Nature，2025。DOI：10.1038/s41586-025-09029-4。身体来源和肌肉局限需与新版本实现分别核查。
7. FlyGym 当前官方迁移与肌肉示例文档：`neuromechfly.org/migration/`；`neuromechfly.org/tutorials/6_muscle_imitation/`。示例明确当前左前腿实验性范围。
8. Özdil 等，Musculoskeletal simulation of limb movement biomechanics in Drosophila melanogaster，ICLR 2026；arXiv:2509.06426。
9. Liu 与 Wilson，Glutamate is an inhibitory neurotransmitter in the Drosophila olfactory system，PNAS，2013。DOI：10.1073/pnas.1220560110。
10. Gengs 等，The target of Drosophila photoreceptor synaptic transmission is a histamine-gated chloride channel encoded by ort (hclA)，JBC，2002。DOI：10.1074/jbc.M207133200。
11. Allen 等，A high-resolution atlas of the brain predicts lineage and birth order underlying neuronal identity，Cell Genomics，2026。DOI：10.1016/j.xgen.2025.101103。用于分子和细胞类型先验，不等于逐突触电生理。
12. Dopamine-Dependent Plasticity Is Heterogeneously Expressed by Presynaptic Calcium Activity in the Drosophila Mushroom Body，2023；PMCID：PMC10616905。局部学习应尊重细胞/回路差异。
13. Brian2 当前时间步长与调度文档：`brian2.readthedocs.io/en/stable/user/running.html`。
14. GeNN 官方项目与文档入口：`genn-team.github.io/`。

结论：最有价值的下一步是把解剖节点、输入输出、时间单位和肌肉闭环接对，再用独立实验把参数约束住。神经元更少但身份正确、闭环经过检验的模型，比把全部分割碎片当神经元运行更接近真实果蝇。
