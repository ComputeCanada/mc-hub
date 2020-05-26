<template>
  <cluster-editor :existing-cluster="true" :cluster-name="clusterName" />
</template>

<script>
import ClusterEditor from "@/components/ClusterEditor";

export default {
  components: { ClusterEditor },
  props: {
    clusterName: String
  }
};
</script>
