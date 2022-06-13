<template>
  <v-dialog v-model="dialog" max-width="500px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="secondary" text v-bind="attrs" v-on="on"> <v-icon>mdi-pencil</v-icon> </v-btn>
    </template>
    <v-card>
      <v-card-title>
        <span class="text-h5">Edit project membership</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-list>
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

export default {
  name: "ProjectMembership",
  props: {
    id: {
      type: Number,
      required: true,
    },
  },
  data() {
    return {
      dialog: false,
      project: {},
      members: [],
      newMember: "",
    };
  },
  watch: {
    async dialog(val) {
      if (val) {
        this.project = (await ProjectRepository.get(this.id)).data;
        this.members = [...this.project.members];
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
      await ProjectRepository.patch(this.id, { add: add_members, del: del_members });
      this.close();
    },
    close() {
      this.project = {};
      this.members = [];
      this.dialog = false;
    },
  },
};
</script>
