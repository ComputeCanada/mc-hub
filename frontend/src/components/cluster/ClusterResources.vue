<template>
  <div>
    <v-list v-if="relevantResourcesChanges.length === 0" class="my-2">
      <v-list-item>
        <b class="ma-auto">No resource to change.</b>
      </v-list-item>
    </v-list>
    <v-list v-else two-line>
      <v-list-item v-for="resource in relevantResourcesChanges" :key="resource.address">
        <v-list-item-avatar>
          <!-- https://www.terraform.io/docs/internals/json-format.html#change-representation -->
          <v-icon
            v-if="isEqual(resource.change.actions, ['no-op'])"
          >mdi-checkbox-blank-circle-outline</v-icon>
          <v-icon v-else-if="isEqual(resource.change.actions, ['create'])" color="green">mdi-plus</v-icon>
          <v-icon v-else-if="isEqual(resource.change.actions, ['read'])">mdi-text</v-icon>
          <v-icon v-else-if="isEqual(resource.change.actions, ['update'])" color="blue">mdi-pencil</v-icon>
          <div v-else-if="isEqual(resource.change.actions, ['delete', 'create'])" class="d-flex">
            <v-icon color="red">mdi-minus</v-icon>
            <v-icon color="green">mdi-plus</v-icon>
          </div>
          <div v-else-if="isEqual(resource.change.actions, ['create', 'delete'])" class="d-flex">
            <v-icon color="green">mdi-plus</v-icon>
            <v-icon color="red">mdi-minus</v-icon>
          </div>
          <v-icon v-else-if="isEqual(resource.change.actions, ['delete'])" color="red">mdi-close</v-icon>
        </v-list-item-avatar>
        <v-list-item-content>
          <v-list-item-title>{{resource.type}}</v-list-item-title>
          <v-list-item-subtitle>{{resource.address}}</v-list-item-subtitle>
        </v-list-item-content>
        <v-list-item-action v-if="showProgress">
          <template v-if="resource.change.progress === 'done'">
            <v-icon color="green">mdi-check</v-icon>
            <div class="green--text mt-1">done</div>
          </template>
          <template v-else-if="resource.change.progress === 'running'">
            <v-progress-circular color="blue" indeterminate width="2" size="20" />
            <div class="blue--text mt-1">running</div>
          </template>
          <template v-else-if="resource.change.progress === 'queued'">
            <v-icon color="grey">mdi-cloud-upload</v-icon>
            <div class="grey--text mt-1">queued</div>
          </template>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </div>
</template>
<script>
import { isEqual } from "lodash";
export default {
  name: "ClusterResources",
  props: {
    resourcesChanges: {
      type: Array,
      required: true
    },
    showProgress: {
      type: Boolean,
      default: false
    }
  },
  watch: {
    relevantResourcesChanges(relevantResourcesChanges) {
      /**
       * Computes the percentage (from  0 to 100) of resource changes
       * labelled as "done" or "running" (counts for half a resource).
       * The result is emitted to be consumed by other components.
       */
      const total =
        relevantResourcesChanges.length === 0
          ? 1
          : relevantResourcesChanges.length;
      const doneResourceChanges = relevantResourcesChanges.filter(
        resource => resource.change.progress === "done"
      ).length;
      const runningResourceChanges = relevantResourcesChanges.filter(
        resource => resource.change.progress === "running"
      ).length;
      this.$emit(
        "updateProgress",
        (100 * (doneResourceChanges + 0.5 * runningResourceChanges)) / total
      );
    }
  },
  computed: {
    relevantResourcesChanges() {
      /**
       * Resource changes are sorted and displayed in the following order:
       * "done", "running", "queued".
       * "no-op" resource changes are not displayed.
       */
      let resourceChangesComparator = (firstResource, secondResource) => {
        const progressOrder = { done: 0, running: 1, queued: 2 };
        return (
          progressOrder[firstResource.change.progress] -
          progressOrder[secondResource.change.progress]
        );
      };
      return this.resourcesChanges
        .filter(resource => !isEqual(resource.change.actions, ["no-op"]))
        .sort(resourceChangesComparator);
    }
  },
  methods: {
    isEqual(a, b) {
      return isEqual(a, b);
    }
  }
};
</script>
