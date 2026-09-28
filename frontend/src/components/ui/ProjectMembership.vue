<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template #activator="{ props: dialogProps }">
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            color="secondary"
            variant="text"
            aria-label="Members"
            v-bind="mergeProps(tooltipProps, dialogProps)"
            :disabled="!admin"
          >
            <v-icon>mdi-account-group</v-icon>
          </v-btn>
        </template>
        <span>Members</span>
      </v-tooltip>
    </template>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <v-card>
      <v-card-title>
        <span class="text-h5">Project members</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-list>
            <v-list-subheader>Members</v-list-subheader>
            <v-list-item v-for="entry in entries" :key="entry.username" density="compact">
              <v-list-item-title>{{ entry.username }}</v-list-item-title>
              <template #append>
                <v-tooltip location="bottom">
                  <template #activator="{ props }">
                    <v-checkbox-btn aria-label="Admin" v-model="entry.isAdmin" v-bind="props" />
                  </template>
                  <span>Admin</span>
                </v-tooltip>

                <v-btn icon size="small" @click="removeMember(entry.username)">
                  <v-icon size="small">mdi-delete</v-icon>
                </v-btn>
              </template>
            </v-list-item>
            <v-list-item>
              <v-text-field
                :append-icon="'mdi-plus'"
                v-model="newMember"
                type="text"
                clearable
                variant="filled"
                label="Add a member"
                hint="Check the box to make them admin"
                @click:append="addMember"
                v-on:keyup.enter="addMember"
              />
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-checkbox-btn
                    aria-label="New member admin"
                    v-model="newMemberIsAdmin"
                    class="ml-2"
                    v-bind="props"
                  />
                </template>
                <span>Admin</span>
              </v-tooltip>
            </v-list-item>
          </v-list>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue-darken-1" variant="text" @click="close"> Cancel </v-btn>
        <v-btn color="blue-darken-1" variant="text" @click="save"> Save </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { mergeProps } from "vue";
import ProjectRepository from "@/repositories/ProjectRepository";
import MessageDialog from "@/components/ui/MessageDialog";

export default {
  name: "ProjectMembership",
  emits: ["saved"],
  components: { MessageDialog },
  props: {
    id: { type: Number, required: true },
    admin: { type: Boolean, default: false },
  },
  data() {
    return {
      dialog: false,
      errorDialog: false,
      errorMessage: "",
      project: {},
      entries: [], // [{ username, isAdmin }]
      newMember: "",
      newMemberIsAdmin: false,
    };
  },
  watch: {
    async dialog(val) {
      if (val) {
        this.project = (await ProjectRepository.get(this.id)).data;
        const adminSet = new Set(this.project.admins);
        this.entries = this.project.members.map((username) => ({
          username,
          isAdmin: adminSet.has(username),
        }));
      } else {
        this.close();
      }
    },
  },
  methods: {
    mergeProps,
    addMember() {
      if (this.newMember && !this.entries.find((e) => e.username === this.newMember)) {
        this.entries.push({ username: this.newMember, isAdmin: this.newMemberIsAdmin });
        this.newMember = "";
        this.newMemberIsAdmin = false;
      }
    },
    removeMember(username) {
      this.entries = this.entries.filter((e) => e.username !== username);
    },
    async save() {
      const oldMembers = new Set(this.project.members);
      const oldAdmins = new Set(this.project.admins);
      const newMembers = new Set(this.entries.map((e) => e.username));
      const newAdmins = new Set(this.entries.filter((e) => e.isAdmin).map((e) => e.username));

      const payload = {
        add: [...newMembers].filter((x) => !oldMembers.has(x)),
        del: [...oldMembers].filter((x) => !newMembers.has(x)),
        add_admins: [...newAdmins].filter((x) => !oldAdmins.has(x)),
        del_admins: [...oldAdmins].filter((x) => !newAdmins.has(x)),
      };
      try {
        await ProjectRepository.patch(this.id, payload);
      } catch (e) {
        this.errorMessage = e.response?.data?.message ?? "An error occurred while saving the project.";
        this.errorDialog = true;
        return;
      }
      this.$emit("saved");
      this.close();
    },
    close() {
      this.project = {};
      this.entries = [];
      this.newMember = "";
      this.newMemberIsAdmin = false;
      this.dialog = false;
    },
  },
};
</script>
