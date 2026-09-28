import { mount, flushPromises } from "@vue/test-utils";
import { createAppVuetify } from "@/plugins/vuetify";
import CodeEditor from "@/components/ui/CodeEditor";
import loader from "@monaco-editor/loader";
import { version as monacoVersion } from "monaco-editor/package.json";

jest.mock("@monaco-editor/loader", () => ({ init: jest.fn(), config: jest.fn() }));
let wrappers, monaco, editors, warn;
beforeEach(() => {
  wrappers = [];
  editors = [];
  warn = jest.spyOn(console, "warn");
  monaco = {
    editor: {
      defineTheme: jest.fn(),
      setModelLanguage: jest.fn(),
      create: jest.fn((host, options) => {
        let value = options.value;
        const model = { dispose: jest.fn() };
        const editor = {
          host,
          model,
          dispose: jest.fn(),
          getModel: () => model,
          getValue: () => value,
          setValue: jest.fn((next) => {
            value = next;
            editor.change?.();
          }),
          onDidChangeModelContent: jest.fn((callback) => {
            editor.change = callback;
            return { dispose: jest.fn() };
          }),
          onDidBlurEditorText: jest.fn((callback) => {
            editor.blur = callback;
            return { dispose: jest.fn() };
          }),
        };
        editors.push(editor);
        return editor;
      }),
    },
  };
  loader.init.mockResolvedValue(monaco);
});
afterEach(() => {
  wrappers.forEach((wrapper) => {
    if (wrapper.exists()) wrapper.unmount();
  });
  expect(warn).not.toHaveBeenCalled();
  jest.restoreAllMocks();
});
function render(props = {}) {
  const wrapper = mount(CodeEditor, { props, global: { plugins: [createAppVuetify()] } });
  wrappers.push(wrapper);
  return wrapper;
}

test("uses the latest parent value after initialization and distinct editor hosts", async () => {
  let resolve;
  loader.init.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const first = render({ modelValue: "old" });
  expect(loader.config).toHaveBeenCalledWith({
    paths: { vs: `https://cdn.jsdelivr.net/npm/monaco-editor@${monacoVersion}/min/vs` },
  });
  await first.setProps({ modelValue: "latest" });
  const second = render();
  resolve(monaco);
  await flushPromises();
  expect(editors[0].getValue()).toBe("latest");
  expect(editors[0].host).not.toBe(editors[1].host);
  await first.setProps({ modelValue: "parent" });
  expect(first.emitted("update:modelValue")).toBeUndefined();
  editors[0].setValue("typed");
  expect(first.emitted("update:modelValue")).toEqual([["typed"]]);
  expect(second.emitted("update:modelValue")).toBeUndefined();
});

test("participates in real form validation and supports non-YAML text", async () => {
  const wrapper = mount(
    {
      components: { CodeEditor },
      data: () => ({ value: "a: [" }),
      template: '<v-form ref="form"><code-editor v-model="value" language="yaml"/></v-form>',
    },
    { global: { plugins: [createAppVuetify()] } }
  );
  wrappers.push(wrapper);
  await flushPromises();
  expect((await wrapper.vm.$refs.form.validate()).valid).toBe(false);
  expect(wrapper.text()).toContain("Line");
  await wrapper.setData({ value: "a: 1" });
  expect((await wrapper.vm.$refs.form.validate()).valid).toBe(true);
  const plain = render({ modelValue: "a: [" });
  await flushPromises();
  expect(await plain.vm.validateCode()).toEqual([]);
});

test("disposes subscriptions, editor and model on unmount", async () => {
  const wrapper = render();
  await flushPromises();
  wrapper.unmount();
  const editor = editors[0];
  expect(editor.dispose).toHaveBeenCalledTimes(1);
  expect(editor.model.dispose).toHaveBeenCalledTimes(1);
  expect(editor.onDidChangeModelContent.mock.results[0].value.dispose).toHaveBeenCalledTimes(1);
  expect(editor.onDidBlurEditorText.mock.results[0].value.dispose).toHaveBeenCalledTimes(1);
});

test("does not create an editor if initialization finishes after unmount", async () => {
  let resolve;
  loader.init.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const wrapper = render();
  wrapper.unmount();
  resolve(monaco);
  await flushPromises();
  expect(monaco.editor.create).not.toHaveBeenCalled();
});

test("shows initialization failures without an unhandled rejection", async () => {
  loader.init.mockRejectedValue(new Error("offline"));
  const wrapper = render();
  await flushPromises();
  expect(wrapper.text()).toContain("Unable to load the code editor");
});
