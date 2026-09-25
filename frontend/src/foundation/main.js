import { createApp } from "vue";
import { createWebHistory } from "vue-router";
import "vuetify/styles";
import FoundationApp from "@/foundation/FoundationApp.vue";
import { createFoundationRouter } from "@/foundation/router";
import { createFoundationVuetify } from "@/foundation/vuetify";

createApp(FoundationApp)
  .use(createFoundationRouter(createWebHistory(process.env.BASE_URL)))
  .use(createFoundationVuetify())
  .mount("#app");
