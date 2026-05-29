#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
import sys
import time
from urllib.parse import urljoin

import requests


PORTAL_HOST = "20.20.20.3"
PORTAL_ORIGIN = "http://20.20.20.3"
LOGIN_URL = PORTAL_ORIGIN + "/ac_portal/login.php"
INFO_URL = PORTAL_ORIGIN + "/homepage/info.php"
HOME_URL = PORTAL_ORIGIN + "/homepage/index.html?_FLAG=1"
LOGOUT_URL = PORTAL_ORIGIN + "/homepage/logout"
LOGIN_REFERER = (
    PORTAL_ORIGIN
    + "/ac_portal/disclaimer_antileak/pc.html?"
    + "template=disclaimer_antileak&tabs=pwd-sms&dual_stack=0"
    + "&vlanid=0&_ID_=0&switch_url="
    + "&url=http://20.20.20.3/homepage/index.html&controller_type="
)

DEFAULT_CHECK_HOSTS = ("223.5.5.5", "1.1.1.1")
DEFAULT_TIMEOUT = 5


def encrypt_rc4(src, passwd):
    """Match the portal's do_encrypt_rc4(src, auth_tag) JavaScript."""
    src = str(src).strip()
    passwd = str(passwd)
    if not passwd:
        raise ValueError("RC4 key cannot be empty")

    key = [ord(passwd[i % len(passwd)]) for i in range(256)]
    sbox = list(range(256))

    j = 0
    for i in range(256):
        j = (j + sbox[i] + key[i]) % 256
        sbox[i], sbox[j] = sbox[j], sbox[i]

    a = 0
    b = 0
    output = []
    for ch in src:
        a = (a + 1) % 256
        b = (b + sbox[a]) % 256
        sbox[a], sbox[b] = sbox[b], sbox[a]
        c = (sbox[a] + sbox[b]) % 256
        output.append(f"{ord(ch) ^ sbox[c]:02x}")

    return "".join(output)


class UstcSuzhouAuthenticator:
    def __init__(self, username, password, check_hosts=None, timeout=DEFAULT_TIMEOUT):
        self.username = str(username).strip()
        self.password = str(password).strip()
        self.check_hosts = tuple(check_hosts or DEFAULT_CHECK_HOSTS)
        self.timeout = timeout
        self.auth_session_id = None

        self.session = requests.Session()
        self.session.trust_env = False

    def _headers(self, referer=HOME_URL, xhr=True):
        headers = {
            "Accept": "*/*" if xhr else "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 "
                "Safari/537.36 Edg/148.0.0.0"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if referer:
            headers["Referer"] = referer
        if xhr:
            headers["Origin"] = PORTAL_ORIGIN
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["X-Requested-With"] = "XMLHttpRequest"
        if self.auth_session_id:
            headers["Cookie"] = "AUTHSESSID=" + self.auth_session_id
        return headers

    def _remember_cookie(self, response):
        auth_session_id = response.cookies.get("AUTHSESSID")
        if auth_session_id:
            self.auth_session_id = auth_session_id

    def _prepare_login(self):
        referer = self._visit_and_find_login_page(HOME_URL)
        if not referer:
            referer = self._visit_and_find_login_page(PORTAL_ORIGIN + "/")

        referer = referer or LOGIN_REFERER
        self._visit_page(referer)
        return referer

    def _visit_page(self, url, referer=PORTAL_ORIGIN + "/"):
        response = self.session.get(
            url,
            headers=self._headers(referer, xhr=False),
            timeout=self.timeout,
            allow_redirects=True,
        )
        self._remember_cookie(response)
        return response

    def _visit_and_find_login_page(self, url):
        response = self._visit_page(url)
        return self._extract_login_page(response)

    @staticmethod
    def _extract_login_page(response):
        candidates = []
        if response.url:
            candidates.append(response.url)

        text = response.text or ""
        patterns = (
            r"""['"]([^'"]*/ac_portal/[^'"]+)['"]""",
            r"""(?:href|src)\s*=\s*['"]([^'"]+)['"]""",
            r"""location(?:\.href)?\s*=\s*['"]([^'"]+)['"]""",
        )
        for pattern in patterns:
            candidates.extend(re.findall(pattern, text, flags=re.IGNORECASE))

        preferred = []
        fallback = []
        for candidate in candidates:
            full_url = urljoin(PORTAL_ORIGIN + "/", candidate)
            if "/ac_portal/" not in full_url or full_url.endswith("/login.php"):
                continue
            if "disclaimer_antileak" in full_url or "pc.html" in full_url:
                preferred.append(full_url)
            elif "needauth" not in full_url:
                fallback.append(full_url)

        if preferred:
            return preferred[0]
        if fallback:
            return fallback[0]
        return None

    def login(self):
        if not self.username:
            raise ValueError("username cannot be empty")
        if not self.password:
            raise ValueError("password cannot be empty")

        login_referer = self._prepare_login()
        auth_tag = str(int(time.time() * 1000))
        encrypted_password = encrypt_rc4(self.password, auth_tag)
        data = {
            "opr": "pwdLogin",
            "userName": self.username,
            "pwd": encrypted_password,
            "auth_tag": auth_tag,
            "rememberPwd": "0",
        }

        response = self.session.post(
            LOGIN_URL,
            data=data,
            headers=self._headers(login_referer),
            timeout=self.timeout,
        )
        self._remember_cookie(response)
        login_result = self._response_json(response)

        info = self.get_info()
        if info and info.get("success"):
            return True, self.describe_info(info), info

        return False, self._failure_message(response, info, login_result), info

    def debug_login(self):
        login_referer = self._prepare_login()
        auth_tag = str(int(time.time() * 1000))
        encrypted_password = encrypt_rc4(self.password, auth_tag)
        data = {
            "opr": "pwdLogin",
            "userName": self.username,
            "pwd": encrypted_password,
            "auth_tag": auth_tag,
            "rememberPwd": "0",
        }

        response = self.session.post(
            LOGIN_URL,
            data=data,
            headers=self._headers(login_referer),
            timeout=self.timeout,
        )
        self._remember_cookie(response)
        login_result = self._response_json(response)
        info = self.get_info()

        return {
            "login_referer": login_referer,
            "login_status_code": response.status_code,
            "login_content_type": response.headers.get("Content-Type", ""),
            "login_json": login_result,
            "login_text": self._response_text(response)[:500],
            "has_auth_session_cookie": bool(self.auth_session_id),
            "auth_tag_len": len(auth_tag),
            "encrypted_password_len": len(encrypted_password),
            "info_json": info,
        }

    def get_info(self):
        response = self.session.post(
            INFO_URL,
            data={"opr": "list"},
            headers=self._headers(HOME_URL),
            timeout=self.timeout,
        )
        self._remember_cookie(response)
        return self._response_json(response)

    def logout(self):
        response = self.session.get(
            LOGOUT_URL,
            headers=self._headers(HOME_URL),
            timeout=self.timeout,
        )
        self._remember_cookie(response)
        try:
            data = response.json()
        except ValueError:
            data = None
        return response.status_code == 200, data

    def is_session_online(self):
        info = self.get_info()
        return bool(info and info.get("success"))

    def has_external_connectivity(self):
        return any(self.ping(host) for host in self.check_hosts)

    def is_online(self):
        return self.is_session_online() or self.has_external_connectivity()

    @staticmethod
    def ping(host):
        if sys.platform.lower() == "win32":
            args = ["ping", "-n", "2", "-w", "1000", host]
            creation_flags = subprocess.CREATE_NO_WINDOW
        else:
            args = ["ping", "-c", "2", "-W", "1", host]
            creation_flags = 0

        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        return process.wait() == 0

    @staticmethod
    def describe_info(info):
        data = info.get("data") or {}
        basic = data.get("basic") or {}
        name = basic.get("name") or "unknown"
        group = basic.get("group") or ""
        online_time = data.get("onlinetime")

        details = [name]
        if group:
            details.append(group)
        if online_time is not None:
            details.append("online %s min" % online_time)
        return "logged in: " + ", ".join(details)

    @staticmethod
    def _response_text(response):
        content = response.content or b""
        for encoding in ("utf-8", "gbk", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                pass

        response.encoding = response.apparent_encoding or response.encoding
        return response.text or ""

    @staticmethod
    def _response_json(response):
        text = UstcSuzhouAuthenticator._response_text(response).strip()
        if text:
            try:
                return json.loads(text)
            except ValueError:
                pass

        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _failure_message(response, info, login_result=None):
        parts = []
        if login_result:
            msg = login_result.get("msg") or login_result.get("message")
            location = login_result.get("location")
            success = login_result.get("success")
            if msg:
                parts.append("login.php: " + str(msg))
            elif success is not None:
                parts.append("login.php success=%s" % success)
            if location:
                parts.append("login redirect: " + str(location))

        if info:
            msg = info.get("msg") or info.get("message")
            location = info.get("location")
            if msg:
                parts.append("info.php: " + str(msg))
            if location:
                parts.append("info redirect: " + str(location))
            if parts:
                return "; ".join(parts)

        text = (response.text or "").strip()
        if text:
            parts.append("login response: " + text[:200])
        if parts:
            return "; ".join(parts)
        return "login request sent, but status check did not confirm success"
