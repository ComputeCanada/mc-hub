<template>
  <cluster-display
    :existing-cluster="true"
    :hostname="hostname"
    :show-plan-confirmation="showPlanConfirmation"
    :destroy="destroy"
  />
</template>

<script>
import ClusterDisplay from "@/components/cluster/ClusterDisplay";

export default {
  components: { ClusterDisplay },
  props: {
    hostname: {
      type: String,
      required: true,
    },
    showPlanConfirmation: {
      type: Boolean,
      default: false,
    },
    destroy: {
      type: Boolean,
      default: false,
    },
  },
  created() {
    this.removeQueryParameters();
  },
  methods: {
    removeQueryParameters() {
      /*
      Removes all query parameters from the url (e.g. "?destroy=1").
      The parameters still get sent as a prop to ClusterEditor.

      NavigationDuplicated errors need to be caught, because vue-router throws this
      exception whenever a path is navigated twice in a row, even with different query params.
      */
      this.$router.replace({ query: {} }).catch(() => {});
    },
  },
};
</script>
