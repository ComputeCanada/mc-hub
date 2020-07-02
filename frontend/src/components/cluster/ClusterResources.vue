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
          <v-icon color="green" v-if="resource.change.done === true">mdi-check</v-icon>
          <v-icon color="grey" v-else>mdi-cloud-upload</v-icon>
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
  computed: {
    relevantResourcesChanges() {
      return this.resourcesChanges.filter(
        resource => !isEqual(resource.change.actions, ["no-op"])
      );
    }
  },
  methods: {
    isEqual(a, b) {
      return isEqual(a, b);
    }
  }
};
</script>
