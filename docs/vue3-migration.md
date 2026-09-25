# Vue 3 migration foundation

Steps 2–4 are implemented on `migration/vue3-foundation`: the dependency
foundation, real application startup, router, shared state, plugins, shell, and
Vue 3 test infrastructure. Shared components and feature screens still need
steps 5–6; their behavioral tests remain active and expose migration blockers.
This branch is not ready for a production release.

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

## Run the foundation

From the repository root, with Node 24 available:

```sh
cd frontend
# If using nvm: nvm install && nvm use
npm ci
npm run test:foundation
npm run lint:foundation
npm run build:foundation
npm run serve:foundation
```

`frontend/.nvmrc` selects Node 24. The development command prints its local URL.
It uses `.env.vue3-foundation-development`, explicitly selecting development
mode. The build uses `.env.vue3-foundation`, explicitly selecting production
mode, and writes to `frontend/dist/vue3-foundation`.

The foundation flag selects an alternate page entry in `vue.config.js`. It uses
the same webpack, Babel, Monaco, HTML template, public assets, and source alias
configuration as the application. The normal `serve`, `build`, and `test:unit`
commands still target the application or complete suite; they are not redirected
to the demonstration. A normal build cleans `dist`, including the demonstration
output, so rebuild the foundation afterward if necessary.

Serve the production output at the root of an HTTP server with SPA fallback to
`index.html` for `/about`. Do not open its HTML through a `file://` URL. For example,
if a `serve` static-server CLI is available:

```sh
serve -s dist/vue3-foundation
```

In both development and production:

1. Enter a name and confirm the greeting updates.
2. Click the counter button and confirm it increments.
3. Confirm controls are styled and the check icon appears.
4. Navigate to About and confirm the lazy-loaded page appears.
5. Reload `/about` directly, then navigate Home.
6. Check for runtime errors, unresolved components, or Vue warnings.

## Implementation conventions

- `src/foundation/main.js` registers a fresh router and Vuetify instance with
  `createApp`. It deliberately does not import the unmigrated `App.vue`.
- Components retain the Options API. Composition API and TypeScript conversion
  are not required for the upgrade.
- Vuetify components and directives are imported explicitly through supported
  public subpaths. No automatic-import webpack plugin is needed for this proof.
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

## Next contributions

- [x] Step 3: migrate the real entry point, router, unload-confirmation plugin,
  Vuetify plugin, benchmark-access state, and shell.
- [x] Step 4: migrate legacy test mounting, props, mocks, and teardown APIs;
  document active component failures for steps 5–6.
- [ ] Steps 5–6: migrate shared components and feature screens with their tests.
- [ ] Replace the demonstration with checks of real application workflows once
  the application boots; then remove its entry, modes, scripts, and temporary
  components while retaining useful test/tooling configuration.
- [ ] Validate the full build, suite, Docker image, CI, and Vuetify support target
  before merging the migration into the release branch.
- [ ] Migrate from Vue CLI to Vite as a separate tooling contribution.
