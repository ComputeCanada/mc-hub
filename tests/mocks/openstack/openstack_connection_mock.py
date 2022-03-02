import re


class OpenStackConnectionMock:
    """
    OpenStackConnectionMock is a mock class for the openstack.connection.Connection class.
    It is used to avoid making real calls to the OpenStack API while running unit and integration tests.
    Right now, only a few OpenStack APIs are supported and return realistic values.
    """

    class ComputeApi:
        class Flavor:
            def __init__(self, name, vcpus, ram, disk):
                self.name = name
                self.vcpus = vcpus
                self.ram = ram
                self.disk = disk

        def flavors(self):
            flavors = [
                self.Flavor("p1-1.5gb", 1, 1_536, 0),
                self.Flavor("p2-3gb", 2, 3_072, 0),
                self.Flavor("p4-6gb", 4, 6_144, 0),
                self.Flavor("c8-30gb-186", 8, 30_720, 20),
                self.Flavor("c8-90gb-186", 8, 92_160, 20),
                self.Flavor("g2-c24-112gb-500", 24, 114_688, 80),
                self.Flavor("c16-120gb-392", 16, 122_880, 20),
            ]
            return (flavor for flavor in flavors)

        def get(self, url):
            if re.search(r"\/os-quota-sets\/.*\/detail", url):
                return OpenStackConnectionMock.OpenStackResponseMock(
                    {
                        "quota_set": {
                            "instances": {"limit": 128, "in_use": 28},
                            "cores": {"limit": 500, "in_use": 199},
                            "ram": {
                                # 280 GiO limit, 180 GiO used
                                "limit": 286_720,
                                "in_use": 184_320,
                            },
                        }
                    }
                )
            else:
                NotImplementedError(
                    f"OpenStack connection mock not implemented for url {url}"
                )

    class NetworkApi:
        class Ip:
            def __init__(self, floating_ip_address):
                self.floating_ip_address = floating_ip_address

        def ips(self, *, status=None):
            active_ips = [self.Ip("1.1.1.1"), self.Ip("1.1.1.2")]
            down_ips = [self.Ip("2.1.1.1"), self.Ip("2.1.1.2"), self.Ip("2.1.1.3")]
            if status == "ACTIVE":
                ips = active_ips
            elif status == "DOWN":
                ips = down_ips
            else:
                ips = [active_ips] + [down_ips]
            return (ip for ip in ips)

        def get(self, url):
            if re.search(r"\/quotas\/.*\/details.json", url):
                return OpenStackConnectionMock.OpenStackResponseMock(
                    {"quota": {"floatingip": {"limit": 5, "used": 3}}}
                )
            else:
                raise NotImplementedError(
                    f"OpenStack connection mock not implemented for url {url}"
                )

    class ImageApi:
        class Image:
            def __init__(self, name):
                self.name = name

        def images(self):
            images = [
                self.Image("centos7"),
                self.Image("CentOS-8 x64"),
                self.Image("CentOS VGPU"),
            ]
            return iter(images)

    class BlockStorageApi:
        def get(self, url):
            if re.search(r"\/os-quota-sets\/.*\?usage=true", url):
                return OpenStackConnectionMock.OpenStackResponseMock(
                    {
                        "quota_set": {
                            "gigabytes": {"limit": 1000, "in_use": 720},
                            "volumes": {"limit": 128, "in_use": 100},
                        }
                    }
                )
            else:
                raise NotImplementedError(
                    f"OpenStack connection mock not implemented for url {url}"
                )

    class OpenStackResponseMock:
        def __init__(self, json_data: dict):
            self.__json_data = json_data

        def json(self) -> dict:
            return self.__json_data

    def __init__(self):
        self.compute = self.ComputeApi()
        self.network = self.NetworkApi()
        self.image = self.ImageApi()
        self.block_storage = self.BlockStorageApi()
        self.current_project_id = "MOCK_PROJECT_ID_f6b8437ac74893"
