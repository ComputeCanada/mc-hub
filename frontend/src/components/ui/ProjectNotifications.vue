<template>
  <v-dialog v-model="dialog" max-width="600">
    <template #activator="{ on: dialogOn, attrs: dialogAttrs }">
      <v-tooltip bottom>
        <template #activator="{ on: tooltipOn, attrs: tooltipAttrs }">
          <v-btn
            text
            color="secondary"
            aria-label="Notifications"
            v-bind="{ ...dialogAttrs, ...tooltipAttrs }"
            v-on="{ ...tooltipOn, ...dialogOn }"
            ><v-icon>mdi-bell-outline</v-icon></v-btn
          >
        </template>
        <span>Notifications</span>
      </v-tooltip>
    </template>
    <v-card :loading="loading">
      <v-card-title>Project notifications</v-card-title>
      <v-card-text>
        <p>
          Capacity warnings go only to this project's destination. Only hub operators who administer this project can
          change it.
        </p>
        <v-alert v-if="error" type="error">{{ error }}</v-alert>
        <v-form ref="form" v-model="valid">
          <v-select v-model="kind" :items="types" label="Destination type" :disabled="busy" />
          <v-text-field
            v-model="url"
            type="password"
            autocomplete="new-password"
            label="HTTPS webhook URL"
            :disabled="busy"
            :rules="[urlRule]"
            :hint="
              configured
                ? 'A URL is stored. Leave blank to keep it, or enter a replacement.'
                : 'Enter a Slack incoming webhook or a generic HTTPS webhook URL.'
            "
            persistent-hint
          />
          <v-text-field
            v-model="token"
            type="password"
            autocomplete="new-password"
            label="Bearer token (optional)"
            :disabled="busy || clearToken"
            :hint="
              hasToken ? 'A token is stored. Leave blank to keep it.' : 'Optional authorization token for the webhook.'
            "
            persistent-hint
          />
          <v-checkbox v-if="hasToken" v-model="clearToken" label="Remove stored token" :disabled="busy" />
          <v-switch v-model="enabled" label="Enable project capacity alerts" :disabled="busy" />
        </v-form>
        <p v-if="lastDelivery">
          Last delivery: {{ lastDelivery.state }} ({{ lastDelivery.attempts }} attempts)<span v-if="lastDelivery.error">
            — {{ lastDelivery.error }}</span
          >
        </p>
        <p v-else-if="configured">No deliveries to this destination yet.</p>
      </v-card-text>
      <v-card-actions>
        <v-btn v-if="configured" text color="error" :disabled="busy" @click="removeDialog = true"
          >Remove destination</v-btn
        >
        <v-spacer />
        <v-btn text :disabled="busy" @click="dialog = false">Cancel</v-btn>
        <v-btn text color="primary" :disabled="busy || !valid" :loading="saving" @click="save">Save</v-btn>
      </v-card-actions>
    </v-card>
    <confirm-dialog v-model="removeDialog" title="Remove notification destination" @confirm="remove">
      Stop external capacity alerts for this project and cancel pending deliveries?
    </confirm-dialog>
  </v-dialog>
</template>
<script>
import Repository from "@/repositories/Repository";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
export default {
  name: "ProjectNotifications",
  components: { ConfirmDialog },
  props: { id: { type: Number, required: true } },
  data: () => ({
    dialog: false,
    removeDialog: false,
    loading: false,
    saving: false,
    valid: false,
    error: "",
    configured: false,
    kind: "webhook",
    url: "",
    token: "",
    hasToken: false,
    clearToken: false,
    enabled: true,
    lastDelivery: null,
    types: [
      { text: "Generic webhook", value: "webhook" },
      { text: "Slack", value: "slack" },
    ],
  }),
  computed: {
    busy() {
      return this.loading || this.saving;
    },
    path() {
      return `/projects/${this.id}/notification-destination`;
    },
    urlRule() {
      return (value) => (!value && this.configured) || /^https:\/\/\S+$/i.test(value) || "Enter an HTTPS webhook URL";
    },
  },
  watch: {
    async dialog(open) {
      this.url = "";
      this.token = "";
      this.clearToken = false;
      this.error = "";
      if (!open) return;
      this.loading = true;
      try {
        const { data } = await Repository.get(this.path);
        this.configured = data.configured;
        this.kind = data.type || "webhook";
        this.enabled = data.configured ? data.enabled : true;
        this.hasToken = data.has_token || false;
        this.lastDelivery = data.last_delivery || null;
      } catch (e) {
        this.showError(e);
      } finally {
        this.loading = false;
      }
    },
  },
  methods: {
    showError(e) {
      this.error = e.response?.data?.message || "Could not update project notifications.";
    },
    async save() {
      if (!this.$refs.form.validate()) return;
      this.saving = true;
      this.error = "";
      const payload = { type: this.kind, enabled: this.enabled };
      if (this.url) payload.url = this.url;
      if (this.clearToken) payload.token = "";
      else if (this.token) payload.token = this.token;
      try {
        await Repository.put(this.path, payload);
        this.dialog = false;
      } catch (e) {
        this.showError(e);
      } finally {
        this.saving = false;
      }
    },
    async remove() {
      this.saving = true;
      this.error = "";
      try {
        await Repository.delete(this.path);
        this.dialog = false;
      } catch (e) {
        this.showError(e);
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>
