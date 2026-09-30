<template>
  <v-menu location="bottom" v-if="currentUser.username">
    <template #activator="{ props }">
      <v-btn v-bind="props" variant="text">
        <v-icon class="mr-4">mdi-account</v-icon>
        {{ currentUser.username }}
      </v-btn>
    </template>
    <v-list>
      <v-list-item to="/capacity"
        ><v-list-item-title
          ><v-icon class="mr-4">mdi-calendar-clock</v-icon>Capacity planner</v-list-item-title
        ></v-list-item
      >
      <v-list-item v-if="benchmarkAccess.allowed" to="/benchmarks">
        <v-list-item-title><v-icon class="mr-4">mdi-timer-outline</v-icon>Benchmarks</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="currentUser.is_admin" to="/usage">
        <v-list-item-title><v-icon class="mr-4">mdi-chart-bar</v-icon>Service adoption</v-list-item-title>
      </v-list-item>
      <v-list-item to="/projects">
        <v-list-item-title> <v-icon class="mr-4">mdi-cloud-braces</v-icon>Projects </v-list-item-title>
      </v-list-item>
      <v-list-item v-if="currentUser.usertype == 'saml'" href="/Shibboleth.sso/Logout">
        <v-list-item-title> <v-icon class="mr-4">mdi-logout</v-icon>Logout </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import { benchmarkAccess } from "@/services/benchmarkAccess";
import UserRepository from "@/repositories/UserRepository";
export default {
  data() {
    return {
      benchmarkAccess,
      currentUser: { full_name: null, username: null, usertype: "local", public_keys: [], is_admin: false },
    };
  },
  async created() {
    this.currentUser = (await UserRepository.getCurrent()).data;
  },
};
</script>
