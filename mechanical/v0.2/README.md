# 牛来机器人：物料表兼容机械骨架 v0.2

这是根据主办方物料表和公开参考尺寸生成的参数化机械版本。它解决“只能看到物料表、无法取得实物尺寸”的问题，但仍不是无需复测即可整套打印的冻结版。

## 本版解决的问题

- TT 电机改为开放式卡箍座，按 70 × 23 × 25 mm 保守包络设计，并提供扎带长槽。
- ESP32、DRV8833、降压板和其他 PCB 不使用供应商专用孔距，统一安装在长圆孔电子层板上。
- 电池托盘扩大到约 100 × 60 mm，并通过绑带固定；不把物料表 66 号电池盒视为已验证的执行器电源。
- 2.42 寸 OLED、HC-SR04 和 24 GHz 雷达只冻结包络与窗口，不冻结孔位。
- 增加 1.4 mm 黄色 PLA 前壳和可拆背壳。
- 物料表没有车轮和万向轮，保留 65 mm 轮占位，并增加后滑块降级打印件。
- 头部保留混元 3D 牛头最大包络；生成式头壳尚未导入。

## 关键文件

- `niulai-bom-compatible-frame-v0.2.FCStd`：FreeCAD 可编辑装配。
- `niulai-bom-compatible-frame-assembly-v0.2.step`：骨架、薄壳与硬件包络装配。
- `niulai-bom-compatible-frame-print-parts-v0.2.step`：18 个打印件合集。
- `stl/`：独立打印件；16、17号是黄色前后壳，18号是无万向轮时的后滑块。
- `validation-report-v0.2.json`：包络、碰撞、粗略重心、公开尺寸依据和未冻结项。
- `niulai-bom-compatible-overview-v0.2.png`：整机工程包络图；透明牛头不是最终外观。
- `niulai-bom-compatible-chassis-v0.2.png`：兼容底盘爆炸图。
- `niulai-bom-compatible-head-v0.2.png`：舵机、OLED和超声波接口爆炸图。

## 公开尺寸依据

- ESP32-S3：主办方只写 N16R8，无法确定开发板版型。以 Espressif DevKitC-1 官方尺寸图作为较大参考，再扩展为 66 × 32 mm 兼容区。
- TT 电机：主办方未给供应商、减速比和轴心图。参考公开黄壳 TT 产品的约 70 mm 长度，安装结构不依赖固定螺孔。
- SG90：TowerPro 公布本体为 23 × 12.2 × 29 mm；头部仍必须换成可定位舵机，不能使用物料表的 360°连续旋转件。
- OLED：参考 Waveshare 2.42寸 SSD1309 模块 61.5 × 39.5 mm，设计包络放宽到 66 × 44 mm。
- HC-SR04：公开资料给出 45 × 20 × 15 mm，本版增加接插件与装配余量。
- MP1584EN：常见迷你板约 22 × 17 × 4 mm，但主办方照片显示更大的端子板，因此本版预留 48 × 28 × 16 mm。

## 生成和验证

```powershell
Set-Location "E:\AI WORK\硬件黑客松\mechanical\v0.2"
& "E:\software\FreeCAD\FreeCAD_1.1.0-Windows-x86_64-py311\bin\freecadcmd.exe" -c "exec(open('generate_niulai_bom_frame.py', encoding='utf-8').read())"
& "E:\software\FreeCAD\FreeCAD_1.1.0-Windows-x86_64-py311\bin\freecadcmd.exe" -c "exec(open('export_preview_meshes.py', encoding='utf-8').read())"
python .\render_niulai_bom_frame.py
python .\verify_niulai_bom_frame.py
```

## 打印边界

第一轮只建议打印 `02/03` 电机座、`04` 电池托盘、`05` 电子层板和 `18` 后滑块试片。主办方实物到手后检查电机是否能夹紧、轮轴高度、电池绑带和USB插拔空间，再决定是否打印立柱、头架和完整壳板。

