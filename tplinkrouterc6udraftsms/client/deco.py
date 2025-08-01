from base64 import b64decode
from json import dumps
from requests.exceptions import ConnectTimeout
from collections.abc import Callable
from macaddress import EUI48
from ipaddress import IPv4Address
from logging import Logger
from tplinkrouterc6udraftsms.common.helper import get_ip, get_mac, get_value
from tplinkrouterc6udraftsms.common.package_enum import Connection
from tplinkrouterc6udraftsms.common.dataclass import Firmware, Status, Device, IPv4Status
from tplinkrouterc6udraftsms.client_abstract import AbstractRouter
from tplinkrouterc6udraftsms.client.c6u import TplinkEncryption


class TPLinkDecoClient(TplinkEncryption, AbstractRouter):
    def __init__(self, host: str, password: str, username: str = 'admin', logger: Logger = None,
                 verify_ssl: bool = True, timeout: int = 30) -> None:
        super().__init__(host, password, username, logger, verify_ssl, timeout)

        self._headers_request = {'Content-Type': 'application/json'}
        self._headers_login = {'Content-Type': 'application/json'}
        self._data_block = 'result'
        self.devices = []

    def logout(self) -> None:
        self.request('admin/system?form=logout', dumps({'operation': 'logout'}), True)
        self._stok = ''
        self._sysauth = ''
        self._logged = False

    def set_wifi(self, wifi: Connection, enable: bool) -> None:
        en = {'enable': enable}
        if Connection.HOST_2G == wifi:
            params = {'band2_4': {'host': en}}
        elif Connection.HOST_5G == wifi:
            params = {'band5_1': {'host': en}}
        elif Connection.GUEST_5G == wifi:
            params = {'band5_1': {'guest': en}}
        elif Connection.HOST_6G == wifi:
            params = {'band6': {'host': en}}
        elif Connection.GUEST_6G == wifi:
            params = {'band6': {'guest': en}}
        else:
            params = {'band2_4': {'guest': en}}

        self.request('admin/wireless?form=wlan', dumps({'operation': 'write', 'params': params}))

    def reboot(self) -> None:
        if not self.devices:
            self.get_firmware()
        self.request('admin/device?form=system', dumps({
            'operation': 'reboot',
            'params': {'mac_list': [{"mac": item['mac']} for item in self.devices]}}))

    def get_firmware(self) -> Firmware:
        self.devices = self.request('admin/device?form=device_list', dumps({"operation": "read"})).get(
            'device_list', [])

        for item in self.devices:
            if item.get('role') != 'master' and len(self.devices) != 1:
                continue
            firmware = Firmware(item.get('hardware_ver', ''),
                                item.get('device_model', ''),
                                item.get('software_ver', ''))

        return firmware

    def get_status(self) -> Status:
        data = self.request('admin/network?form=wan_ipv4', dumps({'operation': 'read'}))

        status = Status()
        element = get_value(data, ['wan', 'ip_info', 'mac'])
        status._wan_macaddr = EUI48(element) if element else None
        status._lan_macaddr = EUI48(get_value(data, ['lan', 'ip_info', 'mac']))
        element = get_value(data, ['wan', 'ip_info', 'ip'])
        status._wan_ipv4_addr = IPv4Address(element) if element else None
        element = get_value(data, ['lan', 'ip_info', 'ip'])
        status._lan_ipv4_addr = IPv4Address(element) if element else None
        element = get_value(data, ['wan', 'ip_info', 'gateway'])
        status._wan_ipv4_gateway = IPv4Address(element) if element else None

        data = self.request('admin/network?form=performance', dumps({"operation": "read"}))
        status.mem_usage = data.get('mem_usage')
        status.cpu_usage = data.get('cpu_usage')

        data = self.request('admin/wireless?form=wlan', dumps({'operation': 'read'}))
        status.wifi_2g_enable = get_value(data, ['band2_4', 'host', 'enable'])
        status.guest_2g_enable = get_value(data, ['band2_4', 'guest', 'enable'])
        status.wifi_5g_enable = get_value(data, ['band5_1', 'host', 'enable'])
        status.guest_5g_enable = get_value(data, ['band5_1', 'guest', 'enable'])
        status.wifi_6g_enable = get_value(data, ['band6', 'host', 'enable'])
        status.guest_6g_enable = get_value(data, ['band6', 'guest', 'enable'])

        devices = []
        data = self.request('admin/client?form=client_list', dumps(
            {"operation": "read", "params": {"device_mac": "default"}})).get('client_list', [])

        for item in data:
            if not item.get('online'):
                continue
            conn = self._map_wire_type(item)
            if conn == Connection.WIRED:
                status.wired_total += 1
            elif conn.is_host_wifi():
                status.wifi_clients_total += 1
            elif conn.is_guest_wifi():
                status.guest_clients_total += 1
            elif conn.is_iot():
                if status.iot_clients_total is None:
                    status.iot_clients_total = 0
                status.iot_clients_total += 1

            device = Device(conn,
                            get_mac(item.get('mac', '00:00:00:00:00:00')),
                            get_ip(item.get('ip', '0.0.0.0')),
                            b64decode(item['name']).decode())
            device.down_speed = item.get('down_speed')
            device.up_speed = item.get('up_speed')
            devices.append(device)

        status.clients_total = (status.wired_total + status.wifi_clients_total + status.guest_clients_total
                                + (0 if status.iot_clients_total is None else status.iot_clients_total))
        status.devices = devices

        return status

    def get_ipv4_status(self) -> IPv4Status:
        ipv4_status = IPv4Status()
        data = self.request('admin/network?form=wan_ipv4', dumps({'operation': 'read'}))
        element = get_value(data, ['wan', 'ip_info', 'mac'])
        ipv4_status._wan_macaddr = get_mac(element if element else '00:00:00:00:00:00')
        element = get_value(data, ['wan', 'ip_info', 'ip'])
        ipv4_status._wan_ipv4_ipaddr = IPv4Address(element) if element else None
        element = get_value(data, ['wan', 'ip_info', 'gateway'])
        ipv4_status._wan_ipv4_gateway = IPv4Address(element) if element else None
        element = get_value(data, ['wan', 'dial_type'])
        ipv4_status._wan_ipv4_conntype = element if element else ''
        element = get_value(data, ['wan', 'ip_info', 'mask'])
        ipv4_status._wan_ipv4_netmask = IPv4Address(element) if element else None
        element = get_value(data, ['wan', 'ip_info', 'dns1'])
        ipv4_status._wan_ipv4_pridns = get_ip(element if element else '0.0.0.0')
        element = get_value(data, ['wan', 'ip_info', 'dns2'])
        ipv4_status._wan_ipv4_snddns = get_ip(element if element else '0.0.0.0')
        element = get_value(data, ['lan', 'ip_info', 'mac'])
        ipv4_status._lan_macaddr = get_mac(element if element else '00:00:00:00:00:00')
        element = get_value(data, ['lan', 'ip_info', 'ip'])
        ipv4_status._lan_ipv4_ipaddr = get_ip(element if element else '0.0.0.0')
        ipv4_status.lan_ipv4_dhcp_enable = False
        element = get_value(data, ['lan', 'ip_info', 'mask'])
        ipv4_status._lan_ipv4_netmask = get_ip(element if element else '0.0.0.0')

        return ipv4_status

    def authorize(self) -> None:
        self._retry_request(super().authorize)

    def request(self, path: str, data: str, ignore_response: bool = False, ignore_errors: bool = False) -> dict | None:
        return self._retry_request(super().request, path, data, ignore_response, ignore_errors)

    def _retry_request(self, callback: Callable, *args):
        retries = 0
        while True:
            try:
                return callback(*args)
            except ConnectTimeout as err:
                if retries > 2:
                    raise err
                retries += 1

    def _map_wire_type(self, data: dict) -> Connection:
        if data.get('wire_type') == 'wired':
            return Connection.WIRED
        mapping = {'band2_4': {'main': Connection.HOST_2G, 'guest': Connection.GUEST_2G, 'iot': Connection.IOT_2G},
                   'band5': {'main': Connection.HOST_5G, 'guest': Connection.GUEST_5G, 'iot': Connection.IOT_5G},
                   'band6': {'main': Connection.HOST_6G, 'guest': Connection.GUEST_6G, 'iot': Connection.IOT_6G}
                   }
        result = get_value(mapping, [data.get('connection_type'), data.get('interface')])

        return result if result else Connection.UNKNOWN

    @staticmethod
    def _get_login_data(crypted_pwd: str) -> str:
        data = {
            "params": {"password": crypted_pwd},
            "operation": "login",
        }

        return dumps(data)

    def _is_valid_response(self, data: dict) -> bool:
        return 'error_code' in data and data['error_code'] == 0
