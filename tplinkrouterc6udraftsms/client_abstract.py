from requests.packages import urllib3
from logging import Logger
from tplinkrouterc6udraftsms.common.package_enum import Connection
from tplinkrouterc6udraftsms.common.dataclass import Firmware, Status, IPv4Status
from abc import ABC, abstractmethod


class AbstractRouter(ABC):
    def __init__(self, host: str, password: str, username: str = 'admin', logger: Logger = None,
                 verify_ssl: bool = True, timeout: int = 30) -> None:
        self.username = username
        self.password = password
        self.timeout = timeout
        self._logger = logger
        self.host = host
        if not (self.host.startswith('http://') or self.host.startswith('https://')):
            self.host = "http://{}".format(self.host)
        self._verify_ssl = verify_ssl
        if self._verify_ssl is False:
            urllib3.disable_warnings()

    @abstractmethod
    def supports(self) -> bool:
        pass

    @abstractmethod
    def authorize(self) -> None:
        pass

    @abstractmethod
    def logout(self) -> None:
        pass

    @abstractmethod
    def get_firmware(self) -> Firmware:
        pass

    @abstractmethod
    def get_status(self) -> Status:
        pass

    @abstractmethod
    def get_ipv4_status(self) -> IPv4Status:
        pass

    @abstractmethod
    def reboot(self) -> None:
        pass

    @abstractmethod
    def set_wifi(self, wifi: Connection, enable: bool) -> None:
        pass
