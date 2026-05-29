# USTC 苏州校区网络准入认证原理

本文记录本仓库适配 USTC 苏州校区校园网认证系统时使用到的网页接口和脚本逻辑。

## 入口页面

连接苏州校区校园网后，访问 `http://20.20.20.3` 会自动跳转到登录界面。登录成功后的主页是：

```text
http://20.20.20.3/homepage/index.html?_FLAG=1
```

一次抓包中观察到的登录页形态如下，末尾的 `mac` 会随终端变化：

```text
http://20.20.20.3/ac_portal/disclaimer_antileak/pc.html?template=disclaimer_antileak&tabs=pwd-sms&dual_stack=0&vlanid=0&_ID_=0&switch_url=&url=http://20.20.20.3/homepage/index.html&controller_type=&mac=<CLIENT_MAC>
```

## 登录接口

网页登录时真正提交账号密码的是：

```text
POST http://20.20.20.3/ac_portal/login.php
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Origin: http://20.20.20.3
```

表单字段：

```text
opr=pwdLogin
userName=<网络准入账号>
pwd=<加密后的密码>
auth_tag=<当前毫秒时间戳>
rememberPwd=0
```

其中 `auth_tag` 是 JavaScript 中 `+(new Date()) + ''` 的结果，也就是当前 Unix 毫秒时间戳字符串。

## 密码字段

登录表单里的 `pwd` 不是明文密码，而是网页函数 `do_encrypt_rc4(明文密码, auth_tag)` 的结果。网页 JS 逻辑等价于：

```javascript
function do_encrypt_rc4(src, passwd) {
    src = $.trim(src + '');
    passwd = passwd + '';
    var i, j = 0, a = 0, b = 0, c = 0, temp;
    var plen = passwd.length;
    var size = src.length;
    var key = Array(256);
    var sbox = Array(256);
    var output = Array(size);

    for (i = 0; i < 256; i++) {
        key[i] = passwd.charCodeAt(i % plen);
        sbox[i] = i;
    }
    for (i = 0; i < 256; i++) {
        j = (j + sbox[i] + key[i]) % 256;
        temp = sbox[i];
        sbox[i] = sbox[j];
        sbox[j] = temp;
    }
    for (i = 0; i < size; i++) {
        a = (a + 1) % 256;
        b = (b + sbox[a]) % 256;
        temp = sbox[a];
        sbox[a] = sbox[b];
        sbox[b] = temp;
        c = (sbox[a] + sbox[b]) % 256;
        temp = src.charCodeAt(i) ^ sbox[c];
        temp = temp.toString(16);
        if (temp.length === 1) {
            temp = '0' + temp;
        } else if (temp.length === 0) {
            temp = '00';
        }
        output[i] = temp;
    }
    return output.join('');
}
```

本仓库在 `ustc_suzhou_auth.py` 中用 Python 复刻了这个 RC4-hex 过程。每次登录都重新生成 `auth_tag`，并用它作为 RC4 key。

## 登录状态接口

登录后管理页面会请求：

```text
POST http://20.20.20.3/homepage/info.php
Content-Type: application/x-www-form-urlencoded; charset=UTF-8

opr=list
```

成功响应结构类似：

```json
{
  "success": true,
  "data": {
    "basic": {
      "name": "<账号>",
      "showname": "<姓名>",
      "group": "学生组",
      "allowLogout": true
    },
    "bind": {
      "count": 3,
      "data": {}
    },
    "onlinetime": 1
  }
}
```

因此脚本使用 `success == true` 作为认证成功或当前会话在线的判断依据。

## 注销接口

管理页面中的注销按钮对应：

```text
GET http://20.20.20.3/homepage/logout
```

当前脚本主要用于自动登录和断线重连，注销接口保留在共享认证模块中，便于后续扩展。

## 断线检测

`20.20.20.3` 是准入认证网关，未登录时也能访问，所以不能用它判断是否已经连通互联网。本仓库默认检测外网主机：

```text
223.5.5.5
1.1.1.1
```

脚本的判断顺序是：

1. 请求 `/homepage/info.php`，如果返回 `success: true`，认为已认证。
2. 如果状态接口不可用，则 ping 外网检测主机，任一成功则认为网络可用。
3. 如果都失败，则发起 `/ac_portal/login.php` 登录。

## 抓包方法

后续如果学校升级认证系统，可以按以下方式重新确认参数：

1. 打开浏览器开发者工具，进入 Network。
2. 勾选 Preserve log 和 Disable cache。
3. 访问 `http://20.20.20.3`，输入账号密码登录。
4. 找到 `login.php` 请求，记录 Request URL、Method、Payload 和 Headers。
5. 搜索登录页 JS 中的 `pwdLogin`、`auth_tag`、`rememberPwd`、`do_encrypt_rc4`。
6. 登录后找到 `info.php` 请求，确认成功响应字段。

贴出抓包信息时应打码账号、密码、Cookie、手机号、姓名、MAC 和内网 IP。
