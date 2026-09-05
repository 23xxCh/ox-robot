# 牛来角色图生 3D 输入图 v1

## 文件用途

- `niulai-three-quarter.png`：单图生成入口首选。
- `niulai-front.png`：多视图正面。
- `niulai-left.png`：多视图左侧面。
- `niulai-back.png`：多视图背面。
- `niulai-turnaround-2x2.png`：人工核对角色一致性的母版，不建议作为单张图直接上传到图生 3D。

## 使用顺序

1. 只有单图入口时，先上传 `niulai-three-quarter.png`。
2. 支持多视图时，分别上传 front、left、back；不要把四宫格当作单个视角。
3. 生成时优先选择较干净的网格/智能拓扑，不需要先生成毛发卡片或复杂毛发几何。
4. 导出 GLB/OBJ 进入 Blender，先删除漂浮面、修复非流形，再按机器人结构切成头壳、躯干、背盖和嘴壳。
5. 这些图片只定义角色外形。电机、舵机、电池和 ESP32 的承力结构仍由 FreeCAD 参数化骨架决定。

## 建议追加提示词

```text
Create a clean watertight stylized character mesh with simple topology and symmetrical limbs. Preserve the short horns, large ears, broad muzzle, sleepy half-lidded eyes and pear-shaped body. Avoid separate hair cards, floating fur strands, clothing, props, base, text and extra accessories. Keep mouth geometry separable for later mechanical modification.
```

## 风险

图片参考电影角色形象，仅用于牛来机器人原型设计。公开参赛、传播或商业化前仍需核对角色知识产权和比赛规则。
