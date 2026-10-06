import { createApp } from "vue";
import "vuetify/styles";
import App from "./App.vue";
import { createAppRouter } from "./router";
import { createAppVuetify } from "./plugins/vuetify";
import UnloadConfirmation from "./plugins/UnloadConfirmation";

const router = createAppRouter();
export const app = createApp(App);

// Register confirmation hooks before Router starts the initial navigation.
app.use(UnloadConfirmation, { router });
app.use(createAppVuetify());
app.use(router);

// A rejected initial navigation remains a visible startup error.
export const ready = router.isReady().then(() => app.mount("#app"));
