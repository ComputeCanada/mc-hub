import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import vuetify from "./plugins/vuetify";
import UnloadConfirmation from "./plugins/UnloadConfirmation";

Vue.config.productionTip = false;

Vue.use(UnloadConfirmation, { router });

new Vue({
  router,
  vuetify,
  render: (h) => h(App),
}).$mount("#app");
