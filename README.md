# USTCNetwork

USTC 苏州校区校园网自动认证工具，适配 `http://20.20.20.3` 准入认证系统，支持断线检测和自动重连。主要面向树莓派、Linux 服务器和软路由等常驻设备。

## 功能

- 使用苏州校区准入认证接口 `/ac_portal/login.php`
- 按网页 JavaScript 的 RC4 规则生成登录密码字段
- 通过 `/homepage/info.php` 判断登录状态
- 通过外网检测主机判断网络是否可用
- 支持 uv 隔离环境、前台调试和 systemd 后台运行

## Linux / 树莓派快速部署

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

重新打开 shell，或执行安装脚本提示的 `source` 命令让 `uv` 生效。然后进入仓库：

```bash
cd /path/to/USTC-Network
```

创建本机私密配置：

```bash
cp ustc-network.example.conf ustc-network.local.conf
nano ustc-network.local.conf
```

前台调试登录：

```bash
chmod +x run.sh
./run.sh --debug
```

正常前台运行：

```bash
./run.sh
```

`run.sh` 会优先读取 `ustc-network.local.conf`；如果不存在，才读取 `ustc-network.conf`。

## 配置文件

推荐把真实账号密码写到 `ustc-network.local.conf`，它已被 `.gitignore` 忽略，不会被提交：

```text
# 第 1 行有效配置：网络准入账号，通常是手机号。不要加 {}。
13300000000

# 第 2 行有效配置：网页登录时输入的明文密码。
your_plaintext_password

# 第 3 行有效配置：检测间隔，单位秒。
60

# 第 4 行有效配置：外网检测主机。
223.5.5.5,1.1.1.1

# 第 5 行有效配置：心跳日志间隔。
10
```

配置说明：

- 第 1 行：账号，通常是苏州校区网络准入账号/手机号
- 第 2 行：密码，填写网页登录时输入的明文密码，不是抓包里的加密 `pwd`
- 第 3 行：检测间隔，单位秒，可省略，默认 `60`
- 第 4 行：外网检测主机，可省略，默认 `223.5.5.5,1.1.1.1`
- 第 5 行：心跳日志间隔，可省略，默认 `10`；表示每 10 次检测输出一次 `still online`，设为 `1` 表示每次检测都输出，设为 `0` 表示只在状态变化时输出
- 空行和以 `#` 开头的整行注释会被忽略

注意：账号和密码不要加 `{}`。如果写成 `{13300000000}`，大括号会被当成账号的一部分提交，认证系统会返回“用户名或密码错误”。

## systemd 后台运行

确认 `uv` 的绝对路径：

```bash
command -v uv
```

假设仓库在 `/home/pi/USTC-Network`，`uv` 在 `/home/pi/.local/bin/uv`，可以创建服务文件：

```bash
sudo nano /etc/systemd/system/ustc-network.service
```

内容示例：

```ini
[Unit]
Description=USTC Suzhou Network Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/USTC-Network
Restart=on-failure
RestartSec=5s
ExecStart=/home/pi/.local/bin/uv run python UstcNetwork.py /home/pi/USTC-Network/ustc-network.local.conf
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ustc-network.service
```

查看日志：

```bash
journalctl -u ustc-network.service -f
```

停止或重启：

```bash
sudo systemctl stop ustc-network.service
sudo systemctl restart ustc-network.service
```

仓库里也提供了模板：`systemd/ustc-network.service`。

## Windows 调试

Windows 不是主要部署目标，但可以用于抓包和调试。

安装 uv：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

前台运行：

```powershell
.\run.ps1
.\run.ps1 -Debug
```

## pip 备用方案

如果不使用 uv，也可以手动创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python UstcNetwork.py ustc-network.local.conf
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python UstcNetwork.py ustc-network.local.conf
```

## GUI

仓库仍保留 PySide6 GUI，主要用于 Windows 临时调试：

```bash
uv run --extra gui python UstcNetwork_GUI.py
```

GUI 中勾选“保存配置”后会写入当前目录的 `config.ini`，该文件已被 `.gitignore` 忽略。

## 原理

详细抓包记录和协议说明见 `ustcinfo.md`。
