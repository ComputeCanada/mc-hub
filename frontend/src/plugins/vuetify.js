import { VPagination } from "vuetify/components/VPagination";
import { VDataTable } from "vuetify/components/VDataTable";
import { VToolbar, VToolbarTitle } from "vuetify/components/VToolbar";
import { VDatePicker } from "vuetify/components/VDatePicker";
import { VExpandTransition } from "vuetify/components/transitions";
import { VCombobox } from "vuetify/components/VCombobox";
import { VSheet } from "vuetify/components/VSheet";
import { VProgressLinear } from "vuetify/components/VProgressLinear";
import { VProgressCircular } from "vuetify/components/VProgressCircular";
import { VChip } from "vuetify/components/VChip";
import { VInput } from "vuetify/components/VInput";
import { VRadioGroup } from "vuetify/components/VRadioGroup";
import { VRadio } from "vuetify/components/VRadio";
import { VFileInput } from "vuetify/components/VFileInput";
import { VForm } from "vuetify/components/VForm";
import { VSwitch } from "vuetify/components/VSwitch";
import { VCheckbox, VCheckboxBtn } from "vuetify/components/VCheckbox";
import { VSelect } from "vuetify/components/VSelect";
import { VTextarea } from "vuetify/components/VTextarea";
import { VTextField } from "vuetify/components/VTextField";
import { VTooltip } from "vuetify/components/VTooltip";
import { VDivider } from "vuetify/components/VDivider";
import { VDialog } from "vuetify/components/VDialog";
import { VCard, VCardTitle, VCardSubtitle, VCardText, VCardActions } from "vuetify/components/VCard";
import { createVuetify } from "vuetify";
import { VAlert } from "vuetify/components/VAlert";
import { VApp } from "vuetify/components/VApp";
import { VAppBar } from "vuetify/components/VAppBar";
import { VBtn } from "vuetify/components/VBtn";
import { VContainer, VSpacer, VRow, VCol } from "vuetify/components/VGrid";
import { VIcon } from "vuetify/components/VIcon";
import {
  VList,
  VListItem,
  VListItemTitle,
  VListSubheader,
  VListItemSubtitle,
  VListGroup,
} from "vuetify/components/VList";
import { VMain } from "vuetify/components/VMain";
import { VMenu } from "vuetify/components/VMenu";
import { Ripple } from "vuetify/directives/ripple";
import { aliases, mdi } from "vuetify/iconsets/mdi";

export const appComponents = {
  VDataTable,
  VPagination,
  VToolbar,
  VToolbarTitle,
  VDatePicker,
  VExpandTransition,
  VListItemSubtitle,
  VListGroup,
  VCombobox,
  VSheet,
  VProgressLinear,
  VProgressCircular,
  VChip,
  VInput,
  VRadioGroup,
  VRadio,
  VFileInput,
  VForm,
  VSwitch,
  VCheckbox,
  VCheckboxBtn,
  VSelect,
  VTextarea,
  VTextField,
  VTooltip,
  VDivider,
  VDialog,
  VCard,
  VCardTitle,
  VCardSubtitle,
  VCardText,
  VCardActions,
  VAlert,
  VApp,
  VAppBar,
  VBtn,
  VContainer,
  VRow,
  VCol,
  VListSubheader,
  VSpacer,
  VIcon,
  VList,
  VListItem,
  VListItemTitle,
  VMain,
  VMenu,
};

export function createAppVuetify() {
  return createVuetify({
    components: appComponents,
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
