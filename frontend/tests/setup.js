// Jest 27's jsdom does not implement CSS feature detection or layout observers.
// These shims allow real Vuetify inputs to mount; layout is checked in a browser.
global.CSS = { supports: () => false };
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
