import { createVuetify } from "vuetify";
import { VApp } from "vuetify/components/VApp";
import { VBtn } from "vuetify/components/VBtn";
import { VContainer } from "vuetify/components/VGrid";
import { VIcon } from "vuetify/components/VIcon";
import { VMain } from "vuetify/components/VMain";
import { VTextField } from "vuetify/components/VTextField";
import { Ripple } from "vuetify/directives/ripple";
import { aliases, mdi } from "vuetify/iconsets/mdi";

export function createFoundationVuetify() {
  return createVuetify({
    components: { VApp, VBtn, VContainer, VIcon, VMain, VTextField },
    directives: { Ripple },
    // Uses the MDI font already included by public/index.html.
    icons: { defaultSet: "mdi", aliases, sets: { mdi } },
  });
}
