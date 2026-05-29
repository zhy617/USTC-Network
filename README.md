# USTCNetwork

USTC 苏州校区校园网自动认证工具，适配 `http://20.20.20.3` 准入认证系统，支持断线检测、自动重连和 Windows GUI。

## 功能

- 使用苏州校区准入认证接口 `/ac_portal/login.php`
- 按网页 JavaScript 的 RC4 规则生成登录密码字段
- 通过 `/homepage/info.php` 判断登录状态
- 通过外网检测主机判断网络是否可用
- 提供命令行版本和 PySide6 GUI 版本

## 推荐：使用 uv

`uv` 会在项目目录自动维护独立的 `.venv`，并在 `uv run` 时同步依赖后再运行，适合避免系统 Python、全局 pip 和其他项目之间的冲突。

Windows 安装 uv：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装后重新打开 PowerShell，进入仓库目录。命令行版本一键启动：

```powershell
.\run.ps1
```

GUI 版本一键启动：

```powershell
.\run.ps1 -Gui
```

如果只想提前部署环境，不立刻运行：

```powershell
.\setup.ps1
.\setup.ps1 -Gui
.\setup.ps1 -Build
```

也可以不用脚本，直接运行：

```powershell
uv run python UstcNetwork.py ustc-network.conf
uv run --extra gui python UstcNetwork_GUI.py
```

## 备用：使用 pip

如果不使用 uv，也可以手动创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` 只包含命令行版本所需的最小依赖。GUI 和打包依赖体积较大，按需安装：

```powershell
pip install -r requirements-gui.txt
pip install -r requirements-build.txt
```

## 命令行使用

复制或编辑 `ustc-network.conf`，前两行分别填写自己的网络准入账号和密码：

```text
{苏州校区网络准入账号}
{苏州校区网络准入密码}
60
223.5.5.5,1.1.1.1
```

配置说明：

- 第 1 行：账号，通常是苏州校区网络准入账号/手机号
- 第 2 行：密码，填写网页登录时输入的明文密码
- 第 3 行：检测间隔，单位秒，可省略，默认 `60`
- 第 4 行：外网检测主机，可省略，默认 `223.5.5.5,1.1.1.1`

运行：

```bash
python UstcNetwork.py ustc-network.conf
```

## GUI 使用

```bash
python UstcNetwork_GUI.py
```

GUI 中填写：

- 网络准入账号
- 网络准入密码
- 断线重连间隔
- 检测主机 1/2

勾选“保存配置”后会写入当前目录的 `config.ini`。

## systemd

Linux 后台运行可参考 `systemd/ustc-network.service`。把其中的 `{UstcNetwork.py 的绝对路径}` 和 `{ustc-network.conf 的绝对路径}` 替换为真实路径后安装服务。

## 原理

详细抓包记录和协议说明见 `ustcinfo.md`。
