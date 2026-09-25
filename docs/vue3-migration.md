# Vue 3 migration foundation

Step 2 provides an isolated Vue 3 demonstration on `migration/vue3-foundation`.
The MC Hub application itself still needs the startup, component, and test
migrations in steps 3–6. This branch is not ready for a production release.

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

## Verification and remaining work

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

Next contributions:

- [ ] Step 3: migrate the real entry point, router, unload-confirmation plugin,
  Vuetify plugin, and benchmark-access state.
- [ ] Step 4: migrate legacy test mounting, props, mocks, and teardown APIs.
- [ ] Steps 5–6: migrate shared components and feature screens with their tests.
- [ ] Replace the demonstration with checks of real application workflows once
  the application boots; then remove its entry, modes, scripts, and temporary
  components while retaining useful test/tooling configuration.
- [ ] Validate the full build, suite, Docker image, CI, and Vuetify support target
  before merging the migration into the release branch.
- [ ] Migrate from Vue CLI to Vite as a separate tooling contribution.
