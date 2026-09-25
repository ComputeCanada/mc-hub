<template>
  <section>
    <h2 class="mb-4">Component integration</h2>
    <v-text-field v-model="name" label="Your name" />
    <p data-testid="greeting" class="mb-4">Hello, {{ name || "contributor" }}!</p>
    <v-btn data-testid="increment" color="primary" @click="count++">Clicked {{ count }} times</v-btn>
    <v-icon icon="mdi-check" aria-label="Ready" class="ml-2" />
  </section>
</template>

<script>
export default {
  name: "FoundationHome",
  data() {
    return { name: "", count: 0 };
  },
};
</script>
