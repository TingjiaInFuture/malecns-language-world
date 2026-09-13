# 公开数据接入实录（2026-09-13）

本记录基于当前 Windows 工作区的实际下载与检查。总体为部分完成；生理闭环未验收。另一会话的 `/mnt/data/` 路径不是本机资产。

## 已取得的资产

- MaleCNS 官方注释已在本地；保持 `male-cns:v1.0` 身份。7 个左前腿胫节运动候选来自官方注释，不是正式生产接口。
- [MANC 论文](https://elifesciences.org/articles/96084)的实际下载文件是 `elife-96084-supp3-v1.csv` 和 `elife-96084-supp6-v1.csv`。两表已保存于 `data/physiology_raw/manc/`，下载回执含 URL、字节数和本地 SHA-256；源站未提供独立 SHA-256，不能声称经过发布者哈希验证。
- [FeCO 作者仓库](https://github.com/chrisjdallmann/feco-inhibition)的数据说明、观测滤波 MATLAB 源码和配置已下载。它们是说明和代码，没有实测钙活动文件。
- [运动实验相关 Zenodo 记录](https://zenodo.org/records/4527659)的 README、探针标定及 force-per-spike 分析入口已保存于 `data/physiology_raw/motor-author/`。3 个文件均校验发布者 MD5，并记录本地 SHA-256。该 Zenodo 记录提供分析代码；没有取得原始细胞/试次压缩包。
- 两组 Dryad 版本和完整文件目录已保存于 `data/physiology_raw/*-catalog.json`，包括发布者摘要及字节数。

完整机器清单：`validation/public-data-availability.json`。下载失败项的 `local_path` 为 null。

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

## 原始记录的访问障碍

[FeCO Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.gqnk98t16)及[运动 Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.76hdr7stb)的元数据可访问，但本次公开下载请求返回 HTTP 403，API 文件下载返回 401。页面访问、正常 Referer/cookie 会话和旧公开路径亦未解决。没有使用凭据或绕过访问控制。

FeCO 首选文件 `hook_flexion_01_magnet.parquet` 的发布者字节数为 14,993,835，SHA-256 为 `d4a8c10f2700fe06f142da438e52797c99636fbbad2e1c04c1cc29c9fe080abd`。当前没有这个文件，`validation/feco-run-status.json` 记录实际入口检查结果 `not_run_missing_experimental_file`。未生成实测分数或保留集协议。

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
