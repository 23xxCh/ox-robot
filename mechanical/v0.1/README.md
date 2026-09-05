# 牛来机器人开架机电骨架 v0.1

这是一版用于黑客松 P0 的参数化机械布局，不是正式打印冻结版，也不是牛来外壳。

## 当前结构

- 180×140×4 mm 底盘主板。
- 左右两台 TT 电机、64 mm 车轮、后滚珠万向轮和前防倾支点。
- 下置 2S 电池仓，电子模块位于独立上层板。
- 两根承力颈柱、PAN 转头平台、TILT U 型架和独立 MOUTH 嘴部舵机架。
- 头部外壳接口板与背部 Insta360 四孔预留接口。
- 全部运动舵机均按 180°可定位舵机占位，禁止用 360°连续旋转舵机替代。

## 文件

- `niulai-open-frame-v0.1.FCStd`：FreeCAD 可编辑主文件。
- `niulai-open-frame-assembly-v0.1.step`：含硬件占位的装配检查文件。
- `niulai-open-frame-print-parts-v0.1.step`：仅可打印工程件。
- `stl/`：15 个分件 STL。
- `validation-report-v0.1.json`：包络、打印空间、碰撞和粗略重心检查。
- `niulai-open-frame-overview-v0.1.png`：不透明的整机开架骨架总览。
- `niulai-open-frame-chassis-v0.1.png`：底盘动力、电子层和支撑件显示层爆炸图。
- `niulai-open-frame-head-mechanism-v0.1.png`：PAN、TILT、MOUTH 三执行器显示层爆炸图。
- `niulai-open-frame-v0.1.png`、`niulai-open-frame-mechanisms-v0.1.png`：兼容旧链接的总览与头部图副本。

爆炸图只在渲染时把零件拉开，便于辨认安装关系；不会修改 `FCStd`、STEP 或 STL 中的真实装配坐标。旧预览曾把 FreeCAD 组合对象和其子零件重复绘制，造成透明重影，现已从渲染器中排除组合对象。

## 重要边界

TT 电机、轮子、SG90、2S 电池和万向轮尚未拿到，当前尺寸是可编辑占位参数。打印整套前应先打印电机座、舵机座和万向轮支架试片；实物到货后测量包络、轴心、孔距和线束出口，再生成 v0.2。

`validation-report-v0.1.json` 中的重心只是基于占位质量的静态包围盒代理，不替代带最终重量假负载的急停、防倾和热测试。

## 重新生成

```powershell
Set-Location "E:\AI WORK\硬件黑客松\mechanical\v0.1"
& "E:\software\FreeCAD\FreeCAD_1.1.0-Windows-x86_64-py311\bin\freecadcmd.exe" -c "exec(open('generate_niulai_open_frame.py', encoding='utf-8').read())"
python .\export_preview_meshes.py
python .\render_niulai_open_frame.py
```
