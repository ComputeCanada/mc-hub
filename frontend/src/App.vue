<template>
  <div id="app">
    <v-app style="background: #eef3f3">
      <v-app-bar dense color="primary" dark>
        <v-btn text to="/" exact>MC Hub</v-btn>
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
import AccountDropdown from "@/components/ui/AccountDropdown";

export default {
  components: { AccountDropdown },
};
</script>
