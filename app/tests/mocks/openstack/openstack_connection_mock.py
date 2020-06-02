class OpenStackConnectionMock:
    class ComputeApi:
        class Flavor:
            def __init__(self, name, vcpus, ram, disk):
                self.name = name
                self.vcpus = vcpus
                self.ram = ram
                self.disk = disk

        def flavors(self):
            # Here, rounded values are used to simplify the calculations
            # with RAM quantities, but they don't exactly match the real values
            flavors = [
                self.Flavor("p1-1.5gb", 1, 1_500, 0),
                self.Flavor("c8-30gb-186", 8, 30_000, 20),
                self.Flavor("c8-90gb-186", 8, 90_000, 20),
                self.Flavor("g2-c24-112gb-500", 24, 112_000, 80),
                self.Flavor("c16-120gb-392", 16, 120_000, 20),
            ]
            return (flavor for flavor in flavors)

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
            return (image for image in images)

    def __init__(self):
        self.compute = self.ComputeApi()
        self.network = self.NetworkApi()
        self.image = self.ImageApi()
