# Vite tooling migration

The frontend now uses **Vite 8.3.1**, **@vitejs/plugin-vue 6.0.9**, standalone
**Jest 29.7.0 / @vue/vue3-jest 29.2.6**, and **ESLint 9.39.5**. Vue 3.5.43,
Router 4.6.4, and Vuetify 3.13.5 remain the application framework versions.
Jest 29 matches the Vue transformer's supported peer range and preserves the
existing test suite and command-line flags.

## Development and validation

Use Node 24 (`frontend/.nvmrc`), then:

```sh
cd frontend
npm ci
npm run serve                    # Vite at http://localhost:8080
npm run lint -- --no-fix
npm run test:unit -- --runInBand
npm run build                    # frontend/dist
npm audit
```

`npm run dev` is an alias for `serve`. `npm run preview` serves the production
build for local inspection; it is not a production application server. The
existing `test:shared`, `test:startup`, and scoped lint commands remain available.
Lint is now a separate, non-mutating ESLint command; Vite's build does not run
lint implicitly. The existing workflow's separate lint/test/build commands are
compatible without workflow edits. ESLint checks JavaScript and Vue rules;
Prettier configuration disables conflicting style rules rather than running
formatting through ESLint.

Development uses a same-origin `/api` proxy to `http://127.0.0.1:5000`. Optional
settings in `frontend/.env.local`:

```dotenv
# Server-side development proxy target; not an application credential.
VITE_API_PROXY_TARGET=http://127.0.0.1:5000
# Optional browser-visible API URL, when a separate origin is required:
# VITE_API_URL=https://backend.example.org/api
```

The existing `VUE_APP_API_URL` remains supported; `VITE_API_URL` takes precedence.
Only that selected public API URL and the root base path are substituted into
the existing `process.env` references. The whole process environment is not
injected. Cross-origin API URLs still require appropriate backend CORS settings.
Run the CLI from `frontend`, so its environment files and config resolve there.

## Packaging changes

- `frontend/index.html` is the Vite HTML entry, with a module script for
  `/src/main.js`. The Vue CLI public HTML template and Webpack config are removed.
- The `@` alias and extensionless `.vue` imports are supported. Router history
  remains rooted at `/`.
- JavaScript, including lazy route chunks, is emitted under `dist/js`; CSS under
  `dist/css`. Other emitted assets use `dist/js` too. These paths work with the
  existing Flask static routes, so no backend code changes are needed.
- The Docker build still uses `npm ci` and `npm run build`, and the final image
  still copies `dist` to `/code/frontend`. No Dockerfile edits were necessary.
- Vue CLI, its plugins, Webpack's Monaco plugin, sass-loader, and core-js are
  removed. Vite handles modern-browser compilation and Sass directly. Its default
  production target is Baseline Widely Available; the old Browserslist setting
  is removed because Vite does not use it as its compilation target.
- Monaco remains loaded from the pinned CDN version. Its version now comes from
  the application's exact package pin, avoiding an unsupported package-export
  lookup. The Webpack plugin was unused by that CDN loading path.
- Babel remains solely for Jest. Explicit Vue/JavaScript transforms and a CSS
  mock replace the CLI test preset. The cluster-list test uses lodash's deep
  clone because Jest's jsdom does not supply `structuredClone`.

## Validation on September 28, 2026

| Check | Result |
| --- | --- |
| Fresh `npm ci` using Node 24 | Pass, without force, overrides, or peer bypasses |
| Full ESLint check | Pass |
| Jest suite | **262 tests across 38 suites pass** |
| Vite production build | Pass; lazy routes retained |
| `npm audit` | **0 vulnerabilities**, including 0 high; previously 27 total / 6 high |
| Development HTTP checks | SPA/deep links, module requests, all 37 Vue component transforms, and `/api` proxy pass |
| Production Docker build/startup | Pass; schema migrates to 0023; non-root Gunicorn starts |
| Container HTTP checks | Ten SPA routes and all seven JS/CSS files pass, correct content types and bytes; missing JS/CSS return 404 |
| Container API/database checks | Four real JSON endpoints and SQLite integrity pass |

The production image is local-only `mc-hub:vite-validation`, ID
`sha256:f06084509746e40ca6ff4af66930d09d9fcbc0e7e6c7ab05d5f96b2dffa0e2be`.
It used a disposable database/configuration, no network, and no background
worker. The test container/database was removed afterward.

The initial migration's 647 kB main-chunk warning was resolved by the bundle
optimization below. Existing shallow-test `prefix` and missing `$route`
warnings remain test-harness debt. Optional native-package install-script notices
are distinct from security audit findings; no blanket script approval was added.

At the user's request, no Chromium/browser, SAML, live cluster build, or GitHub
operations were performed. Visual checks, browser runtime behavior, and remote
CI are still user-owned. A zero-advisory audit is a dated result, not a guarantee
against future advisories. Vuetify 3's support deadline remains July 27, 2027.

References: [Vite guide](https://vite.dev/guide/),
[Vite build configuration](https://vite.dev/config/build-options.html),
[Vue Jest compatibility](https://github.com/vuejs/vue-jest), and
[Vue ESLint flat configuration](https://eslint.vuejs.org/user-guide/).

## Initial bundle optimization

CreateCluster, ModifyCluster, and Projects now use lazy route imports. Their
screen code and shared editor dependencies load when those routes are visited.
Application Lodash imports now select individual functions (`cloneDeep`,
`isEqual`, and `capitalize`) instead of importing from the full package entry.
No dependency changes or manual vendor chunks were needed.

Production builds with `--manifest` were compared before and after. Initial
JavaScript includes the entry and its recursively resolved static imports;
deferred dynamic imports are excluded. Both builds have one initial JS file.
Sizes below use decimal kB; initial gzip values are Vite's reported values.

| Measurement | Before | After |
| --- | ---: | ---: |
| Initial JavaScript, minified | 647.13 kB | 467.45 kB |
| Initial JavaScript, gzip | 211.06 kB | 154.30 kB |
| All route JavaScript combined, minified | 689.18 kB | 639.57 kB |
| Largest JavaScript chunk | 647.13 kB | 467.45 kB |

Initial JavaScript decreased by **27.8%**; total JavaScript decreased by **7.2%**.
The production build no longer emits a chunk-size warning, with Vite's default
500 kB threshold unchanged. CSS/global Vuetify registration was not optimized
in this change. Loading another screen now requires its deferred chunks; these
measurements do not establish browser navigation latency or rendering speed.

Validation: production build, lint, whitespace checks, and **264 tests across
38 suites** pass. Route tests now await navigation to all three newly lazy
screens and verify their components resolve without invoking the benchmark
permission API. Browser/Chromium testing remains excluded at the user's request.
The earlier container image predates this bundle optimization.
