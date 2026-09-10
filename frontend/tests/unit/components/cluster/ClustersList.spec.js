import ClustersList from "@/components/cluster/ClustersList";

describe("ClustersList service health", () => {
  const jupyterhub = {
    label: "JupyterHub",
    url: "https://jupyter.example.com",
    status: "healthy",
  };
  const freeipa = {
    label: "FreeIPA",
    url: "https://ipa.example.com",
    status: "unavailable",
  };

  const methods = ClustersList.methods;

  it("uses green for an available service", () => {
    expect(methods.serviceStatusColor(jupyterhub)).toBe("green");
    expect(methods.serviceStatusLabel(jupyterhub)).toBe("JupyterHub is available");
  });

  it("uses red for an unhealthy service", () => {
    expect(methods.serviceStatusColor(freeipa)).toBe("red");
    expect(methods.serviceStatusLabel(freeipa)).toBe("FreeIPA is unhealthy");
  });
});
