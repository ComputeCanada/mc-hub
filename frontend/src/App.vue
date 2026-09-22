<template>
  <div id="app">
    <v-app style="background: #eef3f3">
      <v-app-bar dense color="primary" dark>
        <v-btn text to="/" exact>MC Hub</v-btn>
        <v-btn v-if="benchmarkAccess.allowed" text to="/benchmarks">Benchmarks</v-btn>
        <v-spacer />
        <account-dropdown />
      </v-app-bar>
      <v-container style="height: 100%">
        <router-view />
      </v-container>
    </v-app>
  </div>
</template>
<script>
import { benchmarkAccess, refreshBenchmarkAccess } from "@/services/benchmarkAccess";
import AccountDropdown from "@/components/ui/AccountDropdown";

export default {
  components: { AccountDropdown },
  data: () => ({ benchmarkAccess }),
  watch: {
    $route: { immediate: true, handler: refreshBenchmarkAccess },
  },
};
</script>
