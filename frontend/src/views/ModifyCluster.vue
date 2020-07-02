<template>
  <cluster-editor
    :existing-cluster="true"
    :hostname="hostname"
    :show-plan-confirmation="showPlanConfirmation"
    :destroy="destroy"
  />
</template>

<script>
import ClusterEditor from "@/components/cluster/ClusterEditor";

export default {
  components: { ClusterEditor },
  props: {
    hostname: {
      type: String,
      required: true
    },
    showPlanConfirmation: {
      type: Boolean,
      default: false
    },
    destroy: {
      type: Boolean,
      default: false
    }
  },
  created() {
    this.removeQueryParameters();
  },
  methods: {
    removeQueryParameters() {
      /*
      Removes all query parameters from the url (e.g. "?destroy=1").
      The parameters still get sent as a prop to ClusterEditor.
      */
      this.$router.push({});
    }
  }
};
</script>
