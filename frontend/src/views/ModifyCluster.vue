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
  }
};
</script>
