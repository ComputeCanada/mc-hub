<template>
  <div>
    <div v-if="localEntries.length === 0" class="text-body-2 grey--text mb-2">
      No entries. Click "Add entry" to add puppet configuration variables.
    </div>
    <div v-for="(entry, index) in localEntries" :key="index" class="d-flex align-center mb-2">
      <v-text-field
        v-model="entry.key"
        label="Key"
        dense
        outlined
        hide-details
        class="mr-2"
        style="max-width: 260px; flex-shrink: 0"
        @input="emit"
      />
      <template v-if="isWriteOnly(entry)">
        <v-text-field
          placeholder="Encrypted (write-only)"
          label="Value"
          dense
          outlined
          hide-details
          disabled
          class="mr-2 flex-grow-1"
        />
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <v-btn icon small class="mr-2" v-bind="attrs" v-on="on" @click="enableEdit(index)">
              <v-icon small>mdi-pencil</v-icon>
            </v-btn>
          </template>
          <span>Set new value</span>
        </v-tooltip>
      </template>
      <v-text-field
        v-else
        v-model="entry.value"
        label="Value"
        dense
        outlined
        hide-details
        class="mr-2 flex-grow-1"
        @input="emit"
      />
      <v-checkbox
        v-model="entry.encrypt"
        label="Encrypt"
        dense
        hide-details
        class="mt-0 mr-3 flex-shrink-0"
        @change="onEncryptChange(index)"
      />
      <v-btn icon small color="error" @click="removeEntry(index)">
        <v-icon small>mdi-delete</v-icon>
      </v-btn>
    </div>
    <v-btn small text color="primary" class="mt-1 pl-0" @click="addEntry">
      <v-icon left small>mdi-plus</v-icon>
      Add entry
    </v-btn>
  </div>
</template>

<script>
import { cloneDeep } from "lodash";

export default {
  name: "HieradataEditor",
  props: {
    value: {
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
    value: {
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
      this.$emit("input", cloneDeep(this.localEntries));
    },
  },
};
</script>
