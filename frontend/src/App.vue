<template>
  <div id="app">
    <v-app>
      <v-app-bar
        dense
        color="primary"
        dark
      >
        <v-toolbar-title>Magic Castle UI</v-toolbar-title>
      </v-app-bar>
      <v-container style="height: 100%">
        <router-view/>
      </v-container>
    </v-app>
  </div>
</template>
