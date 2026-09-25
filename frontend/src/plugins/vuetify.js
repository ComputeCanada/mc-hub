import { createVuetify } from "vuetify";
import { VAlert } from "vuetify/components/VAlert";
import { VApp } from "vuetify/components/VApp";
import { VAppBar } from "vuetify/components/VAppBar";
import { VBtn } from "vuetify/components/VBtn";
import { VContainer, VSpacer } from "vuetify/components/VGrid";
import { VIcon } from "vuetify/components/VIcon";
import { VList, VListItem, VListItemTitle } from "vuetify/components/VList";
import { VMain } from "vuetify/components/VMain";
import { VMenu } from "vuetify/components/VMenu";
import { Ripple } from "vuetify/directives/ripple";
import { aliases, mdi } from "vuetify/iconsets/mdi";

export function createAppVuetify() {
  return createVuetify({
    components: {
      VAlert,
      VApp,
      VAppBar,
      VBtn,
      VContainer,
      VSpacer,
      VIcon,
      VList,
      VListItem,
      VListItemTitle,
      VMain,
      VMenu,
    },
    directives: { Ripple },
    // The public HTML template loads the MDI font.
    icons: { defaultSet: "mdi", aliases, sets: { mdi } },
    theme: {
      defaultTheme: "light",
      themes: {
        light: {
          colors: {
            background: "#eef3f3",
            primary: "#1976D2",
            "on-primary": "#FFFFFF",
            secondary: "#424242",
            accent: "#82B1FF",
            error: "#FF5252",
            info: "#2196F3",
            success: "#4CAF50",
            warning: "#FFC107",
          },
        },
      },
    },
  });
}
