<template>
  <v-app>
    <v-app-bar density="compact" color="primary">
      <v-btn variant="text" to="/" exact>MC Hub</v-btn>
      <v-btn variant="text" to="/capacity">Planner</v-btn>
      <v-btn v-if="benchmarkAccess.allowed" variant="text" to="/benchmarks">Benchmarks</v-btn>
      <v-spacer />
      <account-dropdown />
    </v-app-bar>
    <v-main>
      <service-status-banner />
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>
<script>
import { benchmarkAccess, refreshBenchmarkAccess } from "@/services/benchmarkAccess";
import ServiceStatusBanner from "@/components/ui/ServiceStatusBanner";
import AccountDropdown from "@/components/ui/AccountDropdown";

export default {
  components: { AccountDropdown, ServiceStatusBanner },
  data: () => ({ benchmarkAccess }),
  watch: {
    $route: { immediate: true, handler: refreshBenchmarkAccess },
  },
};
</script>
