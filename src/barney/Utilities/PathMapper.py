from __future__ import annotations

import logging
import os
import re
from pathlib import Path, PosixPath
from platform import system
from typing import TYPE_CHECKING

from qtpy.QtCore import QDir, QObject, QStorageInfo, QUrl
from qtpy.QtNetwork import QHostInfo

if TYPE_CHECKING:
    from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PathMapper(QObject):
    """This class handles the mapping of local to network paths, as well as sanitizing paths as need-be

    Parameters
    ----------
    QObject : QObject
        Operational parent to set PathMapper widget to.
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # network mapping
        self.storageInfo = QStorageInfo()
        self.localToNetworkPath: Dict[Path, Path] = {}
        self.networkToLocalPath: Dict[Path, Path] = {}
        logger.info(
            "Generating network path mapping, if this does not finish, there is a bad mount."
        )
        self._generateMapping()
        logger.info("Network path mapping complete.")

    def refreshMapping(self) -> None:
        self.storageInfo.refresh()
        self._generateMapping()

    def _generateMapping(self) -> None:
        """This method determines the mapping between local and network paths,
        and vice versa.  Great care should be taken when modifying this method
        """
        hostOS = system()
        volumes = self.storageInfo.mountedVolumes()
        self.localToNetworkPath.clear()
        self.networkToLocalPath.clear()
        for volume in volumes:
            # skip volume if it's the main
            if volume.isRoot():
                continue
            if str(volume.device(), encoding="utf-8").startswith(r"/dev/sd"):
                # not interested in local storage devices
                continue
            elif (
                re.match(
                    r"^\\\\[a-z]\\.*",
                    str(volume.device(), encoding="utf-8"),
                    flags=re.IGNORECASE,
                )
                is not None
            ):
                # local path on windows
                continue

            # danger will robinson
            # seriously, be very careful with this bit of code
            # should probably refactor to a separate function that I can test better

            localPath = Path(volume.rootPath())

            if hostOS == "Windows":
                remoteQUrl = QUrl(
                    QUrl.fromLocalFile(volume.device().data().decode("utf-8"))
                )
            else:
                remoteQUrl = QUrl(QUrl.fromPercentEncoding(volume.device().data()))

            # handle the case where machines are mounted by ip address
            remoteHost = QHostInfo.fromName(remoteQUrl.host()).hostName()
            # handle case of dat.sensory.local -> dat
            remoteQUrl.setHost(remoteHost.partition(".")[0])

            if hostOS == "Windows":
                remotePath = Path(
                    remoteQUrl.toDisplayString(
                        QUrl.FormattingOptions(
                            QUrl.RemoveUserInfo | QUrl.PreferLocalFile
                        )
                    )
                )
            else:
                remotePath = Path(
                    remoteQUrl.toDisplayString(
                        QUrl.FormattingOptions(QUrl.RemoveUserInfo)
                    )
                )
            # peak danger has passed...
            if not remotePath.root or (
                isinstance(remotePath, PosixPath) and remotePath.is_mount()
            ):
                # local path on linux
                continue

            # # handle the case of `//<hostname>.<domain>` vs. `//<hostname>`
            remotePath = sanitizeHostPath(remotePath)

            # update the respective lookups
            self.localToNetworkPath[localPath] = remotePath
            self.networkToLocalPath[remotePath] = localPath

    def getLocalFilepath(self, fpath: Path) -> Optional[Path]:
        localPath = self._getLocalFilepath(fpath)
        if localPath is None or not localPath.exists():
            self.refreshMapping()
            localPath = self._getLocalFilepath(fpath)
        return localPath

    def _getLocalFilepath(self, fpath: Path) -> Optional[Path]:
        if fpath.exists():
            return fpath

        hostOS = system()
        qurl_fpath = QUrl.fromLocalFile(fpath.as_posix())

        if qurl_fpath.host() == "":
            # already a local file dummy!
            return fpath

        for networkMount, localMount in self.networkToLocalPath.items():
            try:
                if hostOS == "Darwin":
                    networkMount = matchCase(fpath, networkMount)
                remainder = fpath.relative_to(networkMount)
                return localMount / remainder
            except ValueError:
                continue

        return None

    def getNetworkFilepath(self, fpath: Path) -> Optional[Path]:
        networkPath = self._getNetworkFilepath(fpath)
        if networkPath is None:
            self.refreshMapping()
            networkPath = self._getNetworkFilepath(fpath)
        return networkPath

    def _getNetworkFilepath(self, fpath: Path) -> Optional[Path]:
        hostOS = system()
        qurl_fpath = QUrl.fromLocalFile(fpath.as_posix())

        if qurl_fpath.host() != "":
            return fpath

        for localMount, networkMount in self.localToNetworkPath.items():
            try:
                if hostOS == "Darwin":
                    localMount = matchCase(fpath, localMount)
                remainder = fpath.relative_to(localMount)
                return networkMount / remainder
            except ValueError:
                continue
        return None


def matchCase(fPath: Path, caseInsensitivePath: Path) -> Path:
    """Method exists to help with the case-sensitive nature of Path.relativeTo on macOS.
    macOS allows for case-insensitivity, but pathlib.PosixPath does not support that
    """
    correctedPath = Path(fPath.root)
    for remote, questionable in zip(fPath.parts[1:], caseInsensitivePath.parts[1:]):
        if questionable.lower() == remote.lower():
            correctedPath /= remote
        else:
            return caseInsensitivePath
    return correctedPath


def sanitizeHostPath(path: Path) -> Path:
    # handle the case of `//<hostname>.<domain>` vs. `//<hostname>`
    if len(path.parts) > 1 and "." in path.parts[1]:
        parts = list(path.parts)
        remote = parts[1].partition(".")[0]
        path = Path(parts[0] + remote + os.sep.join(parts[2:]))
    return path


def pathToQUrl(path: Path) -> QUrl:
    return stringToQUrl(path.resolve().as_posix())


def qUrlToString(url: QUrl) -> str:
    return url.toDisplayString(QUrl.FormattingOptions(QUrl.PreferLocalFile))


def stringToQUrl(path: str) -> QUrl:
    return QUrl.fromLocalFile(path)


def qUrlToPath(url: QUrl) -> Path:
    return Path(qUrlToString(url))


def qUrlToQDir(url: QUrl) -> QDir:
    return QDir(qUrlToString(url))


def pathToQDir(path: Path) -> QDir:
    return QDir(path.resolve().as_posix())
