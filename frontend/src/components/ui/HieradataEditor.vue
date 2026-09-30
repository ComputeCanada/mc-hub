<template>
  <div>
    <div v-if="localEntries.length === 0" class="text-body-2 text-grey mb-2">
      No entries. Click "Add entry" to add puppet configuration variables.
    </div>
    <div v-for="(entry, index) in localEntries" :key="index" class="d-flex align-center mb-2">
      <v-text-field
        v-model="entry.key"
        label="Key"
        density="compact"
        variant="outlined"
        hide-details
        class="mr-2"
        style="max-width: 260px; flex-shrink: 0"
        @update:model-value="emit"
      />
      <template v-if="isWriteOnly(entry)">
        <v-text-field
          placeholder="Encrypted (write-only)"
          label="Value"
          density="compact"
          variant="outlined"
          hide-details
          disabled
          class="mr-2 flex-grow-1"
        />
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn icon size="small" class="mr-2" v-bind="props" @click="enableEdit(index)">
              <v-icon size="small">mdi-pencil</v-icon>
            </v-btn>
          </template>
          <span>Set new value</span>
        </v-tooltip>
      </template>
      <v-text-field
        v-else
        v-model="entry.value"
        label="Value"
        density="compact"
        variant="outlined"
        hide-details
        class="mr-2 flex-grow-1"
        @update:model-value="emit"
      />
      <v-checkbox
        v-model="entry.encrypt"
        label="Encrypt"
        density="compact"
        hide-details
        class="mt-0 mr-3 flex-shrink-0"
        @update:model-value="onEncryptChange(index)"
      />
      <v-btn icon size="small" color="error" @click="removeEntry(index)">
        <v-icon size="small">mdi-delete</v-icon>
      </v-btn>
    </div>
    <v-btn size="small" variant="text" color="primary" class="mt-1 pl-0" @click="addEntry">
      <v-icon start size="small">mdi-plus</v-icon>
      Add entry
    </v-btn>
  </div>
</template>

<script>
import cloneDeep from "lodash/cloneDeep";

export default {
  name: "HieradataEditor",
  emits: ["update:modelValue"],
  props: {
    modelValue: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      localEntries: [],
    };
  },
  watch: {
    modelValue: {
      handler(val) {
        this.localEntries = cloneDeep(val || []);
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    isWriteOnly(entry) {
      return entry.encrypt && entry.value === null;
    },
    enableEdit(index) {
      this.localEntries[index].value = "";
      this.emit();
    },
    onEncryptChange(index) {
      // If unchecking encrypt on a write-only entry, clear the preserved value
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
