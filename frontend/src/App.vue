<template>
  <div id="app">
    <v-app
      style="background: #eef3f3">
      <v-app-bar
        dense
        color="primary"
        dark
      >
        <v-btn text to="/" exact>Magic Castle UI</v-btn>
      </v-app-bar>
      <v-container style="height: 100%">
        <router-view/>
      </v-container>
    </v-app>
  </div>
</template>
