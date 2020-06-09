<template>
  <cluster-editor :existing-cluster="false" />
</template>

<script>
import ClusterEditor from "@/components/cluster/ClusterEditor";

export default {
  components: { ClusterEditor }
};
</script>
