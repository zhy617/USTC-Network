#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time

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

    def _headers(self, referer=HOME_URL):
        headers = {
            "Accept": "*/*",
            "Origin": PORTAL_ORIGIN,
            "Referer": referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 "
                "Safari/537.36 Edg/148.0.0.0"
            ),
            "X-Requested-With": "XMLHttpRequest",
        }
        if self.auth_session_id:
            headers["Cookie"] = "AUTHSESSID=" + self.auth_session_id
        return headers

    def _remember_cookie(self, response):
        auth_session_id = response.cookies.get("AUTHSESSID")
        if auth_session_id:
            self.auth_session_id = auth_session_id

    def login(self):
        if not self.username:
            raise ValueError("username cannot be empty")
        if not self.password:
            raise ValueError("password cannot be empty")

        auth_tag = str(int(time.time() * 1000))
        data = {
            "opr": "pwdLogin",
            "userName": self.username,
            "pwd": encrypt_rc4(self.password, auth_tag),
            "auth_tag": auth_tag,
            "rememberPwd": "0",
        }

        response = self.session.post(
            LOGIN_URL,
            data=data,
            headers=self._headers(LOGIN_REFERER),
            timeout=self.timeout,
        )
        self._remember_cookie(response)

        info = self.get_info()
        if info and info.get("success"):
            return True, self.describe_info(info), info

        return False, self._failure_message(response, info), info

    def get_info(self):
        response = self.session.post(
            INFO_URL,
            data={"opr": "list"},
            headers=self._headers(HOME_URL),
            timeout=self.timeout,
        )
        self._remember_cookie(response)
        try:
            return response.json()
        except ValueError:
            return None

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
    def _failure_message(response, info):
        if info:
            msg = info.get("msg") or info.get("message")
            location = info.get("location")
            if msg and location:
                return "%s; redirect: %s" % (msg, location)
            if msg:
                return str(msg)
            if location:
                return "redirect: " + str(location)

        text = (response.text or "").strip()
        if text:
            return text[:200]
        return "login request sent, but status check did not confirm success"
