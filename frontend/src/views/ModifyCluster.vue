<template>
  <cluster-editor :existing-cluster="true" :hostname="hostname" />
</template>

<script>
import ClusterEditor from "@/components/cluster/ClusterEditor";

export default {
  components: { ClusterEditor },
  props: {
    hostname: {
      type: String,
      required: true
    }
  }
};
</script>
