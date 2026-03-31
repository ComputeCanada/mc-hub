<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="secondary" text v-bind="attrs" v-on="on"> <v-icon>mdi-pencil</v-icon> edit </v-btn>
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
            <v-list-item>
              <v-combobox v-model="members" label="Members" multiple chips append-icon deletable-chips />
            </v-list-item>
            <v-list-item>
              <v-text-field
                :append-outer-icon="'mdi-plus'"
                v-model="newMember"
                type="text"
                clearable
                filled
                label="Add a new member"
                @click:append-outer="addMember"
                v-on:keyup.enter="addMember"
              />
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
    id: {
      type: Number,
      required: true,
    },
    admin: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      dialog: false,
      errorDialog: false,
      errorMessage: "",
      project: {},
      members: [],
      newMember: "",
      githubTemplate: "",
    };
  },
  watch: {
    async dialog(val) {
      if (val) {
        this.project = (await ProjectRepository.get(this.id)).data;
        this.members = [...this.project.members];
        this.githubTemplate = this.project.github_template;
      } else {
        this.close();
      }
    },
  },
  methods: {
    addMember() {
      if (this.newMember !== "") {
        this.members.push(this.newMember);
        this.newMember = "";
      }
    },
    async save() {
      const old_members = new Set(this.project.members);
      const new_members = new Set(this.members);
      const add_members = [...new_members].filter((x) => !old_members.has(x));
      const del_members = [...old_members].filter((x) => !new_members.has(x));
      const payload = { add: add_members, del: del_members };
      if (this.admin && this.githubTemplate !== this.project.github_template) {
        payload.github_template = this.githubTemplate ?? "";
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
      this.members = [];
      this.githubTemplate = "";
      this.dialog = false;
    },
  },
};
</script>
