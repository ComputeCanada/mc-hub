/* Production-build smoke checks. Every API request is intercepted; no backend is contacted. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");
const dist = path.resolve(__dirname, "../../dist");
const projects = [
    { id: 11, name: "Research", provider: "openstack", admin: true, can_manage_notifications: true, nb_clusters: 0 },
    { id: 22, name: "Teaching", provider: "openstack", admin: false, nb_clusters: 0 },
];
const specs = {
    cloud: { id: 11, name: "Research" },
    cluster_name: "smoke",
    domain: "example.org",
    image: "image",
    mc_version: "14",
    instances: { node: { count: 1, type: "p1", tags: ["node"] } },
    volumes: { nfs: {} },
    public_keys: [],
    guest_passwd: "password",
    nb_users: 1,
    hieradata_entries: [],
};
const benchmark = {
    id: "bench-1",
    project_id: 11,
    name: "Browser benchmark",
    enabled: true,
    frequency: "daily",
    timeout_minutes: 120,
    success_criterion: "healthy",
    setup_status: "ready",
    identity_locked: true,
    configuration: specs,
    next_run_at: null,
};
const durations = { count: 0, average_seconds: null, median_seconds: null, p95_seconds: null };
async function main() {
    await fs.access(path.join(dist, "index.html"));
    const server = http.createServer(async (req, res) => {
        try {
            const pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
            const filename = path.resolve(dist, `.${pathname}`);
            if (!filename.startsWith(dist + path.sep) && filename !== dist) {
                res.writeHead(403).end();
                return;
            }
            const extension = path.extname(filename);
            const file =
                extension && !req.headers.accept?.includes("text/html") ? filename : path.join(dist, "index.html");
            const data = await fs.readFile(file);
            res.setHeader(
                "Content-Type",
                { ".js": "text/javascript", ".css": "text/css", ".html": "text/html", ".ico": "image/x-icon" }[
                    path.extname(file)
                ] || "application/octet-stream"
            );
            res.end(data);
        } catch {
            res.writeHead(404).end();
        }
    });
    await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(0, "127.0.0.1", resolve);
    });
    let browser;
    try {
        browser = await chromium.launch({
            headless: true,
            ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
        });
        const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
        page.setDefaultTimeout(10000);
        const errors = [],
            requests = [];
        page.on("pageerror", (error) => errors.push(error.message));
        page.on("console", (message) => {
            if (["error", "warning"].includes(message.type())) errors.push(message.text());
        });
        const base = `http://127.0.0.1:${server.address().port}`;
        let defaultProject = 22;
        let allowBenchmarks = true;
        await page.route("**/*", async (route) => {
            const request = route.request(),
                url = new URL(request.url());
            // Keep this smoke run offline, including optional CDN fonts/icons.
            if (url.origin !== base) return route.fulfill({ contentType: "text/css", body: "" });
            if (!url.pathname.startsWith("/api/")) return route.continue();
            const endpoint = url.pathname.slice(4),
                method = request.method();
            requests.push({ endpoint, method, body: request.postDataJSON() });
            let data;
            if (endpoint === "/users/me") {
                if (method === "PATCH") defaultProject = request.postDataJSON().default_project_id;
                data = {
                    username: "Browser tester",
                    is_admin: true,
                    public_keys: [],
                    default_project_id: defaultProject,
                };
            } else if (endpoint === "/service-status") data = { providers: [] };
            else if (endpoint === "/projects")
                data = projects.map((project) => ({ ...project, admin: allowBenchmarks && project.admin }));
            else if (endpoint === "/magic-castles") data = [];
            else if (endpoint === "/magic-castles/smoke.example.org/status")
                data = { status: "provisioning_success", stateful: true, progress: [] };
            else if (endpoint === "/magic-castles/smoke.example.org") data = specs;
            else if (endpoint === "/template/default") data = specs;
            else if (endpoint.startsWith("/available-resources/"))
                data = {
                    provider: "openstack",
                    possible_resources: {
                        domain: ["example.org"],
                        image: ["image"],
                        mc_version: ["14"],
                        types: ["p1"],
                        tag_types: {},
                    },
                    resource_details: {
                        instance_types: [
                            { name: "p1", ram: 1024, vcpus: 1, required_volume_count: 0, required_volume_size: 0 },
                        ],
                    },
                    quotas: Object.fromEntries(
                        ["instance_count", "ram", "vcpus", "volume_count", "volume_size", "ips"].map((key) => [
                            key,
                            { max: 10000 },
                        ])
                    ),
                };
            else if (/^\/projects\/\d+\/capacity$/.test(endpoint)) data = { plans: [], forecast: { segments: [] } };
            else if (endpoint === "/benchmarks") data = { projects: [projects[0]], benchmarks: [benchmark] };
            else if (endpoint === "/benchmarks/bench-1")
                data =
                    method === "PUT"
                        ? { id: "bench-1" }
                        : {
                              benchmark,
                              total_runs: 1,
                              comparison_groups: [],
                              default_comparison_group: null,
                              runs: [
                                  {
                                      id: "run-1",
                                      requested_at: "2027-01-01T00:00:00Z",
                                      phase: "cleanup",
                                      outcome: "failed",
                                      error: "Smoke diagnostic",
                                      configuration: specs,
                                  },
                              ],
                          };
            else if (endpoint === "/usage")
                data = {
                    projects,
                    summary: {},
                    months: [{ month: "2027-01", successful_deployments: 1 }],
                    page: Number(url.searchParams.get("page")) || 1,
                    attempts: [{ id: 1, hostname: `page-${url.searchParams.get("page") || 1}` }],
                    attempt_count: 26,
                    apply_to_healthy: durations,
                    completed_lifetime: durations,
                    ongoing_age: durations,
                    last_poll_at: null,
                };
            else if (endpoint === "/projects/openstack/clouds") data = { clouds: [] };
            else {
                errors.push(`Unexpected API request: ${method} ${endpoint}`);
                return route.fulfill({ status: 500, json: {} });
            }
            return route.fulfill({ json: data });
        });
        await page.goto(base);
        await page.getByText("Your Magic Castles", { exact: true }).waitFor();
        await page.getByRole("link", { name: "Create cluster", exact: true }).click();
        await page.getByText("Magic Castle Creation", { exact: true }).waitFor();
        await page.getByLabel("count", { exact: true }).waitFor();
        for (const width of [1440, 600, 375]) {
            await page.setViewportSize({ width, height: 1000 });
            const fields = await page
                .locator(".instance-row")
                .first()
                .evaluate((row) => ({
                    overflow: row.scrollWidth > row.clientWidth,
                    clippedLabels: [...row.querySelectorAll(".v-field-label--floating")]
                        .filter((label) => label.scrollWidth > label.clientWidth + 1)
                        .map((label) => label.textContent),
                }));
            assert.equal(fields.overflow, false, `Instance row overflows at ${width}px`);
            assert.deepEqual(fields.clippedLabels, [], `Instance labels are clipped at ${width}px`);
        }
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.getByLabel("Cluster name", { exact: true }).fill("browser-cluster");
        await page.getByText("Additional puppet configuration (optional)", { exact: true }).click();
        await page.getByRole("button", { name: "Add entry" }).click();
        await page.getByLabel("Key", { exact: true }).fill("profile::example");
        await page.getByLabel("Value", { exact: true }).fill("browser-value");
        page.on("dialog", (dialog) => dialog.accept());
        await page.getByRole("button", { name: "Browser tester" }).click();
        await page.getByRole("link", { name: "Projects", exact: true }).click();
        const preferred = page.getByRole("checkbox", { name: "Set Research as default project" });
        await preferred.click();
        await page.waitForFunction(
            () => document.querySelector('input[aria-label="Set Research as default project"]')?.checked
        );
        assert.equal(defaultProject, 11);
        await preferred.click();
        assert.equal(await preferred.isChecked(), true);
        await page.getByRole("button", { name: "Add Project", exact: true }).click();
        await page.getByLabel("Project name", { exact: true }).fill("Browser project");
        await page.getByRole("button", { name: "Cancel", exact: true }).click();
        await page.locator('header a[href="/capacity"]').click();
        await page.getByRole("heading", { name: "Project capacity planner" }).waitFor();
        await page.getByRole("button", { name: "Plan resource usage" }).click();
        await page.getByLabel("Start date", { exact: true }).fill("2099-01-01");
        await page.getByLabel("End date", { exact: true }).fill("2099-01-02");
        await page.getByRole("button", { name: "Check planned capacity" }).waitFor();
        await page.getByRole("button", { name: "Cancel", exact: true }).click();
        await page.locator('header a[href="/benchmarks"]').click();
        await page.getByRole("heading", { name: "Browser benchmark", exact: true }).waitFor();
        await page.locator("tbody tr").first().getByRole("button").click();
        await page.getByText("Smoke diagnostic", { exact: true }).waitFor();
        await page.getByRole("link", { name: "Edit", exact: true }).click();
        await page.getByLabel("Benchmark name", { exact: true }).fill("Updated in browser");
        await page.getByRole("button", { name: "Save benchmark", exact: true }).click();
        await page.waitForURL(/\/benchmarks\?benchmark=bench-1$/);
        assert.ok(requests.some((entry) => entry.method === "PUT" && entry.body.name === "Updated in browser"));
        await page.getByRole("button", { name: "Browser tester" }).click();
        await page.getByRole("link", { name: "Service adoption", exact: true }).click();
        await page.getByRole("heading", { name: "Service adoption" }).waitFor();
        await page.locator(".v-pagination").last().getByRole("button", { name: "Next page" }).click();
        await page.getByText("page-2", { exact: true }).waitFor();
        await page.reload();
        await page.getByRole("heading", { name: "Service adoption" }).waitFor();
        await page.goto(base + "/clusters/smoke.example.org");
        await page.getByText("Magic Castle Modification", { exact: true }).waitFor();
        await page.getByLabel("count", { exact: true }).waitFor();
        allowBenchmarks = false;
        await page.goto(base + "/benchmarks/new");
        await page.waitForURL(base + "/");
        await page.getByText("Your Magic Castles", { exact: true }).waitFor();
        assert.equal(await page.locator('header a[href="/benchmarks"]').count(), 0);
        await page.goto(base + "/unknown-route");
        await page
            .getByText(/not found/i)
            .first()
            .waitFor();
        assert.deepEqual(errors, []);
        console.log(
            "PASS: production startup, cluster form, Projects/default/dialogs, planner dates, benchmark history/edit/save, Usage pagination, cluster edit, access denial, deep reload and 404; no browser errors or warnings."
        );
    } finally {
        if (browser) await browser.close();
        await new Promise((resolve) => server.close(resolve));
    }
}
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
