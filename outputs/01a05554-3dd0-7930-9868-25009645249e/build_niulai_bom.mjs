import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.join(outputDir, "牛来机器人-BOM-v0.1.xlsx");

const COLORS = {
  navy: "#16324F",
  blue: "#2F6690",
  paleBlue: "#EAF2F8",
  paleGreen: "#E9F7EF",
  paleYellow: "#FFF4CC",
  paleRed: "#FDECEC",
  paleGray: "#F3F4F6",
  border: "#CBD5E1",
  text: "#1F2937",
  white: "#FFFFFF",
};

const bomItems = [
  [1, "P0", "主控", "ESP32-S3 核心板 N16R8", "16MB Flash + 8MB PSRAM；到手后复核板载模组与引脚", 1, 0, null, "块", "比赛物料", "46", 40, "冻结", null, null, "G0：拍照记录丝印、供电方式、USB与可用GPIO", "核心计算与控制板", "黑客松物料表-原图.png；系统架构 §5.1"],
  [2, "P0", "移动底盘", "TT 马达", "普通直流减速电机；仅作P0原型候选", 2, 0, null, "个", "比赛物料", "51", 20, "原型候选", null, null, "G1：测额定电压、空载/堵转电流、假负载扭矩与温升", "最终重量不足则换25GA/37GB；Sim2Real需编码器", "黑客松物料表-原图.png；系统架构 §5.1"],
  [3, "P0", "显示", "2.42寸 OLED 屏幕", "双眼共用一块屏；驱动芯片与I2C/SPI接口待确认", 1, 0, null, "块", "比赛物料", "53", 5, "首选待实测", null, null, "G0：确认驱动芯片、电压、接口、刷新率和可视区域", "数量有限，优先领取", "黑客松物料表-原图.png；系统架构 §5.1"],
  [4, "P0", "音频输出", "4Ω喇叭", "与MAX98357A I2S功放配套；额定功率待确认", 1, 0, null, "个", "比赛物料", "55", 30, "待实测", null, null, "G0/G1：确认额定功率；最大音量无破音且不触发棕断", "ESP32不可直接驱动", "黑客松物料表-原图.png；系统架构 §5.1"],
  [5, "P1", "灯效", "WS2812灯带", "状态与情绪灯效；控制线串阻并按长度核算供电", 1, 0, null, "条", "比赛物料", "57", 40, "P1可选", null, null, "G1：全亮峰值电流与音频/电机并发测试", "P0可先不装", "黑客松物料表-原图.png；系统架构 §5.1"],
  [6, "P0", "人员存在检测", "24GHz毫米波雷达（120×120）", "原图描述：运动11m、微动10m；优先候选", 1, 0, null, "块", "比赛物料", "61", 5, "首选待实测", null, null, "G0：确认型号、UART/GPIO、电压、FOV与静止人体检测", "胸前非金属雷达窗后安装", "黑客松物料表-原图.png；系统架构 §5.1"],
  [7, "P0", "人员存在检测", "24GHz毫米波雷达（100°）", "原图描述：16m存在、25m运动；61号不可用时备选", 0, 0, null, "块", "比赛物料", "60", 3, "备选", null, null, "G0：仅在61号不可领或接口不兼容时评估", "不与61号同时装机", "黑客松物料表-原图.png；系统架构 §5.1"],
  [8, "P0", "前向避障", "超声波 HC-SR04", "前方障碍检测；Echo必须做5V→3.3V电平转换", 1, 0, null, "块", "比赛物料", "67", 10, "冻结", null, null, "G1：测盲区、壳体开孔影响与最大速度下停车距离", "不能作为人员存在检测", "黑客松物料表-原图.png；系统架构 §5.1"],
  [9, "P0", "电源", "MP1584EN降压模块", "逻辑/音频、舵机、电机分路候选；具体路数按实测调整", 3, 0, null, "块", "比赛物料", "40", 33, "首选待实测", null, null, "G1：逐路测持续/峰值电流、纹波、温升与棕断", "共地但负载分域；禁止从ESP32板给电机供电", "黑客松物料表-原图.png；系统架构 §5.1"],
  [10, "P1", "日志存储", "SD卡读卡模块", "P1结构化事件日志；P0先用串口/RAM环形日志", 1, 0, null, "块", "比赛物料", "41", 33, "P1可选", null, null, "G2：连续写入、掉电恢复与写满轮转测试", "不默认存原始音频或图像", "黑客松物料表-原图.png；系统架构 §5.1"],
  [11, "P0", "原型调试", "电阻包", "超声波分压、上拉/下拉、LED与信号调试", 1, 0, null, "包", "比赛物料", "47", 30, "冻结", null, null, "G0：确认常用阻值覆盖", "最终装机改为焊接/端子连接", "黑客松物料表-原图.png"],
  [12, "P0", "原型调试", "面包板", "桌面联调使用，不进入移动整机", 1, 0, null, "块", "比赛物料", "48", 40, "冻结", null, null, "G0：桌面原型可用；G2前移除", "运动环境禁止把面包板当永久连接", "黑客松物料表-原图.png"],
  [13, "P0", "原型调试", "杜邦线（公公/公母/母母）", "桌面联调线材", 1, 0, null, "套", "比赛物料", "49", 40, "冻结", null, null, "G0：确认线序；G2前替换为锁止接插件", "移动整机不依赖松动杜邦线", "黑客松物料表-原图.png"],
  [14, "P0", "本地输入", "按键开关模块", "鼻部确认/录音触发或调试输入；不承担急停", 2, 0, null, "块", "比赛物料", "29", 33, "原型候选", null, null, "G0：去抖、长按与断线默认态测试", "急停必须使用独立锁存式实体按钮", "黑客松物料表-原图.png"],
  [15, "升级", "姿态感知", "高性能6轴MEMS运动跟踪模块", "Sim2Real/姿态事件候选；确切芯片与量程未知", 1, 0, null, "块", "比赛物料", "69（原图疑似59）", 5, "待实测", null, null, "G0：核对原图误号、芯片、I2C地址、量程与采样率", "原图编号顺序为58、69、60，保留疑点不擅自改号", "黑客松物料表-原图.png"],
  [16, "P0", "电机驱动", "DRV8833双路电机驱动模块", "1.5A RMS/桥为芯片级参考；模块散热与堵转电流必须实测", 1, 0, null, "块", "自备", "—", null, "首选待实测", null, null, "G1：驱动持续/峰值电流、堵转保护与30分钟温升", "若不满足则换更高电流驱动；TB6612仅备选", "系统架构 §5.1"],
  [17, "P0", "音频输入", "INMP441 I2S麦克风", "16kHz单声道；耳部安装并远离扬声器和电机", 1, 0, null, "块", "自备", "—", null, "冻结", null, null, "G1：装壳前后KWS/录音信噪比与电机噪声测试", "普通声音传感器不能替代", "系统架构 §5.1"],
  [18, "P0", "音频输出", "MAX98357A I2S功放", "驱动4Ω扬声器；逻辑/音频独立供电", 1, 0, null, "块", "自备", "—", null, "冻结", null, null, "G1：最大音量、失真、温升与电源压降测试", "与麦克风物理隔离", "系统架构 §5.1"],
  [19, "P0", "头部动作", "180°可定位金属齿舵机", "转头/点头两轴；扭矩按头部实重与力臂×2.5动态系数选", 2, 0, null, "个", "自备", "—", null, "待称重选型", null, null, "G0/G2：称重算扭矩、软/机械限位、卡滞与100次循环", "禁止使用50号360°连续旋转舵机", "系统架构 §5.1"],
  [20, "P0", "嘴部动作", "180°微型定位舵机", "嘴部开合；弹簧回位并设置机械限位", 1, 0, null, "个", "自备", "—", null, "待称重选型", null, null, "G2：软限位、堵转超时、线缆余量和100次循环", "可从轻载微型舵机起步", "系统架构 §5.1"],
  [21, "P0", "电源", "2S带保护电池包", "7.4V标称；容量、放电倍率、接口与认证待最终负载确认", 1, 0, null, "包", "自备", "—", null, "待实测", null, null, "G1：BMS、反接、峰值电流、低电阈值、固定与运输检查", "不采用裸电芯或未知保护电池盒", "系统架构 §5.1"],
  [22, "P0", "充电", "8.4V合规充电器", "与2S电池化学体系、接口和充电电流匹配", 1, 0, null, "个", "自备", "—", null, "待实测", null, null, "G1：充电截止、温升、接口防呆；比赛版不边充边跑", "必须与最终电池成套确认", "系统架构 §5.1"],
  [23, "P0", "安全", "锁存式实体急停按钮", "直接切断执行器电源；逻辑保持上电记录原因", 1, 0, null, "个", "自备", "—", null, "冻结", null, null, "G1：运动中触发/复位各50次，目标≤100ms进入安全态", "普通按键模块不能替代", "系统架构 §5.1"],
  [24, "P0", "安全", "保险丝及保险座", "额定值按最终堵转与线路电流确定", 1, 0, null, "套", "自备", "—", null, "待实测", null, null, "G1：短时堵转与过流验证；不超过线材/接插件额定值", "安装在电池总输出近端", "系统架构 §5.1"],
  [25, "P0", "电源", "主电源开关", "整机总电源；额定电流与电池输出匹配", 1, 0, null, "个", "自备", "—", null, "待实测", null, null, "G1：带载通断、温升、误触与维护可达性", "与急停职责分开", "系统架构 §5.1"],
  [26, "P0", "移动底盘", "TT马达配套车轮", "建议约65mm；最终轮径需与扭矩和壳体离地间隙联调", 2, 0, null, "个", "自备", "—", null, "原型候选", null, null, "G1：同轴度、打滑、急停、转弯和壳体干涉", "轮径改变需同步修正控制参数", "系统架构 §5.1"],
  [27, "P0", "移动底盘", "后部滚珠轮/万向轮", "与两驱轮组成稳定三点支撑", 1, 0, null, "个", "自备", "—", null, "冻结", null, null, "G1：接缝通过、转向阻力、防卡滞与急停稳定性", "优先低矮轻量结构", "系统架构 §5.1"],
  [28, "P0", "机械安全", "前防倾支点", "正常行驶不拖地，急停或前倾时先于外壳触地", 1, 0, null, "个", "3D打印", "—", null, "冻结", null, null, "G1/G3：最终重量假负载急停与转向各20次不倾倒", "与底盘工程骨架一体设计", "系统架构 §5.1"],
  [29, "P0", "线束", "锁止接插件与多规格线材套件", "JST-XH/端子等；按电流分线径并做应力释放", 1, 0, null, "套", "自备", "—", null, "待实测", null, null, "G2：摇晃、装拆、拉力、反接防呆与温升检查", "杜邦线仅限桌面调试", "系统架构 §5.1"],
  [30, "P0", "机械装配", "M2/M3螺丝、螺母与垫片", "覆盖舵机、主控、骨架、检修门和电池仓", 1, 0, null, "套", "自备", "—", null, "冻结", null, null, "G0：按实物孔位建立紧固件清单；完成3次无损装拆", "不把关键承力件永久胶粘", "系统架构 §5.1"],
  [31, "P0", "机械装配", "M2/M3热熔螺母", "打印件反复装拆接口", 1, 0, null, "套", "自备", "—", null, "冻结", null, null, "G0/G2：先打印孔径试片，再冻结热熔孔参数", "按材料收缩修正孔径", "系统架构 §5.1"],
  [32, "P0", "3D打印", "PLA/PETG打印耗材", "外观件优先PLA；电机座/舵机座等承力件优先PETG", 1, 0, null, "套", "自备", "—", null, "冻结", null, null, "G0：切片包络、关键接口试片、层间强度与温升检查", "混元/群核只负责外观；FreeCAD骨架负责承力孔位", "系统架构 §5.1"],
  [33, "P1", "扩展结构", "Insta360预留安装座", "仅做加强区、螺纹/绑带接口和重心预留，不安装摄像机", 1, 0, null, "个", "3D打印", "—", null, "P1可选", null, null, "G2：CAD干涉、检修门可达性与重心检查", "P0不采集图像", "系统架构 §5.1"],
  [34, "升级", "Sim2Real", "带编码器减速电机或编码器套件", "替换/改造普通TT马达，提供真实轮速反馈", 2, 0, null, "个", "未来升级", "—", null, "升级项", null, null, "升级门：编码器分辨率、轮速闭环、丢脉冲和低速控制验证", "不与普通TT马达重复采购；二选一", "ESP32 Sim2Real调研；系统架构 §5.1"],
  [35, "排除", "舵机", "SG90（360°）", "连续旋转舵机，不能提供可重复的目标角度", 0, 0, null, "个", "比赛物料", "50", 30, "排除", null, null, "不得用于转头、点头或嘴部定位", "可留作尾巴连续旋转实验，但不进入P0 BOM", "黑客松物料表-原图.png"],
  [36, "排除", "音频输入", "麦克风声音传感器模块", "只能检测声音幅度，不能替代语音采集麦克风", 0, 0, null, "块", "比赛物料", "35", 33, "排除", null, null, "不得用于ASR/KWS音频输入", "语音链路使用INMP441", "黑客松物料表-原图.png"],
  [37, "排除", "电源", "UNO R3移动电源电池盒+电池", "保护、串数、容量、放电能力和接口均未确认", 0, 0, null, "套", "比赛物料", "66", 10, "排除", null, null, "未完成电池/BMS/充电合规核验前不得装机", "正式方案使用成套2S保护电池与充电器", "黑客松物料表-原图.png"],
];

const mappingRows = [
  ["29", "按键开关模块", 33, "采用", 2, "鼻部确认/录音触发与调试输入", "不能替代锁存急停", "黑客松物料表-原图.png"],
  ["35", "麦克风声音传感器模块", 33, "排除", 0, "仅能做声音幅度检测", "旧PRD将其当麦克风不准确；ASR使用INMP441", "黑客松物料表-原图.png"],
  ["40", "MP1584EN降压模块", 33, "采用", 3, "逻辑/音频、舵机、电机分路候选", "具体路数和能力必须按峰值电流实测", "黑客松物料表-原图.png"],
  ["41", "SD卡读卡模块", 33, "采用", 1, "P1结构化日志", "P0可先用串口/RAM环形日志", "黑客松物料表-原图.png"],
  ["46", "ESP32 S3核心板板载1-N16R8", 40, "采用", 1, "主控", "旧PRD主控编号46正确；仍需复核实物丝印", "黑客松物料表-原图.png"],
  ["47", "电阻包", 30, "采用", 1, "分压、上拉/下拉与调试", "最终装机使用焊接/端子", "黑客松物料表-原图.png"],
  ["48", "面包板", 40, "采用", 1, "桌面原型", "不进入移动整机", "黑客松物料表-原图.png"],
  ["49", "杜邦线（公公、公母、母母）", 40, "采用", 1, "桌面联调", "G2前换锁止接插件", "黑客松物料表-原图.png"],
  ["50", "SG90（360）", 30, "排除", 0, "连续旋转", "旧PRD把50号用于转头/点头错误；需自备180°定位舵机", "黑客松物料表-原图.png"],
  ["51", "TT马达", 20, "采用", 2, "P0两驱底盘", "原型候选；最终按假负载和堵转电流决定", "黑客松物料表-原图.png"],
  ["52", "1.54寸OLED屏幕", 5, "备选", 0, "小屏备选", "首选53号2.42寸双眼共屏", "黑客松物料表-原图.png"],
  ["53", "2.42寸OLED屏幕", 5, "采用", 1, "双眼表情显示", "旧PRD写53/54不准确；54号是压力传感器", "黑客松物料表-原图.png"],
  ["54", "RFP602压力传感器", 30, "排除", 0, "本版无刚需", "旧PRD将54号误当OLED；原图54号为压力传感器", "黑客松物料表-原图.png"],
  ["55", "4欧喇叭", 30, "采用", 1, "语音播放", "必须配MAX98357A功放", "黑客松物料表-原图.png"],
  ["57", "WS2812灯带", 40, "采用", 1, "P1情绪灯效", "先核算全亮电流", "黑客松物料表-原图.png"],
  ["69（疑似59）", "（BCG）高性能6轴MEMS运动跟踪传感器模块", 5, "待确认", 1, "姿态/Sim2Real候选", "原图顺序58、69、60，疑似编号笔误；先按原图保留", "黑客松物料表-原图.png"],
  ["60", "24Ghz毫米波雷达（100度范围，16m存在，25m运动）", 3, "备选", 0, "人员存在检测备选", "61号不可用时再评估", "黑客松物料表-原图.png"],
  ["61", "24Ghz毫米波雷达（120×120，运动11m，微动10m）", 5, "采用", 1, "人员存在检测首选", "型号、接口和参数均需实物核验", "黑客松物料表-原图.png"],
  ["66", "UNO R3移动电源电池盒+电池", 10, "排除", 0, "不进入正式供电", "保护、放电与充电方案不明；改用成套2S保护电池", "黑客松物料表-原图.png"],
  ["67", "超声波HC-SR04", 10, "采用", 1, "前向避障", "Echo必须做5V→3.3V电平转换", "黑客松物料表-原图.png"],
];

function styleTitle(sheet, endCol, title, subtitle) {
  sheet.showGridLines = false;
  sheet.mergeCells(`A1:${endCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endCol}1`).format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 18, name: "Microsoft YaHei" },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${endCol}1`).format.rowHeightPx = 38;
  sheet.mergeCells(`A2:${endCol}3`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endCol}3`).format = {
    fill: COLORS.paleBlue,
    font: { color: COLORS.text, size: 10, name: "Microsoft YaHei" },
    wrapText: true,
    verticalAlignment: "center",
    borders: { bottom: { style: "thin", color: COLORS.border } },
  };
  sheet.getRange(`A2:${endCol}3`).format.rowHeightPx = 28;
  sheet.getRange(`A4:${endCol}4`).format.rowHeightPx = 10;
}

function styleTableArea(sheet, headerRange, bodyRange) {
  sheet.getRange(headerRange).format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.white, size: 10, name: "Microsoft YaHei" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { bottom: { style: "medium", color: COLORS.navy } },
  };
  sheet.getRange(headerRange).format.rowHeightPx = 34;
  sheet.getRange(bodyRange).format = {
    font: { color: COLORS.text, size: 9, name: "Microsoft YaHei" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { insideHorizontal: { style: "thin", color: COLORS.border } },
  };
}

const workbook = Workbook.create();
const bomSheet = workbook.worksheets.add("牛来BOM");
const mapSheet = workbook.worksheets.add("比赛物料映射");
const gapSheet = workbook.worksheets.add("采购缺口");
const summarySheet = workbook.worksheets.add("状态汇总");

// Sheet 1: master BOM.
styleTitle(
  bomSheet,
  "R",
  "牛来机器人 BOM · v0.1",
  "黑客松P0移动原型清单。比赛物料的“待购数量”表示尚未领取/获取；自备与升级件表示待采购。预算单价由团队拿到实物规格或真实报价后填写，空白不计入总额。雷达、电机、驱动、电池和舵机在门禁验证前不得宣称最终冻结。",
);
const bomHeaders = [["序号", "优先级", "子系统", "物料/部件", "规格/用途", "需求数量", "已领/已有", "待购数量", "单位", "来源", "比赛编号", "原图库存", "选型状态", "预算单价（元）", "预算小计（元）", "验证门禁", "备注", "来源证据"]];
const bomStart = 6;
const bomEnd = bomStart + bomItems.length - 1;
bomSheet.getRange("A5:R5").values = bomHeaders;
bomSheet.getRange(`A${bomStart}:R${bomEnd}`).values = bomItems;
bomSheet.getRange(`H${bomStart}`).formulas = [[`=MAX(0,F${bomStart}-G${bomStart})`]];
bomSheet.getRange(`H${bomStart}:H${bomEnd}`).fillDown();
bomSheet.getRange(`O${bomStart}`).formulas = [[`=IF(OR(H${bomStart}="",N${bomStart}=""),"",H${bomStart}*N${bomStart})`]];
bomSheet.getRange(`O${bomStart}:O${bomEnd}`).fillDown();
styleTableArea(bomSheet, "A5:R5", `A${bomStart}:R${bomEnd}`);
const bomTable = bomSheet.tables.add(`A5:R${bomEnd}`, true, "NiulaiBOMTable");
bomTable.style = "TableStyleMedium2";
bomTable.showFilterButton = true;
bomSheet.freezePanes.freezeRows(5);
bomSheet.freezePanes.freezeColumns(4);
bomSheet.dataValidations.add({ range: `B${bomStart}:B${bomEnd}`, rule: { type: "list", values: ["P0", "P1", "升级", "排除"] } });
bomSheet.dataValidations.add({ range: `G${bomStart}:G${bomEnd}`, rule: { type: "whole", operator: "between", formula1: 0, formula2: 999 } });
bomSheet.dataValidations.add({ range: `J${bomStart}:J${bomEnd}`, rule: { type: "list", values: ["比赛物料", "自备", "3D打印", "未来升级"] } });
bomSheet.dataValidations.add({ range: `M${bomStart}:M${bomEnd}`, rule: { type: "list", values: ["冻结", "原型候选", "首选待实测", "备选", "待实测", "待称重选型", "P1可选", "升级项", "排除"] } });
bomSheet.dataValidations.add({ range: `N${bomStart}:N${bomEnd}`, rule: { type: "decimal", operator: "between", formula1: 0, formula2: 100000 } });
bomSheet.getRange(`M${bomStart}:M${bomEnd}`).conditionalFormats.add("containsText", { text: "排除", format: { fill: COLORS.paleRed, font: { color: "#991B1B", bold: true } } });
bomSheet.getRange(`M${bomStart}:M${bomEnd}`).conditionalFormats.add("containsText", { text: "待实测", format: { fill: COLORS.paleYellow, font: { color: "#854D0E" } } });
bomSheet.getRange(`M${bomStart}:M${bomEnd}`).conditionalFormats.add("containsText", { text: "待称重", format: { fill: COLORS.paleYellow, font: { color: "#854D0E" } } });
bomSheet.getRange(`M${bomStart}:M${bomEnd}`).conditionalFormats.add("containsText", { text: "冻结", format: { fill: COLORS.paleGreen, font: { color: "#166534", bold: true } } });
bomSheet.getRange(`M${bomStart}:M${bomEnd}`).conditionalFormats.add("containsText", { text: "升级项", format: { fill: COLORS.paleBlue, font: { color: COLORS.navy, bold: true } } });
bomSheet.getRange(`F${bomStart}:H${bomEnd}`).format.numberFormat = "0";
bomSheet.getRange(`L${bomStart}:L${bomEnd}`).format.numberFormat = "0";
bomSheet.getRange(`N${bomStart}:O${bomEnd}`).format.numberFormat = "¥#,##0.00";
bomSheet.getRange(`N${bomStart}:N${bomEnd}`).format.fill = "#FFFCE8";
bomSheet.getRange(`A${bomStart}:A${bomEnd}`).format.horizontalAlignment = "center";
bomSheet.getRange(`B${bomStart}:B${bomEnd}`).format.horizontalAlignment = "center";
bomSheet.getRange(`F${bomStart}:O${bomEnd}`).format.horizontalAlignment = "center";
bomSheet.getRange(`A${bomStart}:R${bomEnd}`).format.rowHeightPx = 52;
const bomWidths = [48, 58, 82, 170, 280, 68, 68, 72, 48, 76, 92, 68, 94, 92, 96, 260, 280, 210];
bomWidths.forEach((width, index) => bomSheet.getRangeByIndexes(0, index, bomEnd, 1).format.columnWidthPx = width);

// Sheet 2: source image mapping and corrections.
styleTitle(
  mapSheet,
  "H",
  "比赛物料映射与旧编号纠错",
  "只收录与牛来直接相关或曾被旧PRD误映射的条目。名称、编号和库存按原图抄录；原图本身存在“58、69、60”的编号跳号，因此六轴MEMS模块保留原图编号并标注疑点。库存是表中总数量，不代表团队已领取。",
);
mapSheet.getRange("A5:H5").values = [["原图编号", "原图名称", "原图数量", "牛来决策", "计划数量", "用途", "纠错/限制", "证据"]];
const mapStart = 6;
const mapEnd = mapStart + mappingRows.length - 1;
mapSheet.getRange(`A${mapStart}:H${mapEnd}`).values = mappingRows;
styleTableArea(mapSheet, "A5:H5", `A${mapStart}:H${mapEnd}`);
const mapTable = mapSheet.tables.add(`A5:H${mapEnd}`, true, "MaterialMappingTable");
mapTable.style = "TableStyleMedium2";
mapTable.showFilterButton = true;
mapSheet.freezePanes.freezeRows(5);
mapSheet.dataValidations.add({ range: `D${mapStart}:D${mapEnd}`, rule: { type: "list", values: ["采用", "备选", "待确认", "排除"] } });
mapSheet.getRange(`D${mapStart}:D${mapEnd}`).conditionalFormats.add("containsText", { text: "采用", format: { fill: COLORS.paleGreen, font: { color: "#166534", bold: true } } });
mapSheet.getRange(`D${mapStart}:D${mapEnd}`).conditionalFormats.add("containsText", { text: "排除", format: { fill: COLORS.paleRed, font: { color: "#991B1B", bold: true } } });
mapSheet.getRange(`D${mapStart}:D${mapEnd}`).conditionalFormats.add("containsText", { text: "待确认", format: { fill: COLORS.paleYellow, font: { color: "#854D0E" } } });
mapSheet.getRange(`A${mapStart}:E${mapEnd}`).format.horizontalAlignment = "center";
mapSheet.getRange(`A${mapStart}:H${mapEnd}`).format.rowHeightPx = 48;
const mapWidths = [90, 280, 82, 82, 82, 200, 340, 210];
mapWidths.forEach((width, index) => mapSheet.getRangeByIndexes(0, index, mapEnd, 1).format.columnWidthPx = width);

// Sheet 3: formula-backed procurement gap view.
styleTitle(
  gapSheet,
  "M",
  "采购缺口 · 自备 / 3D打印 / Sim2Real升级",
  "本表由“牛来BOM”公式引用生成，请在主表更新数量、预算与状态。普通TT马达可支持P0开环原型，但Sim2Real需要编码器反馈；升级件不得与普通TT方案重复采购。",
);
gapSheet.getRange("A5:M5").values = [["序号", "缺口类型", "子系统", "物料", "规格", "需求数量", "已领/已有", "待购数量", "单位", "状态", "预算单价（元）", "预算小计（元）", "验证门禁"]];
const procurementIndices = bomItems
  .map((row, index) => ({ row, sourceRow: bomStart + index }))
  .filter(({ row }) => ["自备", "3D打印", "未来升级"].includes(row[9]));
const gapStart = 6;
const gapEnd = gapStart + procurementIndices.length - 1;
const gapFormulaRows = procurementIndices.map(({ sourceRow }) => [
  `='牛来BOM'!A${sourceRow}`,
  `='牛来BOM'!J${sourceRow}`,
  `='牛来BOM'!C${sourceRow}`,
  `='牛来BOM'!D${sourceRow}`,
  `='牛来BOM'!E${sourceRow}`,
  `='牛来BOM'!F${sourceRow}`,
  `='牛来BOM'!G${sourceRow}`,
  `='牛来BOM'!H${sourceRow}`,
  `='牛来BOM'!I${sourceRow}`,
  `='牛来BOM'!M${sourceRow}`,
  `=IF('牛来BOM'!N${sourceRow}="","",'牛来BOM'!N${sourceRow})`,
  `=IF('牛来BOM'!O${sourceRow}="","",'牛来BOM'!O${sourceRow})`,
  `='牛来BOM'!P${sourceRow}`,
]);
gapSheet.getRange(`A${gapStart}:M${gapEnd}`).formulas = gapFormulaRows;
styleTableArea(gapSheet, "A5:M5", `A${gapStart}:M${gapEnd}`);
const gapTable = gapSheet.tables.add(`A5:M${gapEnd}`, true, "ProcurementGapTable");
gapTable.style = "TableStyleMedium2";
gapTable.showFilterButton = true;
gapSheet.freezePanes.freezeRows(5);
gapSheet.getRange(`A${gapStart}:D${gapEnd}`).format.horizontalAlignment = "center";
gapSheet.getRange(`F${gapStart}:L${gapEnd}`).format.horizontalAlignment = "center";
gapSheet.getRange(`F${gapStart}:H${gapEnd}`).format.numberFormat = "0";
gapSheet.getRange(`K${gapStart}:L${gapEnd}`).format.numberFormat = "¥#,##0.00";
gapSheet.getRange(`A${gapStart}:M${gapEnd}`).format.rowHeightPx = 48;
const gapWidths = [48, 76, 82, 190, 300, 70, 70, 72, 48, 100, 96, 96, 300];
gapWidths.forEach((width, index) => gapSheet.getRangeByIndexes(0, index, gapEnd, 1).format.columnWidthPx = width);

// Sheet 4: compact status and budget summary.
styleTitle(
  summarySheet,
  "H",
  "BOM 状态汇总",
  "所有指标均引用“牛来BOM”。预算只统计已填写单价且仍有待购数量的项目；当前空白预算不代表零成本。正式采购冻结必须完成G0实物确认和G1底盘/电源安全验证。",
);
summarySheet.getRange("A5:B5").values = [["关键指标", "结果"]];
summarySheet.getRange("A6:A12").values = [["BOM总条目"], ["P0条目"], ["比赛物料条目"], ["自备条目"], ["待实测/待选型"], ["排除项"], ["当前预算总额（元）"]];
summarySheet.getRange("B6:B12").formulas = [
  [`=COUNTA('牛来BOM'!$D$${bomStart}:$D$${bomEnd})`],
  [`=COUNTIF('牛来BOM'!$B$${bomStart}:$B$${bomEnd},"P0")`],
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},"比赛物料")`],
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},"自备")`],
  [`=COUNTIF('牛来BOM'!$M$${bomStart}:$M$${bomEnd},"首选待实测")+COUNTIF('牛来BOM'!$M$${bomStart}:$M$${bomEnd},"待实测")+COUNTIF('牛来BOM'!$M$${bomStart}:$M$${bomEnd},"待称重选型")`],
  [`=COUNTIF('牛来BOM'!$M$${bomStart}:$M$${bomEnd},"排除")`],
  [`=SUM('牛来BOM'!$O$${bomStart}:$O$${bomEnd})`],
];
summarySheet.getRange("D5:E5").values = [["来源分类", "条目数"]];
summarySheet.getRange("D6:D9").values = [["比赛物料"], ["自备"], ["3D打印"], ["未来升级"]];
summarySheet.getRange("E6:E9").formulas = [
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},D6)`],
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},D7)`],
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},D8)`],
  [`=COUNTIF('牛来BOM'!$J$${bomStart}:$J$${bomEnd},D9)`],
];
summarySheet.getRange("G5:H5").values = [["优先级", "条目数"]];
summarySheet.getRange("G6:G9").values = [["P0"], ["P1"], ["升级"], ["排除"]];
summarySheet.getRange("H6:H9").formulas = [
  [`=COUNTIF('牛来BOM'!$B$${bomStart}:$B$${bomEnd},G6)`],
  [`=COUNTIF('牛来BOM'!$B$${bomStart}:$B$${bomEnd},G7)`],
  [`=COUNTIF('牛来BOM'!$B$${bomStart}:$B$${bomEnd},G8)`],
  [`=COUNTIF('牛来BOM'!$B$${bomStart}:$B$${bomEnd},G9)`],
];
for (const range of ["A5:B5", "D5:E5", "G5:H5"]) {
  summarySheet.getRange(range).format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.white, size: 10, name: "Microsoft YaHei" },
    horizontalAlignment: "center",
    borders: { bottom: { style: "medium", color: COLORS.navy } },
  };
}
for (const range of ["A6:B12", "D6:E9", "G6:H9"]) {
  summarySheet.getRange(range).format = {
    font: { color: COLORS.text, size: 10, name: "Microsoft YaHei" },
    borders: { insideHorizontal: { style: "thin", color: COLORS.border }, outside: { style: "thin", color: COLORS.border } },
  };
}
summarySheet.getRange("B6:B11").format.numberFormat = "0";
summarySheet.getRange("B12").format.numberFormat = "¥#,##0.00";
summarySheet.getRange("E6:E9").format.numberFormat = "0";
summarySheet.getRange("H6:H9").format.numberFormat = "0";
summarySheet.getRange("B6:B12").format = { fill: COLORS.paleGreen, font: { bold: true, color: COLORS.navy, size: 12 }, horizontalAlignment: "right" };
summarySheet.getRange("A14:H14").merge();
summarySheet.getRange("A14").values = [["冻结前的四个动作"]];
summarySheet.getRange("A14:H14").format = { fill: COLORS.navy, font: { bold: true, color: COLORS.white, size: 12 }, horizontalAlignment: "left" };
summarySheet.getRange("A15:H18").merge(true);
summarySheet.getRange("A15:A18").values = [
  ["1. G0：逐件拍照并记录型号、接口、电压、尺寸；原图编号只作领取索引。"],
  ["2. G1：用最终重量假负载测试TT马达、驱动、分路电源、急停、停止距离与温升。"],
  ["3. 头部称重后按力臂×2.5动态系数选择180°定位舵机；50号360°舵机不得替代。"],
  ["4. 若进入Sim2Real，再采购编码器或编码电机；策略只输出v/ω，安全层保留最终裁决。"],
];
summarySheet.getRange("A15:H18").format = {
  fill: COLORS.paleBlue,
  font: { color: COLORS.text, size: 10, name: "Microsoft YaHei" },
  wrapText: true,
  verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: COLORS.border }, outside: { style: "thin", color: COLORS.border } },
};
summarySheet.getRange("A15:H18").format.rowHeightPx = 34;
summarySheet.freezePanes.freezeRows(4);
[150, 100, 24, 130, 80, 24, 100, 80].forEach((width, index) => summarySheet.getRangeByIndexes(0, index, 18, 1).format.columnWidthPx = width);

// Compact workbook verification before export.
const summaryInspect = await workbook.inspect({ kind: "table", sheetId: "状态汇总", range: "A5:H18", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10, maxChars: 8000 });
const bomInspect = await workbook.inspect({ kind: "table", sheetId: "牛来BOM", range: `A5:R${bomEnd}`, include: "values,formulas", tableMaxRows: 10, tableMaxCols: 18, maxChars: 12000 });
const errorInspect = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan", maxChars: 6000 });
console.log("SUMMARY_INSPECT");
console.log(summaryInspect.ndjson);
console.log("BOM_INSPECT");
console.log(bomInspect.ndjson);
console.log("FORMULA_ERROR_SCAN");
console.log(errorInspect.ndjson);

const previews = [
  ["牛来BOM", `A1:R${bomEnd}`, "preview-牛来BOM.png"],
  ["比赛物料映射", `A1:H${mapEnd}`, "preview-比赛物料映射.png"],
  ["采购缺口", `A1:M${gapEnd}`, "preview-采购缺口.png"],
  ["状态汇总", "A1:H18", "preview-状态汇总.png"],
];
for (const [sheetName, range, fileName] of previews) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const roundTripBlob = await FileBlob.load(outputPath);
const roundTripWorkbook = await SpreadsheetFile.importXlsx(roundTripBlob);
const roundTripSheets = await roundTripWorkbook.inspect({ kind: "sheet", include: "id,name", maxChars: 4000 });
const roundTripErrors = await roundTripWorkbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "round-trip formula error scan", maxChars: 4000 });
console.log("ROUND_TRIP_SHEETS");
console.log(roundTripSheets.ndjson);
console.log("ROUND_TRIP_ERROR_SCAN");
console.log(roundTripErrors.ndjson);
console.log(JSON.stringify({ outputPath, sheets: ["牛来BOM", "比赛物料映射", "采购缺口", "状态汇总"], bomRows: bomItems.length, mappingRows: mappingRows.length, procurementRows: procurementIndices.length }, null, 2));
