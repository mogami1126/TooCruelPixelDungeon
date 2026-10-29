# 本地稳定性修复包 fix1

日期：2026-10-29。基于 `88f7e621` 工作区的后续修改；只在本地修复和打包，不推送、不合并、不发布。

## 确认并修复的问题

1. 高生命下食物和圣杯回血先做 int 加法再限制到 HT，会溢出成负数。以实际 Pasty/FrozenCarpaccio 赋值及 Chalice.charge 方法复现失败后修复；同时替换天赋、睡眠、若干怪物/召唤物和法杖中的同类“加完再限制”入口。HealthMath 先限制增量再相加，也能安全处理 Long.MAX_VALUE 治疗量。阳春草的 `40 + HT` 改为宽数值计算，避免治疗速率本身溢出。
2. ShieldBuff.incShield 及 Char.shielding 的多层求和会在 int 上限翻为负数。实际方法探针先失败后通过；现在增长和总和饱和到 INT_MAX。英雄受伤统计和传送信标的生命加护盾中间值使用 long，传回 int 接口时显式限制。
3. TurnTime.legacy 把旧存档绝对时间当成单次 delay，错误截断到一百万回合，可能合并不同事件时间。新增两百万/三百万回合旧时间测试先失败后通过；现在独立转换绝对时间，保留停用标记，并对不可表达的范围饱和。

不改变既有命中/闪避必定阈值，也不擅自把高韧性下溢为零改成另一套减伤平衡；这些需要独立机制设计。未重引入不死、直达 Boss 或自动操作测试入口。

## 验证

- `python tools/health_regression.py`：当前 Healing/Hero.updateHT、真实食物回血语句、Chalice.charge、ShieldBuff.incShield、Char.shielding，以及 Long.MAX_VALUE 治疗量通过；引擎依赖使用最小桩。
- `python tools/numeric_regression.py`：含新增长时间旧档转换及顺序测试，通过。
- `python tools/scheduling_interaction_regression.py`：零耗时链、有限退款、保护边界与角色耗时限制通过；极值命中/韧性仅作为既有行为记录。
- `python tools/boss_regression.py`：天狗动画、移动恢复、国王阶段和死亡路径通过。
- 游戏源代码编译与完整 Android 打包由 `.tools/build-android.ps1` 执行，日志 `.research/pr1-fix1-build.log`；最终状态和包身份以同名交付记录为准。

## 包身份与限制

预期版本 `1.0.2-local-fix1`，versionCode `578`，保持包名 `ua.dreamfools.toocruelpixeldungeon.indev` 与既有本地调试证书。候选文件为 `release/TooCruel-1.0.2-local-fix1.apk`，构建成功后核对实际 Manifest、签名和哈希，交付记录为 `release/TooCruel-1.0.2-local-fix1-manifest.json`。

最终构建成功：38 项任务，13 项执行、25 项复用。实际 Manifest 已核实版本与包名；v1/v2 签名通过，证书与原试玩包一致。APK SHA-256：`3a7d9ab4a4c738a75a919d8661fd77a7bddf54c7a4b175487683414048f0869a`。交付目录同时保存运行时代码差异 `TooCruel-1.0.2-local-fix1-source.patch`，源码状态为基线加本地未提交修改。

当前没有连接 Android 设备，未安装、未读写设备存档。离线探针和构建通过不代表正常装备 Boss、实际饮药、全部挑战组合或完整 HP/伤害迁移已经验收。旧包保留，不覆盖历史测试产物。

## 原版图标试玩包

后续按用户要求停用 debug 资源目录（该目录仅包含灰色宝箱启动图标），使本地试玩版使用 main 中原有的大嘴宝箱图标。版本为 `1.0.2-local-fix1-icon`（579），包名和签名不变，游戏逻辑与 fix1 一致。构建成功，打包后的全部 16 个启动图标 PNG 与 main 原资源逐像素一致，v1/v2 签名通过。文件：`release/TooCruel-1.0.2-local-fix1-icon.apk`；交付记录：同目录 `TooCruel-1.0.2-local-fix1-icon-manifest.json`。


## 2026-10-29 后续模拟器验收

以上“未连接设备”为当时的阶段状态。后续已启动模拟器、安装579和580并完成实际操作验收；当前结论与剩余范围见 `emulator-acceptance-20261029.md`。最新试玩包为 `release/TooCruel-1.0.2-local-fix2.apk`，580。
