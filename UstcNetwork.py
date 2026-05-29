#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json

from ustc_suzhou_auth import DEFAULT_CHECK_HOSTS, UstcSuzhouAuthenticator


DEFAULT_CHECK_INTERVAL = 60
DEFAULT_HEARTBEAT_EVERY = 10


class UstcNetwork:
    def __init__(self, config_file):
        self._check_interval = DEFAULT_CHECK_INTERVAL
        username, password, check_interval, check_hosts, heartbeat_every = self._read_config(config_file)
        self._check_interval = check_interval
        self._heartbeat_every = heartbeat_every
        self._authenticator = UstcSuzhouAuthenticator(
            username,
            password,
            check_hosts=check_hosts,
        )
        self._last_status = None
        self._check_count = 0

    @staticmethod
    def _read_config(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            lines = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append(line)

        if len(lines) < 2 or not lines[0] or not lines[1]:
            raise ValueError("config file must contain username and password in the first two lines")

        if lines[0].startswith("{") and lines[0].endswith("}"):
            raise ValueError("username should not include braces; write 133... instead of {133...}")

        check_interval = DEFAULT_CHECK_INTERVAL
        if len(lines) >= 3 and lines[2]:
            check_interval = int(lines[2])

        check_hosts = DEFAULT_CHECK_HOSTS
        if len(lines) >= 4 and lines[3]:
            check_hosts = tuple(part for part in lines[3].replace(",", " ").split() if part)

        heartbeat_every = DEFAULT_HEARTBEAT_EVERY
        if len(lines) >= 5 and lines[4]:
            heartbeat_every = int(lines[4])

        return lines[0], lines[1], check_interval, check_hosts, heartbeat_every

    @staticmethod
    def _log(level, message):
        time_string = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print("[%s] [%s] %s" % (level, time_string, message))

    def _login(self):
        self._log("Log", "network is offline, trying USTC Suzhou portal login")
        ok, message, _ = self._authenticator.login()
        if ok:
            self._last_status = "online"
            self._check_count = 0
            self._log("Log", "authentication succeeded; " + message)
        else:
            self._last_status = "offline"
            self._log("Warn", "authentication failed; " + message)

    def _online(self):
        self._check_count += 1
        if self._last_status != "online":
            self._log("Log", "network is available")
        elif self._heartbeat_every > 0 and self._check_count % self._heartbeat_every == 0:
            self._log("Log", "still online; checks=%s" % self._check_count)
        self._last_status = "online"

    def run(self):
        while True:
            try:
                if self._authenticator.is_online():
                    self._online()
                else:
                    self._login()
                time.sleep(self._check_interval)
            except KeyboardInterrupt:
                self._log("Log", "stopped by user")
                break
            except Exception as exc:
                self._last_status = "error"
                self._log("Exception", str(exc))
                time.sleep(self._check_interval)


def main(argv=None):
    argv = argv or sys.argv
    if len(argv) == 3 and argv[1] == "--debug-login":
        username, password, _, check_hosts, _ = UstcNetwork._read_config(argv[2])
        authenticator = UstcSuzhouAuthenticator(
            username,
            password,
            check_hosts=check_hosts,
        )
        result = authenticator.debug_login()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if len(argv) != 2:
        print("Usage: python UstcNetwork.py ustc-network.conf")
        print("Debug: python UstcNetwork.py --debug-login ustc-network.conf")
        return 2

    network = UstcNetwork(argv[1])
    network.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
