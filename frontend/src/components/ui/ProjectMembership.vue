<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="secondary" text v-bind="attrs" v-on="on" :disabled="!admin"> <v-icon>mdi-pencil</v-icon> edit </v-btn>
    </template>
    <message-dialog v-model="errorDialog" type="error">{{ errorMessage }}</message-dialog>
    <v-card>
      <v-card-title>
        <span class="text-h5">Edit project</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-list>
            <v-list-item v-if="admin">
              <v-text-field v-model="githubTemplate" label="Github Template" clearable />
            </v-list-item>
            <v-list-item v-if="admin">
              <v-text-field v-model="agentPoolName" label="Agent Pool Name" hint="Leave empty to keep existing" persistent-hint clearable />
            </v-list-item>
            <template v-if="admin && project.provider === 'openstack'">
              <v-subheader>Cloud Credentials</v-subheader>
              <v-list-item>
                <v-text-field v-model="env.OS_AUTH_URL" label="OS_AUTH_URL" hint="Leave empty to keep existing" persistent-hint />
              </v-list-item>
              <v-list-item>
                <v-text-field v-model="env.OS_APPLICATION_CREDENTIAL_ID" label="OS_APPLICATION_CREDENTIAL_ID" hint="Leave empty to keep existing" persistent-hint />
              </v-list-item>
              <v-list-item>
                <v-text-field v-model="env.OS_APPLICATION_CREDENTIAL_SECRET" label="OS_APPLICATION_CREDENTIAL_SECRET" hint="Leave empty to keep existing" persistent-hint type="password" />
              </v-list-item>
            </template>
            <v-subheader>Members</v-subheader>
            <v-list-item v-for="entry in entries" :key="entry.username" dense>
              <v-list-item-content>{{ entry.username }}</v-list-item-content>
              <v-list-item-action>
                <v-tooltip bottom>
                  <template #activator="{ on, attrs }">
                    <v-simple-checkbox
                      v-model="entry.isAdmin"
                      v-bind="attrs"
                      v-on="on"
                    />
                  </template>
                  <span>Admin</span>
                </v-tooltip>
              </v-list-item-action>
              <v-list-item-action>
                <v-btn icon small @click="removeMember(entry.username)">
                  <v-icon small>mdi-delete</v-icon>
                </v-btn>
              </v-list-item-action>
            </v-list-item>
            <v-list-item>
              <v-text-field
                :append-outer-icon="'mdi-plus'"
                v-model="newMember"
                type="text"
                clearable
                filled
                label="Add a member"
                hint="Check the box to make them admin"
                @click:append-outer="addMember"
                v-on:keyup.enter="addMember"
              />
              <v-tooltip bottom>
                <template #activator="{ on, attrs }">
                  <v-simple-checkbox v-model="newMemberIsAdmin" class="ml-2" v-bind="attrs" v-on="on" />
                </template>
                <span>Admin</span>
              </v-tooltip>
            </v-list-item>
          </v-list>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close"> Cancel </v-btn>
        <v-btn color="blue darken-1" text @click="save"> Save </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import ProjectRepository from "@/repositories/ProjectRepository";
import MessageDialog from "@/components/ui/MessageDialog";

export default {
  name: "ProjectMembership",
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
      githubTemplate: "",
      agentPoolName: "",
      env: { OS_AUTH_URL: "", OS_APPLICATION_CREDENTIAL_ID: "", OS_APPLICATION_CREDENTIAL_SECRET: "" },
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
        this.githubTemplate = this.project.github_template;
      } else {
        this.close();
      }
    },
  },
  methods: {
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
      if (this.admin && this.githubTemplate !== this.project.github_template) {
        payload.github_template = this.githubTemplate ?? "";
      }
      if (this.admin && this.agentPoolName) {
        payload.agent_pool_name = this.agentPoolName;
      }
      const envValues = Object.values(this.env);
      if (envValues.some((v) => v)) {
        if (envValues.every((v) => v)) {
          payload.env = { ...this.env };
        } else {
          this.errorMessage = "All credential fields must be filled to update credentials.";
          this.errorDialog = true;
          return;
        }
      }
      try {
        await ProjectRepository.patch(this.id, payload);
      } catch (e) {
        this.errorMessage = e.response?.data?.message ?? "An error occurred while saving the project.";
        this.errorDialog = true;
        return;
      }
      this.close();
    },
    close() {
      this.project = {};
      this.entries = [];
      this.newMember = "";
      this.newMemberIsAdmin = false;
      this.githubTemplate = "";
      this.agentPoolName = "";
      this.env = { OS_AUTH_URL: "", OS_APPLICATION_CREDENTIAL_ID: "", OS_APPLICATION_CREDENTIAL_SECRET: "" };
      this.dialog = false;
    },
  },
};
</script>
