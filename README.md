# MaleCNS Language World · 微境

本地 3D 果蝇外形代理观察世界：觅食、饮水、避雨、有限词符交流、独立状态与存档。默认生产模式使用官方 MaleCNS v1.0 **完整分割连接图**，没有按神经元类型、递质、脑区或弱连接裁剪。

## “全量”到底是什么

| 数据/计算 | 当前定义 |
| --- | --- |
| 来源 | 官方 `connectome-weights-male-cns-v1.0-minconf-0.5.feather` |
| 结构图 | 88,384,522 个分割单元，151,856,684 条连接，排除行数 0 |
| 个体 | 默认 12 个，共享不可变矩阵，各自独立磁盘映射神经状态 |
| 状态计算 | 逐个体完整 CSR 乘法；float32 状态磁盘映射，不截断活动或删边 |
| GUI 神经图 | 仅显示 97 个 MBON 探针，不是实际计算范围 |
| 生产模式 | 强制全图神经计算；不支持跳过神经核心或修改结构权重 |

**这不是“所有个体完全由真实生理神经权重控制”。** 官方公开的是结构连接计数，包含大量分割碎片，不能等同于八千多万个完整神经元。程序加入行归一化、递质符号假设、`tanh` 动力学和人工输入输出端口。乙酰胆碱采用 +1，GABA/谷氨酸采用 −1；未知和调制递质采用明确的 +1 结构传播假设。后者不是实测突触作用。

导航、稳态需求与词符语义仍是混合工程控制器；真实连接图调节行为，而非已经证明所有行为均由生物神经机制独立产生。没有自由语言、词义从零学习、肌肉/气动校准或遗传进化的证据。

来源：[官方完整图与 CC-BY 说明](https://male-cns.janelia.org/download/)。源码、GUI 与数据声明分别见 [许可说明](LICENSE.md) 和 [数据来源](DATA_PROVENANCE.md)。

## 在本机运行

需要 64 位 Python 3.12、支持 WebGL 2 的浏览器、足够内存和磁盘。完整构图临时文件及神经工作映射约十余 GB；建议至少 16 GB RAM 和 20 GB 可用磁盘。全图模式的实际推进速度取决于状态稀疏程度和硬件，不承诺实时 1×；UI 显示真实每步耗时。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe download_data.py --profile core --out data/raw
.venv/Scripts/python.exe build_full_graph.py
.venv/Scripts/python.exe habitat3d/accept_full.py
powershell -ExecutionPolicy Bypass -File habitat3d/start.ps1
```

也可在其他系统中运行 `.venv/bin/python habitat3d/server.py --brain-mode full`。打开 <http://127.0.0.1:8765>。Three.js 运行文件已本地内置，运行 GUI 无需 npm 或 CDN。构图采用存在位图加前缀计数进行精确索引，并检查原文件 SHA-256、重复边、所有计数总和与游标一致性。

下载或校验失败时会停止，不会偷偷回退为随机图或 MBON 小图。仓库不提交 GB 级原始数据、虚拟环境、本机运行存档或凭据；所需文件从官方来源重建。

## 干净 init

`init/world_state.json` 是固定种子 20260913、12 个体、模型时间 0、暂停状态的初始世界。全部神经活动为精确零，经验、资源记忆和所有事件计数指标均为零；`init/manifest.json` 记录图和存档 SHA-256。初始系统日志仅记录世界建立，没有历史实验或学习状态。

第一次启动生产服务从 init 建立当前世界。之后全量模式每 120 秒自动保存（保存会等待当前计算步完成）到 `habitat3d/state/world_state.json`，不会改写 init。关闭 GUI 后服务仍继续；停止服务执行 `habitat3d/stop.ps1`。

要回到 init：先停止服务，把当前 `habitat3d/state/world_state.json` 移到一个备份位置，再启动。恢复不会把关机时间补算入世界。`accept_full.py` 会重新生成并验证干净 init；不要把它用于覆盖尚未备份的自定义 init。

## 观察方式

拖动旋转、滚轮缩放、点击个体并跟随；支持暂停、单步、目标倍速、轨迹、天气和资源干预。个体会发送“糖/水/荫/险/空”与九宫方位；需要实际调查和接触才能计为有效线索。人的输入仅支持有限词符，不支持自由中文。全图权重固定，但个体局部记忆和信任仍会更新。

## 验证

`habitat3d/accept_full.py` 实际加载全图、更新 12 个体、验证实际更新与独立参考计算一致、压缩存档精确续跑以及生产模式无法绕过神经核心。实测报告见 `validation/`。

```powershell
# 快速回归使用明确的小图模型，不能当作全图性能证据
.venv/Scripts/python.exe -m unittest discover -s habitat3d -p test_model.py
# 全量验收：需要已下载并构建的完整真实图
.venv/Scripts/python.exe habitat3d/accept_full.py
```

早期 97 节点版本的成绩不作为此全图版本的语言、生存或拓扑优势证据。
