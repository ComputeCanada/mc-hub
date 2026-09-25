<template>
  <v-app>
    <v-main>
      <v-container class="foundation-shell">
        <h1 class="mb-4">Vue 3 foundation</h1>
        <nav aria-label="Foundation pages" class="mb-6">
          <v-btn to="/" class="mr-2">Home</v-btn>
          <v-btn to="/about">About</v-btn>
        </nav>
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script>
export default { name: "FoundationApp" };
</script>

<style scoped lang="scss">
$content-width: 48rem;

.foundation-shell {
  max-width: $content-width;
}
</style>
