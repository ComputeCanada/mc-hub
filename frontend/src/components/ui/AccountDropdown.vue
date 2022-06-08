<template>
  <v-menu offset-y v-if="currentUser.username">
    <template #activator="{ on, attrs }">
      <v-btn v-bind="attrs" v-on="on" text>
        <v-icon class="mr-4">mdi-account</v-icon>
        {{ currentUser.username }}
      </v-btn>
    </template>
    <v-list>
      <v-list-item @click="projects">
        <v-list-item-title> <v-icon class="mr-4">mdi-cloud-braces</v-icon>Projects </v-list-item-title>
      </v-list-item>
      <v-list-item v-if="currentUser.usertype == 'saml'" @click="logout">
        <v-list-item-title> <v-icon class="mr-4">mdi-logout</v-icon>Logout </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import UserRepository from "@/repositories/UserRepository";
export default {
  data() {
    return {
      currentUser: { full_name: null, username: null, usertype: "local", public_keys: [] },
    };
  },
  async created() {
    this.currentUser = (await UserRepository.getCurrent()).data;
  },
  methods: {
    projects() {
      location.href = "/projects";
    },
    logout() {
      location.href = "/Shibboleth.sso/Logout";
    },
  },
};
</script>
