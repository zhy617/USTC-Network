#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import os
import shutil
import stat
import sys
import time

from PySide6 import QtCore, QtGui, QtWidgets

import rc_icon
from ustc_suzhou_auth import DEFAULT_CHECK_HOSTS, UstcSuzhouAuthenticator


CONFIG_FILE = "config.ini"
APP_NAME = "USTC 苏州校区校园网认证服务"


def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class UstcNetworkWorker(QtCore.QThread):
    status_signal = QtCore.Signal(str)

    def __init__(self, username, password, ping_interval, ping_host1, ping_host2):
        super().__init__()
        self._username = username
        self._password = password
        self._ping_interval = ping_interval
        self._ping_hosts = [host for host in (ping_host1, ping_host2) if host]
        self._stopped = False

    def stop(self):
        self._stopped = True

    def _sleep_interval(self):
        for _ in range(max(1, self._ping_interval)):
            if self._stopped:
                return
            self.msleep(1000)

    def run(self):
        authenticator = UstcSuzhouAuthenticator(
            self._username,
            self._password,
            check_hosts=self._ping_hosts or DEFAULT_CHECK_HOSTS,
        )

        while not self._stopped:
            try:
                if authenticator.is_online():
                    self.status_signal.emit("已认证，网络可用")
                else:
                    self.status_signal.emit("未认证，正在登录...")
                    ok, message, _ = authenticator.login()
                    if ok:
                        self.status_signal.emit("认证成功")
                    else:
                        self.status_signal.emit("认证失败：" + message)
            except Exception as exc:
                self.status_signal.emit("连接失败：" + str(exc))

            self._sleep_interval()


class UstcNetworkGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.tray_icon = None
        self.tray_msg = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(":/icon/network.png"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )

        self.config = configparser.ConfigParser()
        self._create_widgets()
        self._load_config()
        self._cleanup_pyinstaller_dirs()

        if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            self._create_tray_icon()
            self.tray_icon.show()

    def _create_widgets(self):
        self.layout = QtWidgets.QFormLayout(self)

        self.username = QtWidgets.QLineEdit()
        self.layout.addRow("网络准入账号", self.username)

        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.layout.addRow("网络准入密码", self.password)

        self.ping_interval = QtWidgets.QLineEdit("15")
        self.layout.addRow("断线重连间隔(s)", self.ping_interval)

        self.ping_host1 = QtWidgets.QLineEdit(DEFAULT_CHECK_HOSTS[0])
        self.layout.addRow("检测主机1", self.ping_host1)

        self.ping_host2 = QtWidgets.QLineEdit(DEFAULT_CHECK_HOSTS[1])
        self.layout.addRow("检测主机2", self.ping_host2)

        self.status = QtWidgets.QLabel("未运行")
        self.layout.addRow("当前状态", self.status)

        self.save_config = QtWidgets.QCheckBox("保存配置")
        self.save_config.setChecked(True)
        self.silent_start = QtWidgets.QCheckBox("静默启动")
        self.silent_start.setChecked(False)
        self.button = QtWidgets.QPushButton("开启服务")
        self.layout.addRow(self.save_config, self.silent_start)
        self.layout.addRow(self.button)

        self.button.clicked.connect(self.daemon_toggle)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE, encoding="utf-8")
        else:
            self.config["network"] = {}
            self.config["normal"] = {}

        network = self.config["network"] if self.config.has_section("network") else {}
        normal = self.config["normal"] if self.config.has_section("normal") else {}

        self.username.setText(network.get("username", ""))
        self.password.setText(network.get("password", ""))
        self.ping_interval.setText(network.get("ping_interval", "15"))
        self.ping_host1.setText(network.get("ping_host1", network.get("ping_dns1", DEFAULT_CHECK_HOSTS[0])))
        self.ping_host2.setText(network.get("ping_host2", network.get("ping_dns2", DEFAULT_CHECK_HOSTS[1])))
        self.silent_start.setChecked(str(normal.get("silent_start", "False")).lower() == "true")

        self._write_config_if_needed()

    def _write_config_if_needed(self):
        if not self.config.has_section("network"):
            self.config.add_section("network")
        if not self.config.has_section("normal"):
            self.config.add_section("normal")

        self.config["network"] = {
            "username": self.username.text(),
            "password": self.password.text(),
            "ping_interval": self.ping_interval.text(),
            "ping_host1": self.ping_host1.text(),
            "ping_host2": self.ping_host2.text(),
        }
        self.config["normal"] = {"silent_start": str(self.silent_start.isChecked())}

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            self.config.write(f)

    def _cleanup_pyinstaller_dirs(self):
        cur_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        mei_dirs = {}
        max_ctime = 0
        for file_name in os.listdir(cur_dir):
            if "_MEI" not in file_name:
                continue
            mei_dir = os.path.join(cur_dir, file_name)
            if os.path.isdir(mei_dir):
                cur_ctime = os.path.getctime(mei_dir)
                mei_dirs[cur_ctime] = mei_dir
                max_ctime = max(max_ctime, cur_ctime)

        for ctime, mei_dir in mei_dirs.items():
            if ctime != max_ctime:
                shutil.rmtree(mei_dir, onerror=remove_readonly)

    def _create_tray_icon(self):
        show_action = QtGui.QAction("显示", self)
        show_action.triggered.connect(self.showNormal)

        quit_action = QtGui.QAction("退出", self)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)

        tray_icon_menu = QtWidgets.QMenu(self)
        tray_icon_menu.addAction(show_action)
        tray_icon_menu.addSeparator()
        tray_icon_menu.addAction(quit_action)

        self.tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(":/icon/network.png"), self)
        self.tray_icon.setContextMenu(tray_icon_menu)
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.activated.connect(self._tray_icon_activated)

    def _tray_icon_activated(self, reason):
        if reason in (
            QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick,
            QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.showNormal()

    def closeEvent(self, event):
        if (
            event.spontaneous()
            and self.worker
            and self.tray_icon
            and self.tray_icon.isVisible()
        ):
            self.hide()
            self.tray_info("隐藏至系统托盘")
            event.ignore()
            return
        super().closeEvent(event)

    def changeEvent(self, event):
        if self.worker and self.windowState() == QtCore.Qt.WindowState.WindowMinimized:
            self.hide()
            self.tray_info("隐藏至系统托盘")
        super().changeEvent(event)

    @QtCore.Slot(str)
    def set_status(self, message):
        self.status.setText(message)

    @QtCore.Slot(str)
    def tray_info(self, message):
        if self.tray_icon and self.tray_msg != message:
            self.tray_msg = message
            self.tray_icon.showMessage(APP_NAME, message)

    def _save_config(self):
        if self.save_config.isChecked():
            self._write_config_if_needed()

    def _start_auth_daemon(self):
        try:
            ping_interval = int(self.ping_interval.text())
        except ValueError:
            self.set_status("断线重连间隔必须是整数")
            return False

        self.worker = UstcNetworkWorker(
            self.username.text(),
            self.password.text(),
            ping_interval,
            self.ping_host1.text().strip(),
            self.ping_host2.text().strip(),
        )
        self.worker.status_signal.connect(self.set_status)
        self.worker.status_signal.connect(self.tray_info)
        self.worker.start()
        return True

    @QtCore.Slot()
    def daemon_toggle(self):
        if self.worker is None:
            self._save_config()
            self.set_status("认证中...")
            if self._start_auth_daemon():
                self.button.setText("停止服务")
        else:
            self.worker.stop()
            self.worker.wait(3000)
            self.worker = None
            self.set_status("未运行")
            self.button.setText("开启服务")


def main():
    app = QtWidgets.QApplication([])

    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        QtWidgets.QMessageBox.critical(
            None,
            APP_NAME,
            "该系统上不支持隐藏至系统托盘\n如需断线重连功能，认证完成后请勿关闭本程序",
        )

    widget = UstcNetworkGUI()
    widget.resize(280, 220)
    if widget.silent_start.isChecked():
        widget.hide()
        widget.daemon_toggle()
    else:
        widget.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
