# 更新日志

这里归档 CMObsTool 正式发布版本的更新说明，最新版本在前。

此文件根据 GitHub Releases 自动同步。修改版本说明请编辑对应 Release。

<!-- cmobstool-changelog:start -->

## [0.1.29](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.29)

发布日期：2026-11-19 16:13（UTC+8）

- 周期休息新增「出 BOSS 房后按键组」，默认关闭。开启后，确认返回原地图时执行一次；BOSS 房往返测试也支持该设置。
- 修复出 BOSS 房后只补放一个落点技能就开始巡游的问题。进房前执行到一半、且所有成员都有落点的同冷却组，回图后会按新位置整组重新排队，优先于巡游捡物。

---

## [0.1.28](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.28)

发布日期：2026-11-19 15:23（UTC+8）

- 上跳脱困使用小地图总高度的固定 5% 作为两次上跳的累计进展门槛，减少因少量位移反复上跳的情况。
- 连续两轮上跳受阻并完成横向换位后，若目标仍在上方且已配置钩锁键，本次导航会优先尝试一次脱困钩锁。这次尝试占 15 步预算中的 1 步。
- 授权到期提示统一为「超过允许期限」，适用于授权签名有效期和连接中断期限。

---

## [0.1.27](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.27)

发布日期：2026-11-19 14:55（UTC+8）

- 修复部分电脑上 WGC 已收到画面却因捕获项尺寸与实际帧尺寸不同而持续丢帧的问题。实际帧通过物理窗口边界校验后即可使用，帧池过小时会重建并等待完整画面。
- WGC 无法核实画面范围时，故障详情会记录帧池、帧内容、捕获项和纹理尺寸。

---

## [0.1.26](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.26)

发布日期：2026-11-19 11:03（UTC+8）

- 窗口切图或缩放时，WGC 会等待画面尺寸稳定再恢复采集。确认裁剪时也会校验当前画面，避免误用旧坐标。
- PrintWindow 遇到黑帧时继续尝试窗口采集。Boss 入房和回图各有 15 秒确认期限，超时后停止并记录原因。
- 画面坐标变化的停机日志增加前后尺寸、DPI、采集方式和最近故障，方便排查中断。

<!-- cmobstool-changelog:end -->
