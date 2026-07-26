# CivModelTool 自动更新功能设计

日期:2026-07-26
状态:已批准

## 目标

为 CivModelTool Blender 插件添加自动更新功能:跟踪 GitHub 仓库 main 分支,
通过对比 `bl_info` 版本号判断新版本,支持启动时自动检查与一键更新,
更新后自动热重载,无需重启 Blender。

## 需求

- 更新来源:GitHub 仓库 `Sumcam-L/CivModelTool` 的 main 分支最新代码
- 版本判断:拉取远程 `__init__.py`,解析 `bl_info["version"]`,与本地对比
- 触发方式:
  - 插件偏好设置(AddonPreferences)中提供"检查更新"和"下载并更新"按钮
  - 启动(register)时自动后台检查
- 启动检查发现新版本时,在 N 面板顶部直接显示"发现新版本 vX.Y.Z"提示和
  **"立即更新"按钮**,用户无需进入偏好设置
- 更新生效方式:自动热重载(disable + enable 插件)
- 发布流程:开发者修改 `bl_info["version"]` 并 push 到 main 即触发用户侧更新

## 架构

新增子包 `cmt_updater`,遵循项目现有子包结构(properties / operations / ui / register):

```
cmt_updater/
    __init__.py      # register/unregister,启动时注册一次性 timer
    core.py          # 纯逻辑:版本检查、下载、解压、覆盖安装(不依赖 UI)
    operations.py    # Operator:检查更新、执行更新(含热重载)
    preferences.py   # CMT_AddonPreferences:按钮、状态显示、启动检查开关
    ui.py            # N 面板顶部的新版本提示 + 立即更新按钮
```

## 组件设计

### core.py(纯逻辑层)

- `fetch_remote_version() -> tuple[int, int, int]`
  - GET `https://raw.githubusercontent.com/Sumcam-L/CivModelTool/main/__init__.py`
  - 正则提取 `"version": (x, y, z)`
- `download_and_install() -> None`
  - 下载 `https://codeload.github.com/Sumcam-L/CivModelTool/zip/refs/heads/main`
    到临时目录
  - 在临时目录完成解压后,才将文件覆盖复制到插件目录
  - **跳过 `.git`、`.gitignore`、`.serena`**,保护本地开发仓库
  - 覆盖后清理插件目录下所有 `__pycache__`
- 全局状态对象(模块级):`state`(idle / checking / update_available /
  updating / up_to_date / error)、`remote_version`、`error_msg`
- 网络请求使用 `urllib`(标准库,无第三方依赖),在 `threading.Thread`
  后台线程执行;线程只写 state,UI 刷新通过 `bpy.app.timers` 回调触发
  `tag_redraw`

### operations.py

- `CMT_OT_CheckUpdate`:启动后台检查线程
- `CMT_OT_RunUpdate`:启动后台下载安装线程;完成后通过 `bpy.app.timers`
  在主线程执行热重载:
  `bpy.ops.preferences.addon_disable` + `bpy.ops.preferences.addon_enable`
  (现有 `cleanup_modules` 已清理 `sys.modules`,可干净重载)

### preferences.py

- `CMT_AddonPreferences(bpy.types.AddonPreferences)`:
  - `auto_check_update: BoolProperty`(默认 True)
  - draw:当前版本 / 远程版本 / 状态文字(检查中、有新版本、已是最新、
    错误信息)、"检查更新"按钮、有新版本时显示"下载并更新"按钮

### ui.py(N 面板提示)

- 在插件现有 N 面板("Civ6ModelTool" 分类)顶部注册一个提示面板:
  - 仅当 `state == update_available` 或 `updating` 或更新出错时显示
  - 内容:"发现新版本 vX.Y.Z" + "立即更新"按钮(调用 `CMT_OT_RunUpdate`)
  - 更新中:按钮禁用,显示"更新中…"
  - 更新失败:显示错误信息,按钮保留可重试
  - 更新成功热重载后,state 重置,面板自动消失

### 启动检查

- `cmt_updater.register()` 中,若偏好设置 `auto_check_update` 为 True,
  注册一次性 `bpy.app.timers`(延迟约 3 秒)触发后台版本检查

## 错误处理

- 网络失败 / 解析失败:state 置为 error,错误信息显示在偏好设置及
  N 面板提示中;不影响插件其余功能
- 下载与解压全部在临时目录完成后才覆盖插件目录,覆盖前不动原文件,
  降低半更新状态风险
- 热重载失败:错误打印到控制台,提示用户重启 Blender

## 测试

- 手动验证:
  - 本地版本号调低 → 启动 Blender → N 面板出现提示 → 点击立即更新 →
    热重载后版本号变新、提示消失
  - 偏好设置中手动检查 / 更新流程
  - 断网时检查更新 → 显示错误,插件功能正常
- 远程版本解析函数可在 Blender 外用纯 Python 验证

## 发布流程(开发者)

1. 修改 `__init__.py` 中 `bl_info["version"]`
2. push 到 main 分支
3. 用户侧下次启动 Blender 时收到更新提示
