# USTCNetwork

USTC 苏州校区校园网自动认证工具，适配 `http://20.20.20.3` 准入认证系统，支持断线检测、自动重连和 Windows GUI。

## 功能

- 使用苏州校区准入认证接口 `/ac_portal/login.php`
- 按网页 JavaScript 的 RC4 规则生成登录密码字段
- 通过 `/homepage/info.php` 判断登录状态
- 通过外网检测主机判断网络是否可用
- 提供命令行版本和 PySide6 GUI 版本

## 安装依赖

```bash
pip install -r requirements.txt
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
