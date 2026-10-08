<template>
  <div>
    <div v-if="suggestionsUnavailable" class="text-body-2 text-grey mb-2" role="status">
      Key suggestions are unavailable for this version. You can still enter a key.
    </div>
    <div v-if="localEntries.length === 0" class="text-body-2 text-grey mb-2">
      No entries. Click "Add entry" to add puppet configuration variables.
    </div>
    <div v-for="(entry, index) in localEntries" :key="index" class="mb-3">
      <div class="d-flex align-center">
        <v-tooltip
          :disabled="!parameterDetails[entry.key]?.description"
          location="top"
          max-width="420"
          :open-delay="200"
        >
          <template #activator="{ props }">
            <v-combobox
              v-bind="props"
              v-model="entry.key"
              :items="puppetConfigurationKeys.map((parameter) => parameter.key)"
              :loading="loadingSuggestions"
              :return-object="false"
              label="Key"
              placeholder="Select or enter a key"
              density="compact"
              variant="outlined"
              hide-details
              class="mr-2"
              style="max-width: 260px; flex-shrink: 0"
              @update:model-value="emit"
            />
          </template>
          <span>{{ parameterDetails[entry.key]?.description }}</span>
        </v-tooltip>
        <v-tooltip :disabled="!parameterDetails[entry.key]?.type" location="top" max-width="420" :open-delay="200">
          <template #activator="{ props }">
            <div v-bind="props" class="mr-2 flex-grow-1" style="min-width: 0">
              <v-text-field
                v-if="isWriteOnly(entry)"
                placeholder="Encrypted (write-only)"
                label="Value"
                density="compact"
                variant="outlined"
                hide-details
                disabled
              />
              <v-text-field
                v-else
                :model-value="inlineValue(entry)"
                :readonly="String(entry.value ?? '').includes('\n')"
                :rules="requireEncryptedValues && entry.encrypt ? [requiredValue] : []"
                label="Value"
                density="compact"
                variant="outlined"
                hide-details
                @update:model-value="updateInlineValue(index, $event)"
              />
            </div>
          </template>
          <span>Type: {{ parameterDetails[entry.key]?.type }}</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon
              size="small"
              variant="text"
              class="mr-1"
              aria-label="Expand value editor"
              @click="openValueEditor(index)"
            >
              <v-icon>mdi-arrow-expand-all</v-icon>
            </v-btn>
          </template>
          <span>Edit multiline value</span>
        </v-tooltip>
        <v-tooltip v-if="isWriteOnly(entry)" location="bottom">
          <template #activator="{ props }">
            <v-btn icon size="small" class="mr-1" v-bind="props" @click="enableEdit(index)">
              <v-icon size="small">mdi-pencil</v-icon>
            </v-btn>
          </template>
          <span>Set new value</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon
              size="small"
              variant="text"
              :color="entry.encrypt ? 'primary' : 'grey'"
              :aria-pressed="!!entry.encrypt"
              aria-label="Encrypt value"
              class="mr-1 flex-shrink-0"
              @click="toggleEncryption(index)"
            >
              <v-icon>mdi-shield-key-outline</v-icon>
            </v-btn>
          </template>
          <span>{{
            entry.encrypt ? "Encryption enabled — click to disable" : "Encryption disabled — click to enable"
          }}</span>
        </v-tooltip>
        <v-btn icon size="small" variant="text" color="error" class="mr-1" @click="removeEntry(index)">
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </div>
    </div>
    <v-btn size="small" variant="text" color="primary" class="mt-1 pl-0" @click="addEntry">
      <v-icon start size="small">mdi-plus</v-icon>
      Add entry
    </v-btn>
    <v-dialog :model-value="valueEditorIndex !== null" max-width="800" @update:model-value="closeValueEditor">
      <v-card v-if="valueEditorIndex !== null">
        <v-card-title>Edit value</v-card-title>
        <v-card-text>
          <div class="text-subtitle-2 mb-2" style="overflow-wrap: anywhere">
            {{ localEntries[valueEditorIndex].key || "New parameter" }}
          </div>
          <p v-if="parameterDetails[localEntries[valueEditorIndex].key]?.description" class="mb-2">
            {{ parameterDetails[localEntries[valueEditorIndex].key].description }}
          </p>
          <div v-if="parameterDetails[localEntries[valueEditorIndex].key]?.type" class="text-body-2 mb-2">
            Type: {{ parameterDetails[localEntries[valueEditorIndex].key].type }}
          </div>
          <p class="text-body-2 mb-3">
            {{
              localEntries[valueEditorIndex].encrypt
                ? "This value will be encrypted as text. Existing encrypted values cannot be displayed; enter a replacement."
                : "Enter a YAML value, list, or map. For text with line breaks, use a YAML block starting with | and indent the following lines."
            }}
          </p>
          <v-textarea
            v-model="valueDraft"
            label="Value"
            variant="outlined"
            rows="12"
            autofocus
            spellcheck="false"
            class="expanded-value"
            hide-details
          />
          <v-alert v-if="valueEditorError" type="error" variant="tonal" density="compact" class="mt-3">
            {{ valueEditorError }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeValueEditor">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!!valueEditorError"
            @click="applyValueEditor"
            >Apply</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import cloneDeep from "lodash/cloneDeep";
import jsYaml from "js-yaml";
import { getPuppetConfigurationKeys } from "@/services/puppetConfigurationKeys";

export default {
  name: "HieradataEditor",
  emits: ["update:modelValue"],
  props: {
    version: { type: String, default: null },
    requireEncryptedValues: Boolean,
    modelValue: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      localEntries: [],
      puppetConfigurationKeys: [],
      loadingSuggestions: false,
      suggestionsUnavailable: false,
      suggestionsRequest: 0,
      valueEditorIndex: null,
      valueDraft: "",
    };
  },
  computed: {
    valueEditorError() {
      if (this.valueEditorIndex === null || this.localEntries[this.valueEditorIndex] == null) return "";
      if (this.localEntries[this.valueEditorIndex].encrypt && !String(this.valueDraft ?? "").trim()) {
        return "Enter a replacement encrypted value.";
      }
      try {
        jsYaml.load(String(this.valueDraft ?? ""));
        return "";
      } catch (error) {
        return `Enter valid YAML before applying: ${error.message}`;
      }
    },
    parameterDetails() {
      return Object.assign(
        Object.create(null),
        Object.fromEntries(this.puppetConfigurationKeys.map((parameter) => [parameter.key, parameter]))
      );
    },
  },
  watch: {
    version: {
      immediate: true,
      async handler(version) {
        const request = ++this.suggestionsRequest;
        this.puppetConfigurationKeys = [];
        this.suggestionsUnavailable = false;
        this.loadingSuggestions = !!version;
        if (!version) return;
        try {
          const keys = await getPuppetConfigurationKeys(version);
          if (request === this.suggestionsRequest) this.puppetConfigurationKeys = keys;
        } catch {
          if (request === this.suggestionsRequest) this.suggestionsUnavailable = true;
        } finally {
          if (request === this.suggestionsRequest) this.loadingSuggestions = false;
        }
      },
    },
    requireEncryptedValues: Boolean,
    modelValue: {
      handler(val) {
        this.closeValueEditor();
        this.localEntries = cloneDeep(val || []);
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    inlineValue(entry) {
      const value = String(entry.value ?? "");
      if (!value.includes("\n")) return entry.value;
      try {
        return JSON.stringify(jsYaml.load(value)) ?? JSON.stringify(value);
      } catch {
        // Invalid YAML is displayed as a JSON string so the inline preview stays valid JSON.
        return JSON.stringify(value);
      }
    },
    updateInlineValue(index, value) {
      if (String(this.localEntries[index].value ?? "").includes("\n")) return;
      this.localEntries[index].value = value;
      this.emit();
    },
    openValueEditor(index) {
      this.valueEditorIndex = index;
      this.valueDraft = String(this.localEntries[index].value ?? "");
    },
    closeValueEditor() {
      this.valueEditorIndex = null;
      this.valueDraft = "";
    },
    applyValueEditor() {
      if (this.valueEditorError) return;
      this.localEntries[this.valueEditorIndex].value = this.valueDraft;
      this.closeValueEditor();
      this.emit();
    },
    requiredValue(value) {
      return (value != null && String(value).trim().length > 0) || "Re-enter the encrypted value or remove this entry.";
    },
    isWriteOnly(entry) {
      return entry.encrypt && entry.value === null;
    },
    enableEdit(index) {
      this.localEntries[index].value = "";
      this.emit();
    },
    toggleEncryption(index) {
      this.localEntries[index].encrypt = !this.localEntries[index].encrypt;
      // If disabling encryption on a write-only entry, clear the preserved value.
      if (!this.localEntries[index].encrypt && this.localEntries[index].value === null) {
        this.localEntries[index].value = "";
      }
      this.emit();
    },
    addEntry() {
      this.localEntries.push({ key: "", value: "", encrypt: false });
      this.emit();
    },
    removeEntry(index) {
      this.localEntries.splice(index, 1);
      this.emit();
    },
    emit() {
      this.$emit("update:modelValue", cloneDeep(this.localEntries));
    },
  },
};
</script>

<style scoped>
.expanded-value :deep(textarea) {
  font-family: monospace;
  tab-size: 2;
}
</style>
