# MaleCNS Language World · 微境

本地 3D 神经自主动作实验世界，默认 12 个果蝇外形代理。生产模式使用 MaleCNS v1.0 完整公开分割连接图：**88,384,522 个端点、151,856,684 条边，额外排除 0 行**。每只个体共享固定结构矩阵，具有独立完整神经状态。

## 本版的行为边界

主动动作只有一条通路：**局部感觉 → 完整连接图神经更新 → 固定运动端口 → 身体与环境 → 下一步感觉**。

已移除需求优先级选目标、资源坐标记忆、自动寻路、随机探索、规则避障、自动进食与避雨、定时广播、预设词义、信任与人类动作指令。没有失效后的行为兜底。饥饿、碰壁或长期静止会如实发生，不能据此宣称模型已经具备生存能力。

八个神经读出分别控制左/右推进、升力、口器伸展、泵吸、两路无语义信号和制动。零读出不产生主动动作；物体仍受到重力、惯性和接触约束。进食/饮水必须同时满足实际接触和两个口器通道激活。信号按距离衰减，下一步被其他个体的感觉端口接收；不存在“糖、水、庇护”的内置语义。

**神经独占主动动作，不等于生物等价。** 数据包含大量分割碎片；结构计数不等于实测生理权重。行归一化、递质符号、tanh 动力学、24 个感觉/8 个运动端口和简化身体均是模型假设。端口仍固定投射到 97 个 MBON 探针，不是已经审核的真实感觉/运动神经元对应关系。全图计算没有消除这一限制。未知/调制递质的 88,228,690 个端点使用 +1 传播假设，不代表已知兴奋性。

模型不含生物局部可塑性、肌肉/气动校准或繁殖遗传；没有语言涌现、自然进化或生存优势证据。完整边界与公式见 [神经控制说明](NEURAL_CONTROL.md)。

来源：[官方数据](https://male-cns.janelia.org/download/)，[来源和校验值](DATA_PROVENANCE.md)，[许可证](LICENSE.md)。

## 运行

需要 64 位 Python 3.12；建议至少 16 GB RAM、20 GB 可用磁盘。完整神经状态约 4.24 GB；速度受本机限制，0.25 模型秒通常需要十余秒实际计算，不是实时生物仿真。GUI 显示实际计算耗时。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe download_data.py --profile core --out data/raw
.venv/Scripts/python.exe build_full_graph.py
powershell -ExecutionPolicy Bypass -File habitat3d/start.ps1
```

打开 http://127.0.0.1:8765 ，或双击 `start.cmd`。Linux 可使用 `.venv/bin/python habitat3d/server.py --brain-mode full`。Three.js 已内置，GUI 不需要 CDN。神经权重数据、虚拟环境、运行存档不提交 Git；下载或校验失败会明确报错，不会回退小图。

通过窗口观察个体、神经活动、两路信号幅度及推进幅度；可暂停、单步、导出和干预降雨、露水、果实。文字指令已禁用。外形肢体动画仅用于显示，不是肌肉仿真。

## 初始状态与旧版迁移

`init/world_state.json` 使用 `habitat3d/2` 和 `neural-only-actuation-v1`，固定种子 20260913、12 个体、时间 0、暂停、全部神经状态精确为零、主动输出和速度为零。`init/manifest.json` 记录存档和源图 SHA-256。启动后从此状态读取，之后只保存到 `habitat3d/state/world_state.json`，不会覆盖 init。

旧版混合控制存档被明确拒绝，不能静默迁移。升级前执行 `stop.cmd` 保存并停止；将 `habitat3d/state/world_state.json` 重命名备份后再启动。旧控制器保留在 `legacy_ecology.py` 供历史回归，生产控制器不导入它。

## 验收

```powershell
# 小图机制/因果测试和明确标记的旧版回归
.venv/Scripts/python.exe -m unittest discover -s habitat3d -p 'test_*.py'
# 完整图实际计算、感觉消融、精确续跑和短程闭环；会重新生成 init
.venv/Scripts/python.exe habitat3d/accept_full.py
# 启动暂停的生产 init 后，用已安装的 Playwright + Chrome 检查 GUI
cd habitat3d
node browser_test.mjs
```

测试报告见 [validation](validation/README.md)。短程完整图验收与小图因果测试分别记录；后者不能替代完整图运行证据，二者都不能替代真实动物实验。
