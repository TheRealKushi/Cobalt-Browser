# updater.py
import json, os, sys, hashlib, tempfile
from PyQt5.QtCore import QObject, QUrl, QCoreApplication, QStandardPaths, QFileInfo
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import QProcess

def _ver_tuple(v):
    # simple 1.2.3 → (1,2,3) compare
    return tuple(int(p) for p in v.strip().split("."))

class Updater(QObject):
    """
    Checks updates.json, downloads the new installer, verifies SHA256 (optional),
    launches it silently, then quits the app.
    """
    def __init__(self, parent, current_version, feed_url,
                 installer_args=None, app_name="App"):
        super().__init__(parent)
        self.current_version = current_version
        self.feed_url = feed_url
        self.nam = QNetworkAccessManager(self)
        self.installer_args = installer_args or [
            "/VERYSILENT", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"
        ]
        self.app_name = app_name

    def check(self, silent=True):
        req = QNetworkRequest(QUrl(self.feed_url))
        reply = self.nam.get(req)
        reply.finished.connect(lambda r=reply, s=silent: self._on_feed(r, s))

    def _on_feed(self, reply, silent):
        if reply.error():
            if not silent:
                QMessageBox.warning(self.parent(), "Update",
                                    f"Failed to check for updates:\n{reply.errorString()}")
            reply.deleteLater()
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            latest = data["version"].strip()
            url = data["url"].strip()
            sha256 = (data.get("sha256") or "").lower() or None
        except Exception as e:
            if not silent:
                QMessageBox.warning(self.parent(), "Update", f"Bad update feed.\n{e}")
            reply.deleteLater()
            return
        reply.deleteLater()

        if _ver_tuple(latest) <= _ver_tuple(self.current_version):
            if not silent:
                QMessageBox.information(self.parent(), "Update",
                                        f"You are up to date ({self.current_version}).")
            return

        # Ask user
        res = QMessageBox.question(
            self.parent(), f"{self.app_name} Update Available",
            f"A new version {latest} is available (you have {self.current_version}).\n\n"
            f"Download and install now?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if res == QMessageBox.Yes:
            self._download(url, sha256)

    def _download(self, url, sha256):
        req = QNetworkRequest(QUrl(url))
        reply = self.nam.get(req)

        downloads_dir = (QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
                         or tempfile.gettempdir())
        filename = QFileInfo(QUrl(url).path()).fileName() or "update.exe"
        self.dest_path = os.path.join(downloads_dir, filename)

        self._file = open(self.dest_path, "wb")

        self.dlg = QProgressDialog("Downloading update...", "Cancel", 0, 100, self.parent())
        self.dlg.setWindowTitle(f"{self.app_name} Updater")
        self.dlg.setMinimumDuration(0)
        self.dlg.setAutoClose(False)
        self.dlg.setAutoReset(False)
        self.dlg.canceled.connect(lambda: reply.abort())

        reply.downloadProgress.connect(self._on_progress)
        reply.readyRead.connect(lambda: self._file.write(bytes(reply.readAll())))
        reply.finished.connect(lambda: self._on_download_finished(reply, sha256))

    def _on_progress(self, recvd, total):
        if total > 0:
            self.dlg.setValue(int(recvd * 100 / total))

    def _on_download_finished(self, reply, sha256):
        err = reply.error()
        reply.deleteLater()
        self._file.close()
        self.dlg.close()

        if err:
            QMessageBox.warning(self.parent(), "Update",
                                f"Download failed:\n{reply.errorString()}")
            try: os.remove(self.dest_path)
            except: pass
            return

        if sha256:
            h = hashlib.sha256()
            with open(self.dest_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest().lower() != sha256:
                QMessageBox.critical(self.parent(), "Update", "Checksum mismatch. Aborting.")
                try: os.remove(self.dest_path)
                except: pass
                return

        ok = QProcess.startDetached(self.dest_path, self.installer_args)
        if not ok:
            QMessageBox.critical(self.parent(), "Update", "Failed to launch installer.")
            return
        QCoreApplication.quit()
