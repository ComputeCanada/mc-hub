<template>
  <cluster-display :key="$route.fullPath" />
</template>

<script>
import ClusterDisplay from "@/components/cluster/ClusterDisplay";

export default {
  components: { ClusterDisplay },
};
</script>
