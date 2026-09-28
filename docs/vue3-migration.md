# Vue 3 migration foundation

Steps 2–6 are implemented on `migration/vue3-foundation`: Vue 3 startup,
routing, shared components, feature screens, and component/browser checks now
use the real application. The temporary foundation demo has been removed.
Container, CI, live-backend, and release-support validation remain before merge.
This branch is not yet ready for a production release.

## Dependency decisions

| Package/tool | Selected version | Reason |
| --- | --- | --- |
| `vue` | 3.5.43 | Vue 3 runtime; no compatibility build |
| `@vue/compiler-sfc` | 3.5.43 | Exact match with the runtime |
| `vue-router` | 4.6.4 | Vue 3 routing; accepts Vue `^3.5.0` |
| `vuetify` | 3.13.5 | Vue 2-to-3 migration target; accepts Vue `^3.5.0` |
| `@vue/test-utils` | 2.5.1 | Vue 3 component mounting |
| `@vue/vue3-jest` | 27.0.0 | Vue 3 transformer compatible with retained Jest 27 |
| Vue CLI and CLI plugins | 5.0.9 | Retain build and test orchestration during migration |
| Jest / `babel-jest` / jsdom environment | 27.5.1 | Retain the versions selected by the CLI Jest plugin |
| `vue-loader` | 17.0.0 | Existing Vue 3 loader selected automatically by Vue CLI |
| webpack | 5.111.1 | Existing build pipeline, including Monaco worker plugin |
| Sass / `sass-loader` | 1.103.1 / 8.0.2 | Existing versions compile Vuetify CSS and scoped SCSS |
| Node / npm used for verification | 24.21.0 / 11.19.0 | Node 24 matches the Docker build's major version |

The new direct dependencies use exact versions. Unrelated direct dependency
ranges and existing resolved package versions were preserved. npm regenerated
the lockfile after the obsolete Vue 2 entries were removed from a temporary
copy, avoiding the stale-tree peer conflicts encountered with an in-place
install. No `--force`, `--legacy-peer-deps`, or dependency overrides are required.
The lockfile's root version now also matches the existing package version 15.5.8.

Vuetify 3 is the intermediate UI-library target for this migration, rather than
an implicit upgrade to the latest major. Review its
[support window](https://vuetifyjs.com/introduction/long-term-support/) before
planning the production release; schedule a later major upgrade separately.
Use the [Vuetify 3 guide](https://v3.vuetifyjs.com/en/getting-started/upgrade-guide/)
for the component migration.

Removed direct dependencies: `vue-template-compiler`, `@vue/vue2-jest`,
`vue-jest`, `vuetify-loader`, and `vue-cli-plugin-vuetify`.
Vue CLI still carries Vue 2 loader/compiler-helper tooling for its dual-version
support and declares optional Vue 2 peers. These are not an installed Vue 2
runtime or the active compilation path. The generated webpack Vue rule uses
`vue-loader/dist/index.js` from version 17.0.0.

## Run and validate the application

From the repository root, with Node 24 available:

```sh
cd frontend
npm ci
npm run test:unit -- --runInBand
npm run lint -- --no-fix
npm run build
npx playwright install chromium
npm run test:browser
# Start development against your configured backend:
npm run serve
```

`frontend/.nvmrc` selects Node 24. The build writes the real application to
`frontend/dist`. The browser check serves that directory on an ephemeral
localhost port with SPA fallback, launches headless Chromium, and shuts both
down after the check. It intercepts every API request and mocks optional external
font/icon stylesheets, so it does not contact or modify a backend. Unexpected API
requests, browser errors, and console warnings fail the check. Install Chromium
with `npx playwright install --with-deps chromium` when system libraries are
needed, or set `CHROME_PATH` to an existing Chrome/Chromium executable.

Rebuild before running browser checks after application changes. This smoke test
covers routed frontend integration, not authentication with a live identity
provider, actual cloud provisioning, external font rendering, or every visual
layout. Component suites cover detailed AWS/OpenStack and failure behavior.

The old foundation commands, alternate entry, environment modes, and demo-only
test were removed in step 6.7. Earlier verification sections below record the
migration history; use the commands above for the current branch.

## Implementation conventions

- `src/main.js` registers the production router, Vuetify instance, and unload
  confirmation plugin with `createApp`, then mounts `App.vue` after routing.
- Components retain the Options API. Composition API and TypeScript conversion
  are not required for the upgrade.
- Vuetify components and directives are imported explicitly through supported
  public subpaths. No automatic-import webpack plugin is required.
- Global Vuetify styles load in the browser entry. The existing public template
  supplies the MDI font, and the Vuetify plugin selects that icon set.
- The real Vuetify input, button, and Router 4 navigation are exercised together
  by `tests/unit/foundation/Foundation.spec.js` using memory history.
- The existing CLI Jest preset automatically selects `@vue/vue3-jest` from the
  installed Vue major. The configuration supplies explicit Vuetify subpath
  mappings for Jest 27's older resolver and retains the `@` alias and transforms.
- `tests/setup.js` supplies the missing CSS feature-detection and ResizeObserver
  APIs needed to mount Vuetify in jsdom. These shims do not test browser layout.
- ESLint now uses `plugin:vue/vue3-essential`. The focused lint command checks
  only the foundation and its configuration; full lint still reports legacy APIs.

See the [Vue Jest version matrix](https://github.com/vuejs/vue-jest#installation)
and [Vue Test Utils migration guide](https://test-utils.vuejs.org/migration/)
when migrating additional tests.

## Step 2 verification

Verified on Node 24.21.0 with npm 11.19.0:

- `npm ci --no-audit --no-fund`: successful clean installation.
- `npm run test:foundation`: one passing integration test with real Vuetify.
- `npm run lint:foundation`: no errors.
- `npm run build:foundation`: successful production compilation with a separate
  lazy-route chunk and the retained Monaco worker asset.
- Headless Chrome against both the development server and an HTTP server serving
  the production output: typing, clicking, Vuetify CSS, scoped SCSS, MDI icons,
  lazy navigation, and direct-route reload passed without runtime errors or
  console warnings. Browser tooling was temporary and is not a project dependency.
- `vue-cli-service inspect --mode vue3-foundation --rule vue`: Vue 3 loader.
- `vue-cli-service inspect --mode vue3-foundation --plugin define`: production
  `NODE_ENV` confirmed.
- Dependency inspection: one Vue 3 runtime; no installed `vue-template-compiler`,
  `@vue/vue2-jest`, `vue-jest`, or `vuetify-loader`. `npm ls` returns exit code 1
  when explicitly querying this empty list, which is expected.
- `npm ls --all`: successful, with no invalid dependency entries.

The build reports Sass legacy-JS-API deprecation and webpack asset/entry-size
warnings, including the retained Monaco worker. They are not compilation errors;
track Sass loader modernization and bundle-size review for later tooling work.
The editor itself has not been migrated or exercised by this demonstration.

The complete application checks were also run to establish the handoff:

- `npm run test:unit -- --runInBand`: 21 suites failed, 3 passed; 19 tests failed,
  24 passed. Failures include `Vue.observable`, `Vue.use`, `vuetify/lib`, and Vue 2
  mounting/cleanup conventions. No legacy tests were removed or skipped.
- `npm run build`: fails on unmigrated Vue 2 code, including deprecated lifecycle
  hooks, `.sync`, and template key placement. The ordinary Docker build and
  existing frontend CI are therefore not expected to pass yet.

## Step 3: application startup and shell

The real entry now uses `createApp`, installs unload confirmation before the
router starts its initial navigation, registers a fresh Vuetify instance, and
mounts after `router.isReady()`. The exported `ready` promise propagates initial
navigation errors; the bootstrap integration test exercises the real entry.

`createAppRouter(history)` preserves the application URLs, names, access
metadata, lazy routes, and query-to-prop mappings. It defaults to
`createWebHistory(process.env.BASE_URL)` and accepts memory history in tests.
The fallback route is now `/:pathMatch(.*)*`. Benchmark-access state uses
`reactive`, and its guard returns a boolean or redirect. Concurrent permission
lookups still share one request, and failures revoke access while allowing retry.

The unload plugin exposes the existing helper names through
`app.config.globalProperties`. It retains dirty state after cancelled, duplicate,
or failed navigation and clears it after successful navigation or an explicit
disable. It removes its router guards on application unmount and restores its
previous browser handler only if it still owns that handler. The repository can
still replace `window.onbeforeunload` before its session-expiry reload.

The real Vuetify plugin explicitly registers the shell components, directives,
MDI icons, and existing light-theme colors. Feature migrations should add their
required components to this registration as they are converted. `App.vue` uses
`v-main` and Vuetify 3 navigation props; the account menu uses the new activator
binding. Projects uses router navigation so unsaved-change guards apply, while
Logout remains a normal link to Shibboleth. The status banner uses the new props
and `beforeUnmount` cleanup.

Run the step-3 checks from `frontend`:

```sh
npm run test:startup
npm run lint:startup
npm run test:foundation
npm run lint:foundation
npm run build:foundation
```

Verification on Node 24.21.0:

- Startup checks: 6 suites and 42 tests pass. They cover the real bootstrap,
  production route definitions, route props/base, all benchmark guards, shared
  permission state, unload protection, the real Vuetify shell/account menu, and
  service-status polling and cleanup.
- The foundation test and both focused lint commands pass.
- The foundation production build and the production shell build using temporary
  feature-screen placeholders pass. The known Sass/webpack warnings remain.
- Headless Chrome exercised the real `main.js`, router, plugins, `App.vue`,
  account menu, and status banner with temporary feature-screen placeholders
  and intercepted API responses. Checks passed for theme/layout, status details,
  Projects and Logout links, repeated navigation cancellation, confirmed
  navigation, permission denial/grant/API failure, deep links and props, and
  unknown nested URL reload. No runtime errors or console warnings occurred.
  The temporary webpack replacement configuration and browser tooling are not
  part of the application or project dependencies; this does not validate the
  unfinished feature screens.
- Full suite: 10 suites pass, 18 fail; 73 tests pass, 16 fail. Remaining failures
  include legacy `Vue.use`, `vuetify/lib`, `wrapper.destroy`, and unmigrated
  component behavior. No legacy suites were removed or skipped.
- The ordinary application build still fails on feature-screen lifecycle hooks,
  `.sync`, and template key placement. Docker/CI release checks remain deferred
  until the feature migration; passing shell tests do not imply a release-ready
  application.

## Step 4: Vue 3 test infrastructure

The remaining component suites now use Vue Test Utils 2: `props`, per-mount
`global` plugins/mocks/stubs, component wrappers, wrapper arrays, and `unmount`.
They no longer use `Vue.use`, `createLocalVue`, prototype mutation, `propsData`,
`wrapper.destroy`, or private Vuetify 2 imports. Async checks use `nextTick` and
`flushPromises`; polling tests use fake timers with teardown on assertion failure.

`frontend/tests/helpers/mount.js` provides fresh Vuetify instances, optional
memory routers, attached DOM hosts, and cleanup. It preserves caller plugins,
mocks, components, and stubs. Its three tests verify isolation, slot behavior,
navigation, and cleanup. For example, from a component test:

```js
import { mountWithVuetify, cleanupMounts } from "../../helpers/mount";

afterEach(cleanupMounts);

const wrapper = mountWithVuetify(MyComponent, {
  props: { value: initialValue },
  global: { mocks: { $enableUnloadConfirmation: jest.fn() } },
});
```

Use `shallowMountWithVuetify` for isolated logic and opt into
`global.renderStubDefaultSlot: true` only when assertions need slot content.
Use real controls for input, validation, and interaction checks. The helper
registers feature Vuetify components for isolated tests; production registration
still belongs to each feature migration. A passing isolated test therefore does
not prove that the production application registers the component.

Tests drive Vuetify 3 controls through their current model events. Custom
components retain their existing `value`/`input` assertions until those public
contracts are migrated in steps 5–6. The notifications suite uses actual async
form validation and now checks that an invalid URL cannot be submitted.
New unmount checks expose outstanding polling and late-response cleanup defects.
No failing tests are skipped or Vue warnings suppressed.

Run from `frontend` with Node 24:

```sh
npm run lint:tests
npm run test:unit -- --runInBand
```

Verification: test/configuration lint passes. All 29 suites execute: **18 pass
and 11 fail; 147 of 193 tests pass and 46 fail**. Startup and foundation tests
remain green. More tests execute than at step 3 because legacy mounting errors
previously prevented whole suites from loading. The remaining failures are
tracked below; the full suite is intentionally still red until component work
is complete.

| Suite | Failing tests | Component migration follow-up |
| --- | ---: | --- |
| `ClusterEditor` | 16 | Step 6: replace removed `$set` calls, then verify editor flows |
| `AWSClusterEditor` | 3 | Step 6: replace `$set`, repair storage updates and zone selection |
| `DefaultProject` | 8 | Step 6: editor `$set` dependency and table selection events |
| `MigProfilesEditor` | 7 | Steps 5–6: Vuetify model bindings, emitted updates, validation |
| `InstanceSettings` | 3 | Step 6: size/volume controls and nested MIG bindings |
| `ProjectNotifications` | 1 | Step 5: await form validation and inspect its `valid` result before saving |
| `AWSProjectPrice` | 1 | Step 5: nested credentials model contract |
| `OpenStackSubnet` | 2 | Step 5: select `itemTitle` and model binding |
| `OpenStackCloud` | 2 | Step 5: select `itemTitle` and nested credentials model contract |
| `Benchmarks` | 2 | Step 6: unmount cleanup for polling and pending responses |
| `ClusterDisplay` | 1 | Step 6: unmount cleanup for status polling |

Fix production behavior alongside the affected tests in the next steps. In
particular, do not restore legacy Vuetify events in tests or stub validation as
always successful to make these checks pass. Additional defects may become
visible after the current blocking failures are fixed. The ordinary production
build and browser feature workflows still require the remaining migration.

## Step 5: shared UI components

The components in `src/components/ui` now use Vue 3 model contracts and Vuetify 3
controls. Custom input and dialog models use `modelValue` and
`update:modelValue`, with explicit event declarations. Their existing parent
`v-model` bindings work with this contract; the explicit nested OpenStack subnet
binding and affected tests were updated together. Components retain the Options
API. Cluster settings and MIG controls remain step 6.

Implemented behavior:

- Confirmation and message dialogs propagate model updates. Project dialog and
  tooltip activators use `mergeProps` to preserve both sets of handlers.
- Membership uses current list slots and checkboxes. Shared buttons, select
  labels, progress values, sizing, variants, and color classes use Vuetify 3 APIs.
- Credentials propagate through project creation/editing, preserving locked AWS
  regions, stored credentials, and saved OpenStack subnets. Discovery ignores
  superseded requests and responses arriving after unmount.
- Notifications await the form's validation result before submitting, reject
  invalid webhook URLs, and block duplicate saves while validation or submission
  is pending. Existing token preservation/removal behavior remains covered.
- Public-key paste/upload emits normalized key lists while retaining a trailing
  newline in the editable text. Hieradata updates preserve encrypted write-only
  values and do not mutate the supplied entries.
- CodeEditor wraps the public `VInput` component instead of extending Vuetify 2
  internals. YAML validation participates in `VForm`; ordinary text is accepted.
  Monaco uses an element ref, handles parent updates before initialization,
  avoids creating an editor after unmount, reports loading failures, and disposes
  subscriptions, its editor, and its model on unmount.

The production Vuetify plugin explicitly registers shared UI controls. Its
exported `appComponents` registry lets the general test helper add only missing
feature components, avoiding duplicate-registration warnings. New integration
suites use the production plugin directly and assert that no Vue warnings occur.
They cover actual dialogs, nested credentials, role changes, inputs, and form
validation. Monaco lifecycle tests mock its browser API; the browser check below
also exercises a real editor.

Run from `frontend` with Node 24:

```sh
npm run test:shared
npm run lint:shared
npm run test:startup
npm run lint:tests
npm run test:unit -- --runInBand
```

Verification on Node 24.21.0:

- Shared UI: **13 suites and 61 tests pass**.
- Shared source, plugin, helper, test, and Jest/ESLint configuration lint passes.
- Full suite: **25 of 32 suites pass; 170 of 210 tests pass**. Startup, foundation,
  and helper tests remain green. No failing feature tests were skipped.
- Headless Chrome against an isolated page using the actual shared components
  and production Vuetify plugin passed OpenStack registration, locked AWS region
  editing, membership roles, notification validation, confirmation cancellation
  and reopening, public-key paste/upload, encrypted hieradata updates, and Monaco
  validation/remounting. There were no runtime errors or console warnings. API
  responses were intercepted; no real projects or notifications were changed.
- The isolated page's production build passes with webpack size/performance
  warnings and the existing `Repository.js` console lint warning. Its temporary
  entry/configuration and browser tooling are not
  application dependencies. The harness supplies the installed Monaco module to
  its loader; it does not validate the loader's default external CDN delivery.

The remaining **40 failures in seven suites** belong to step 6:

| Suite | Failing tests | Remaining work |
| --- | ---: | --- |
| `ClusterEditor` | 16 | Replace `$set` and migrate editor flows |
| `AWSClusterEditor` | 3 | Editor `$set`, storage updates, and zone selection |
| `DefaultProject` | 8 | Editor dependency and table selection events |
| `MigProfilesEditor` | 7 | Model bindings, emitted updates, and validation |
| `InstanceSettings` | 3 | Size/volume controls and nested MIG bindings |
| `Benchmarks` | 2 | Polling and pending-response cleanup on unmount |
| `ClusterDisplay` | 1 | Status-polling cleanup on unmount |

Some older shallow tests still produce jsdom warnings when their generated
Vuetify stubs receive the read-only DOM `prefix` property. These are separate
from the warning-free production-plugin integration and browser checks. The
ordinary application build and full feature workflows remain blocked by the
unfinished step-6 migration; the isolated build is not release validation.

## Step 6.1: instance settings, MIG profiles, and type selection

`InstanceSettings`, `MigProfilesEditor`, and `TypeSelect` now use current Vue 3
and Vuetify 3 model bindings. Instance settings expose the named model
`v-model:instance` and emit a replacement object instead of mutating their prop.
The cluster editor receives that replacement in `localSpecs.instances[id]`;
its associated invalid-state listener uses direct assignment. The rest of the
cluster editor remains step 6.2.

Numeric overrides retain number conversion, clearing removes optional keys,
and boolean false, numeric zero, and list values are preserved. Nested MIG
validation participates in the real form, retains the last valid configuration
while an edit is invalid, and clears the optional map when all rows are removed.
The type selector uses current item slots, preserves grouped descriptions and
AWS price ordering, and prevents selecting unavailable types. Group headings
and dividers are not selectable options.

The production Vuetify plugin now registers the combobox, sheet, and linear
progress components. `InstanceControls.spec.js` exercises parent model updates,
actual form validation, and real type menus using only the production plugin,
with no Vue warnings. Quantity tests explicitly select the Quantity control;
Vuetify 3 comboboxes also contain a text-field component and must not be mistaken
for the quantity input.

Verification on Node 24.21.0:

- Four focused suites pass: **20 tests**, including the ten previously failing
  MIG and instance-settings cases.
- Lint passes for the three migrated controls, plugin, and four focused suites.
- Full suite: **28 of 33 suites pass; 185 of 214 tests pass**. The caller's
  invalid-state fix also resolves one AWS editor failure.
- The remaining **29 failures** are in `ClusterEditor` (16), `AWSClusterEditor`
  (2), `DefaultProject` (8), `Benchmarks` (2), and `ClusterDisplay` (1). They remain
  active for the subsequent step-6 tasks. Full application build/browser
  validation remains pending those migrations.

Run the focused checks from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/cluster/InstanceControls.spec.js tests/unit/components/cluster/InstanceSettings.spec.js tests/unit/components/cluster/MigProfilesEditor.spec.js tests/unit/components/cluster/TypeSelect.spec.js
```

## Step 6.2: main cluster editor

`ClusterEditor` now uses Vuetify 3 control bindings, menu/chip/list-group slots,
and explicit layout rows. Project selection refreshes provider resources and
updates the displayed project name. AWS image options use current select titles.
Instance and volume additions/removals use ordinary reactive assignment and
deletion; instance renaming/removal also clears obsolete validation state.
Volume names and tags propagate to the specification while existing stateful
volume restrictions remain in place.

The expiration picker bridges local calendar `Date` values to the API's
`YYYY-MM-DD` string, closes after selection, supports clearing, and validates
future dates. Apply and rebuild await form validation before emitting an action;
duplicate submissions are blocked while validation is pending. The old
render-triggered validation hook was removed. Numeric volume rules accept the
input representation while specifications retain numeric values.

Vue 3 unmount cleanup cancels AWS checks, invalidates pending resource and
feasibility responses, and releases unload protection. Initial project/user
loading handles errors and does not update an unmounted editor. The exposed
resource-loading promise settles on failures while the editor presents its
retry message. Dirty-state comparisons include the actual cloud object.

Verification on Node 24.21.0:

- `ClusterEditor`, `AWSClusterEditor`, and the new production-plugin
  `ClusterEditorIntegration` suites pass: **34 tests**. They cover real control
  edits, validated submission, date conversion, project/resource switching,
  stale responses, unload protection, and AWS cleanup, alongside the existing
  quota/default/zone checks.
- Scoped lint for the editor, plugin, and changed tests passes.
- Full suite: **31 of 34 suites pass; 216 of 220 tests pass**.
- The four remaining failures are the Projects default checkbox (step 6.4),
  cluster-display polling cleanup (step 6.3), and benchmark polling/late-response
  cleanup (step 6.6). No tests were skipped. Full application build and browser
  workflow validation remain part of the later step-6 integration tasks.

Run the focused suites from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/cluster/ClusterEditor.spec.js tests/unit/components/cluster/AWSClusterEditor.spec.js tests/unit/components/cluster/ClusterEditorIntegration.spec.js
```

## Step 6.3: cluster lists, details, resources, and failures

`ClustersList` now uses Vuetify 3 table headers, hostname row identity, and the
expanded-row slot. Clicking a row or its expansion button opens one overview at
a time. Expansion survives refreshed objects with the same hostname and closes
when the cluster disappears. Action buttons and links do not toggle the row;
teardown navigation still requests confirmation on the cluster detail screen.
The scoped row styling targets the current table DOM.

List polling prevents overlapping requests, preserves existing rows on failure,
shows a retry message, and recovers on the next poll. Both the list and detail
view stop polling on unmount and ignore late responses. Detail-view plan-wait
timers are cancelled as well, preventing further polling or actions after the
screen is abandoned. `ModifyCluster` keys its detail component by hostname so
navigation between clusters resets the component and cleans up the previous one.

`ClusterDisplay` uses the current card loader and progress model. Its capacity
plan field uses direct reactive assignment. `ClusterResources` uses current list
slots and reports progress immediately as well as after nested resource updates;
it continues to hide no-op resources. `ClusterFailure` uses current alert/button
variants and declares its retry event. The production plugin registers the table
and toolbar components used by the list.

Validation covers real table expansion/navigation, refresh and error handling,
late responses, resource rendering/progress, and real teardown confirmation and
cancellation dialogs. Existing service-health and retained-cluster lifecycle
checks remain active. Full application browser/build validation remains pending
the later step-6 integration tasks.

Verification on Node 24.21.0: **38 focused tests pass** across five suites, and
scoped lint passes. The full suite has **226 passing tests out of 229**, with
34 of 36 suites passing. The three remaining failures are the Projects default
checkbox (step 6.4) and benchmark polling/late-response cleanup (step 6.6).

Run the focused suites from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/cluster/ClustersList.spec.js tests/unit/components/cluster/ClusterDisplay.spec.js tests/unit/components/cluster/ClusterResources.spec.js tests/unit/components/cluster/ClusterFailure.spec.js tests/unit/components/cluster/ClusterLifecycle.spec.js
```

## Step 6.4: Projects screen

`Projects` now uses Vuetify 3 table headers, project-ID row identity, checkbox
controls, and button variants. Default selection uses the actual row ID and
supports mouse, Space, and Enter activation. The checkbox displays the confirmed
preference until the save succeeds, stays selected when clicked again, and
preserves the previous selection on failure. Controls are disabled during saves.

Successful project edits now emit `saved` and refresh the screen, matching
creation and membership changes. Existing edit, membership, notification, and
delete permissions remain in place. Delete failures display an error and retain
the rows; successful deletion refreshes the list and preference.

The screen integration suite mounts real dialogs with the production Vuetify
plugin. It covers table columns and permissions, nested creation/editing forms,
membership updates, notification destinations, refreshes, deletion errors, failed
edits, and default selection failures/retries. The existing default-project and
cluster-editor tests now use native checkbox interactions.

Verification on Node 24.21.0: **235 of 237 tests pass**, across 36 of 37 suites.
All Projects, default-project, and shared UI tests pass; scoped lint also passes.
The two remaining failures are the previously recorded benchmark polling and
late-response cleanup cases (step 6.6). Full application build and browser
workflow validation remain part of later integration work.

Run the focused suites from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/Projects.spec.js tests/unit/components/cluster/DefaultProject.spec.js tests/unit/components/ui
```

## Step 6.5: Usage and Capacity Planner

`Usage` now uses current project labels, table headers and row identity,
descending monthly sorting, progress values, alert variants, and pagination
events. History pagination requests the selected server page with the current
project ID and UTC date strings. The production plugin registers `VPagination`
and `VCardSubtitle`. Admin access checks remain in place; superseded requests
and responses arriving after unmount cannot replace report data.

`CapacityPlanner` now uses current project-selection events, table headers,
resource slots, row identity, button variants, and shortage styling. Resource
metadata separates the API resource name from the table column key, preserving
numeric sorting for GPU counts, RAM in GiB, and AWS quota pools. Editing,
previewing, saving, and cancellation retain their existing API contracts and
permission-controlled actions.

The real editor tests exposed a cross-field validation issue: entering the end
date did not clear the start field's previous period error. Both fields now
revalidate when the period's validity changes. Project changes reset the form
and cancellation dialog; late template, report, preview, edit, save, and cancel
responses cannot overwrite the new context or restart work after unmount.

Verification on Node 24.21.0: **27 focused tests pass** across three suites,
including 13 integration tests using the production plugin, real cluster editor,
and real confirmation dialog. Scoped lint passes. The full suite has **248 of
250 tests passing**, across 37 of 38 suites. Only the two previously recorded
benchmark polling/late-response cleanup failures remain for step 6.6. Full
application build and browser workflow validation remain later integration work.

Run the focused suites from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/Usage.spec.js tests/unit/components/CapacityPlanner.spec.js tests/unit/components/ReportingIntegration.spec.js
```

## Step 6.6: benchmark dashboard and editor

`Benchmarks` now uses current project/benchmark selection events, comparison
labels, table headers, run-ID row identity, descending requested-time sorting,
and the expanded-row slot. Expanded runs render diagnostics and saved
specifications inside a full table row. Alert, button, and chip variants use
Vuetify 3 APIs. Project and archived filters retain only visible selections;
comparison groups continue to separate commits and success criteria without
removing runs from history.

Polling uses `beforeUnmount`, prevents overlapping list refreshes, and does not
start a timer if the initial request completes after navigation. Report requests
ignore superseded responses and errors. Actions prevent duplicate submissions,
refresh after any existing poll completes, and do not restart work after unmount.

`BenchmarkEditor` uses current success-criterion labels and alert variants. It
preserves existing identity restrictions and retries a partially created
benchmark with its saved ID. Loading and saving ignore responses after unmount,
including navigation following a successful save. Users without an administered
project do not load a template. Missing next-run timestamps display as empty.

Verification on Node 24.21.0: **21 focused tests pass** across two suites,
including six integration tests using the production plugin and real cluster
editor. Coverage includes history expansion, comparison/filter controls,
run/pause/archive actions, editor payloads, first-save retry, polling recovery,
stale responses, and unmount cleanup. Scoped lint passes. The full suite now
passes **all 261 tests across 39 suites**; no tests are skipped. Full application
build and browser workflow validation remain later integration work.

Run the focused suites from `frontend`:

```sh
npm run test:unit -- --runInBand tests/unit/components/Benchmarks.spec.js tests/unit/components/BenchmarkIntegration.spec.js
```

## Step 6.7: application integration and demo retirement

Added `npm run test:browser` with a pinned Playwright development dependency.
The check exercises the real production entry, router, shell, and feature screens
against intercepted API responses: cluster creation fields and nested puppet
configuration, Projects navigation/default selection/dialogs, planner date
inputs, benchmark history expansion and editor save/navigation, Usage pagination,
cluster-edit deep links, benchmark access denial, direct reloads, and not-found
routing. It asserts no browser errors or console warnings.

The temporary foundation entry, components, router, plugin, environment modes,
package scripts, and demonstration test are removed. Existing build/test tooling
and the real application tests remain. The full lint check's remaining formatting
warning in `ClustersList.spec.js` is fixed.

Verification on Node 24.21.0:

- Production build passes. Existing webpack bundle-size/performance advisories
  remain; this step does not claim a bundle-size improvement.
- Full lint passes with no errors or warnings.
- All **260 unit/component tests across 38 suites pass**, with none skipped.
  The count is one lower because the replaced demonstration test was removed.
- Production browser smoke passes in headless Chrome with mocked APIs.

Some shallow component tests still log the known Vue Test Utils `prefix`
attribute warning on generated select stubs; the real-screen integration tests
and browser smoke check do not emit it. Docker/CI execution, live-backend workflows,
external font rendering, and release/support validation remain separate work.

## Step 6.8: run completion checks and document the result

Completion checks rerun on September 27, 2026, on
`migration/vue3-foundation`, using Node 24.21.0 and npm 11.19.0.
This step changes documentation only; CI and Docker configuration are unchanged.

| Check | Result |
| --- | --- |
| `npm run test:unit -- --runInBand` | 260/260 tests pass across 38 suites; zero failed or skipped tests |
| `npm run lint -- --no-fix` | Pass, no lint errors or warnings in this command |
| `npm run lint -- --no-fix tests/browser/smoke.cjs` | Pass, no lint errors or warnings |
| `npm run build` | Pass; production artifacts generated in `frontend/dist` |
| `npm run test:browser` against that build | Pass in headless Chrome; zero browser errors or console warnings |
| `npm ls vue @vue/compiler-sfc vue-router vuetify --depth=0` | Vue/compiler 3.5.43, Router 4.6.4, Vuetify 3.13.5; no dependency errors |
| Legacy API scan of `frontend/src` | No matches for the checked migration patterns listed below |
| `git diff --check` | Pass |

The source scan checked `beforeDestroy`, `destroyed` hooks, `$set`, `$delete`,
`.sync`, `item-text`, `item-key`, `expanded-item`, `v-simple-checkbox`,
`v-list-item-content`, and `v-list-item-action`. This is a targeted audit, not a
claim that static scanning proves every runtime behavior.

The browser check covers real routed frontend workflows with mocked APIs:
cluster creation and nested configuration, project defaults/dialogs, planner
dates, benchmark history/edit/save, Usage pagination, cluster-edit deep links,
access denial, reloads, and not-found routing. It does not provision cloud
resources or verify a live backend or identity provider.

Remaining non-failing output:

- Shallow component tests log Vue Test Utils `prefix` attribute warnings on
  generated select/text-field stubs. Real-screen/browser checks emit none.
- Production builds enable the environment-dependent `no-console` rule and
  report eight warnings: two in `ClusterDisplay`, five in `ClusterEditor`, and
  one in `Repository`. The standalone lint command runs without that production
  setting, explaining its clean result.
- Webpack reports asset/entrypoint size and runtime-chunk advisories. The initial
  entry is approximately 1.11 MiB uncompressed. Performance optimization is not
  part of these completion checks.

**Result:** the step-6 frontend completion checks pass. All migration changes
remain uncommitted. Docker validation of the final configuration, remote CI,
live-backend workflows, and release approval remain separate work. An exploratory
Docker build used temporary edits that were reverted; it is not counted as
validation of the final Docker configuration.

## Step 7.1: reproducible dependency installation and clean builds

The Docker frontend stage now copies `package.json` and `package-lock.json`,
runs `npm ci`, then copies the frontend sources and builds. Source-only changes
can reuse the dependency layer. The build context excludes Git metadata, local
Python environments/caches, frontend coverage/browser output, and local frontend
environment overrides in addition to the existing `node_modules` and `dist`
exclusions. Checked-in environment modes remain available as build inputs.

Validation on September 28, 2026, used Node **24.21.0** and npm **11.19.0**:

- Copied the current frontend source snapshot, including uncommitted migration
  changes, into an isolated directory with no dependencies or generated output.
  This validates the current working tree rather than the older committed HEAD.
- Ran a fresh `npm ci`, followed by `npm run build`: both pass.
- Ran the full unit/component suite in that clean installation: **262 tests pass
  across 38 suites**, with zero failed or skipped tests.
- Built the Docker `frontend-build-stage` with `--no-cache`: installation and
  production compilation pass. The resulting image contains `dist/index.html`.
- Confirmed Vue/compiler **3.5.43**, Router **4.6.4**, and Vuetify **3.13.5** in
  the image. Both local and container builds used the same Node/npm versions.
- Confirmed the workspace, clean-install directory, and image lockfiles match
  the pre-install SHA-256:
  `b71b80b746385672ed4624320a8ab0d9746dcb3479b545a4817e408d6234fe79`.

The local validation image is `mc-hub:vue3-frontend-step71`, image ID
`sha256:71d966dd7e8c22ea311ac09f219eaaa87605d131f637880494c24a967ee38dce`.
It was not published. Reproduce the Docker check from the repository root:

```sh
DOCKER_BUILDKIT=1 docker build --no-cache --target frontend-build-stage \
  --tag mc-hub:vue3-frontend-step71 .
```

Existing build/test warnings remain non-failing. Installation reported 29
advisories (10 low, 13 moderate, 6 high), deprecated transitive packages, and
npm install-script policy notices; dependency remediation belongs to step 7.5.
No lockfile regeneration or forced dependency upgrade was used in this step.

This establishes locked dependency installation and successful clean builds,
not byte-identical output: Node/base-image tags are not pinned to immutable
image digests. Final production-container startup and backend integration remain
step 7.3; remote CI configuration and execution remain step 7.2.

## Step 7.2: CI completion checks

The GitHub Actions workflow now validates pushes and pull requests. The frontend
job selects Node 24 from `frontend/.nvmrc`, caches npm downloads using the lockfile,
and runs these checks in order:

1. `npm ci`
2. `npm run lint -- --no-fix` and `npx eslint tests/browser/smoke.cjs`
3. `npm run test:unit -- --runInBand`
4. `npm run build`
5. `npx playwright install --with-deps chromium`
6. `npm run test:browser`

The browser check serves the generated production build and mocks API requests;
it needs no backend credentials. Explicit linting includes the `.cjs` browser
script. The frontend job has a 20-minute timeout. The container job now depends
on successful frontend and backend jobs, so release-tag image publishing cannot
run ahead of validation. Existing release-tag conditions remain in place.

Local validation on September 28, 2026:

- `actionlint` 1.7.11: workflow passes validation.
- Frontend lint and explicit browser-script lint: pass.
- Full unit/component suite: **262 tests pass across 38 suites**.
- Production build: pass, with the previously documented non-failing warnings.
- Production browser smoke check: pass with Playwright's downloaded Chromium,
  with no browser errors or warnings and no `CHROME_PATH` override.
- `git diff --check`: pass. Clean `npm ci` was verified in step 7.1 with the same
  dependency manifests; this step does not modify them.

**Status:** CI configuration and local checks are complete; the remote-run
acceptance check remains pending. GitHub CLI returned `HTTP 401: Bad credentials`
when checking the migration branch. These local checks ran on macOS; they do not
establish that the Ubuntu runner or its browser system-dependency installation
passes. Migration changes remain uncommitted and unpublished. After restoring
GitHub authentication and committing/pushing the migration, verify that the
workflow for that exact commit passes both frontend and backend jobs before
marking remote CI complete. A successful run of an older commit is insufficient.

## Next contributions

- [x] Step 3: migrate the real entry point, router, unload-confirmation plugin,
  Vuetify plugin, benchmark-access state, and shell.
- [x] Step 4: migrate legacy test mounting, props, mocks, and teardown APIs;
  document active component failures for steps 5–6.
- [x] Step 5: migrate shared UI components, model contracts, forms, and editors.
- [x] Step 6.1: migrate instance settings, MIG profiles, and type selection.
- [x] Step 6.2: migrate the main cluster editor and its AWS flows.
- [x] Step 6.3: migrate cluster lists, details, resource progress, and cleanup.
- [x] Step 6.4: migrate Projects, default selection, and dialog integration.
- [x] Step 6.5: migrate Usage and Capacity Planner screens and interactions.
- [x] Step 6.6: migrate benchmark dashboard, editor, and request cleanup.
- [x] Step 6.7: validate production frontend integration and retire the demo.
- [x] Step 6.8: run completion checks and document the result.
- [x] Step 6: migrate feature screens and cluster controls with their tests.
- [x] Replace the demonstration with checks of real application workflows once
  the application boots; then remove its entry, modes, scripts, and temporary
  components while retaining useful test/tooling configuration.
- [x] Step 7.1: verify clean dependency installation and frontend builds.
- [x] Step 7.2: configure CI completion checks and validate them locally.
- [ ] Step 7.2: verify a successful remote CI run on the migration commit.
- [ ] Validate the full build, suite, Docker image, CI, and Vuetify support target
  before merging the migration into the release branch.
- [ ] Migrate from Vue CLI to Vite as a separate tooling contribution.
