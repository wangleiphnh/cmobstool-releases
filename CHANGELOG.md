# 更新日志

这里归档 CMObsTool 正式发布版本的更新说明，最新版本在前。

此文件根据 GitHub Releases 自动同步。修改版本说明请编辑对应 Release。

<!-- cmobstool-changelog:start -->

## [0.1.3](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.3)

发布日期：2026-11-12 18:48（UTC+8）

更新下载优化

- 新增自动测速，在 GitHub 和多个镜像中优先选择响应更快的可用下载源。
- 下载卡住、持续低速或失败时，自动切换其他可用源重试。
- 更新窗口显示当前下载源、测速用时和实时下载速度，测速与下载均可取消。
- 优化检查更新的网络回退，减少 GitHub 直连不可用时的等待。
- 保留更新包签名与版本校验，验证通过后才会停止任务并安装。

提示：安装 0.1.3 后，自动测速和换源功能将在后续更新中生效。从旧版本升级本次更新时，仍使用旧版下载方式；若下载较慢，也可从发布页下载安装包。

---

## [0.1.2](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.2)

发布日期：2026-11-12 18:06（UTC+8）

测试更新

---

## [0.1.1](https://github.com/wangleiphnh/cmobstool-releases/releases/tag/v0.1.1)

发布日期：2026-11-12 16:01（UTC+8）

首次提供支持签名自动更新的 Windows x64 安装包。

- 支持软件内检查更新、查看版本说明、下载和取消下载。
- 安装前停止任务并检查按键清理；其他实例未退出时阻止安装。
- 包含主程序、采集辅助程序、x86 易键鼠桥接及识别资源。

真实游戏、设备联调和 Windows 安装升级效果待用户整体验证。

<!-- cmobstool-changelog:end -->
