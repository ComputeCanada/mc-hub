<template>

  <div>
    <v-container>
      <v-card max-width="500" class="mx-auto" :loading="loading">
        <v-card-title v-if="existingCluster" class="mx-auto pl-8">
          Cluster modification
        </v-card-title>
        <v-card-title v-else class="mx-auto pl-8">
          Cluster creation
        </v-card-title>
        <v-card-text>
          <v-form>
            <v-subheader>General configuration</v-subheader>
            <v-list class="pb-0">
              <v-list-item>
                <div style="display: flex; align-items: center; width: 100%">
                  <v-text-field
                    v-if="existingCluster"
                    v-model="clusterName"
                    label="Cluster name"
                    disabled
                  />
                  <v-text-field
                    v-else
                    v-model="magicCastle.cluster_name"
                    label="Cluster name"
                  />
                  <v-chip
                    class="ml-3"
                    label
                    :color="formattedStatus.color"
                    dark
                    v-if="currentStatus !== null"
                  >{{formattedStatus.text}}
                  </v-chip>
                </div>
              </v-list-item>
            </v-list>
            <template v-if="magicCastle !== null">
              <v-list class="pt-0">
                <v-list-item>
                  <v-text-field v-model="magicCastle.domain" label="Domain"/>
                </v-list-item>
                <v-list-item>

                  <v-select v-model="magicCastle.image" :items="getPossibleValues('image')" label="Image"/>
                </v-list-item>
                <v-list-item>
                  <v-text-field v-model.number="magicCastle.nb_users" type="number" label="Number of users"/>
                </v-list-item>
              </v-list>
              <v-divider/>

              <!-- Instances -->
              <v-subheader>Node instances</v-subheader>
              <v-list>
                <div :key="id" v-for="[id, label] in Object.entries(NODE_LABELS)">
                  <v-list-item>
                    <v-col cols="12" sm="3" class="pl-0">
                      <p>{{label}}</p>
                    </v-col>

                    <v-col cols="12" sm="5">
                      <v-select
                        :items="getPossibleValues(`instances.${id}.type`)"
                        v-model="magicCastle.instances[id].type"
                        label="Type"
                      />
                    </v-col>

                    <v-col cols="12" sm="4">
                      <v-text-field
                        v-model.number="magicCastle.instances[id].count"
                        type="number"
                        label="Count"
                      />
                    </v-col>
                  </v-list-item>
                  <v-divider/>
                </div>
              </v-list>

              <!-- Storage -->
              <v-subheader>Storage</v-subheader>
              <v-list>
                <v-list-item>
                  <v-col cols="12" sm="3" class="pl-0">
                    Type
                  </v-col>
                  <v-col cols="12" sm="9">
                    <v-select
                      :items="getPossibleValues('storage.type')"
                      v-model="magicCastle.storage.type"
                    />
                  </v-col>
                </v-list-item>
                <v-divider/>
                <div :key="id" v-for="[id, label] in Object.entries(STORAGE_LABELS)">
                  <v-list-item>
                    <v-col cols="12" sm="3" class="pl-0">
                      {{label}} size
                    </v-col>
                    <v-col cols="12" sm="9">
                      <v-text-field
                        v-model.number="magicCastle.storage[`${id}_size`]"
                        type="number"
                        suffix="GB"
                      />
                    </v-col>
                  </v-list-item>
                  <v-divider/>
                </div>
              </v-list>

              <!-- Networking & security -->
              <v-subheader>Networking and security</v-subheader>
              <v-list>
                <v-list-item>

                  <v-file-input
                    ref="a"
                    @change="publicKeysUpdated"
                    label="SSH public key file"
                  />
                </v-list-item>
                <v-list-item>


                  <v-text-field v-model="magicCastle.guest_passwd" label="Guest password (optional)"/>
                </v-list-item>
                <v-list-item>

                  <v-select
                    :items="[...getPossibleValues('os_floating_ips'), ...magicCastle.os_floating_ips]"
                    v-model="magicCastle.os_floating_ips[0]"
                    @change="osFloatingIpsUpdated"
                    label="OpenStack floating IP (optional)"
                  />
                </v-list-item>
              </v-list>

              <template v-if="existingCluster === true">
                <v-btn @click="modifyCluster" color="primary" class="ma-2"
                       :disabled="loading" large>
                  Modify
                </v-btn>
                <v-btn @click="deleteCluster" color="primary" class="ma-2" :disabled="loading" large
                       outlined>
                  Delete
                </v-btn>
              </template>
              <template v-else>
                <v-btn @click="createCluster" color="primary" class="text-right"
                       :disabled="loading" large
                >Spawn
                </v-btn>
              </template>
            </template>
          </v-form>
        </v-card-text>
      </v-card>
    </v-container>
    <v-dialog v-model="successDialog" max-width="400">
      <v-card>
        <v-card-title>Success</v-card-title>
        <v-card-text>
          Your cluster was created successfully.<br/><br/>
          Don't forget to destroy it when you are done!
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="successDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="errorDialog" max-width="400">
      <v-card>
        <v-card-title>Error</v-card-title>
        <v-card-text>
          {{ errorMessage }}
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="errorDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
  const API_URL = 'http://localhost:5000/api'

  const ClusterStatusCode = Object.freeze({
    IDLE: 'idle',
    BUILD_RUNNING: 'build_running',
    BUILD_SUCCESS: 'build_success',
    BUILD_ERROR: 'build_error',
    DESTROY_RUNNING: 'destroy_running',
    DESTROY_ERROR: 'destroy_error',
    NOT_FOUND: 'not_found'
  })

  const ClusterFormattedStatus = Object.freeze({
    'idle': {text: 'Idle', color: 'blue'},
    'build_running': {text: 'Build running', color: 'orange'},
    'build_success': {text: 'Build success', color: 'green'},
    'build_error': {text: 'Build error', color: 'red'},
    'destroy_running': {text: 'Destroy running', color: 'orange'},
    'destroy_error': {text: 'Destroy error', color: 'red'},
    'not_found': {text: 'Not found', color: 'purple'}
  })

  const POLL_STATUS_INTERVAL = 1000

  const DEFAULT_MAGIC_CASTLE = {
    cluster_name: "phoenix",
    domain: "calculquebec.cloud",
    image: "CentOS-7-x64-2019-07",
    nb_users: 10,
    instances: {
      mgmt: {
        type: "p4-6gb",
        count: 1
      },
      login: {
        type: "p2-3gb",
        count: 1
      },
      node: {
        type: "p2-3gb",
        count: 1
      }
    },
    storage: {
      type: "nfs",
      home_size: 100,
      project_size: 50,
      scratch_size: 50
    },
    public_keys: [],
    guest_passwd: "",
    os_floating_ips: []
  }

  export default {
    name: "ClusterEditor",
    props: {
      clusterName: String,
      existingCluster: {
        type: Boolean,
        required: true
      }
    },
    data: function () {
      return {
        NODE_LABELS: {
          'mgmt': 'Management',
          'login': 'Login',
          'node': 'Compute'
        },
        STORAGE_LABELS: {
          'home': 'Home',
          'project': 'Project',
          'scratch': 'Scratch'
        },

        successDialog: false,
        errorDialog: false,
        errorMessage: '',
        statusPoller: null,
        currentStatus: null,
        magicCastle: null,
        fieldsPossibleValues: null,
      }
    },
    created() {
      this.loadFieldsPossibleValues()
      if (this.existingCluster) {
        this.startStatusPolling()
      } else {
        this.magicCastle = DEFAULT_MAGIC_CASTLE
      }
    },
    beforeDestroy() {
      this.stopStatusPolling()
    },
    computed: {
      loading() {
        const currentlyRunning = [ClusterStatusCode.DESTROY_RUNNING, ClusterStatusCode.BUILD_RUNNING].includes(this.currentStatus)
        return this.existingCluster && (this.currentStatus === null || currentlyRunning)
      },
      formattedStatus() {
        if (this.currentStatus === null) {
          return ClusterFormattedStatus[ClusterStatusCode.IDLE]
        } else {
          return ClusterFormattedStatus[this.currentStatus]
        }
      }
    },
    methods: {
      getPossibleValues(fieldPath) {
        if (this.fieldsPossibleValues === null) {
          return []
        } else {
          return fieldPath.split('.').reduce((acc, x) => acc[x], this.fieldsPossibleValues)
        }
      },
      osFloatingIpsUpdated() {
        // When the floating IP text field is empty, we need to empty the floating IPs array
        if (this.magicCastle.os_floating_ips[0] === '') {
          this.magicCastle.os_floating_ips = []
        }
      },
      publicKeysUpdated(file) {
        const reader = new FileReader()
        reader.addEventListener('load', event => {
          const publicKey = event.target.result
          this.magicCastle.public_keys = [publicKey]
        })
        if (typeof file === 'object')
          reader.readAsText(file)
        else
          this.magicCastle.public_keys = []
      },
      showSuccess() {
        this.successDialog = true
      },
      showError(message) {
        this.errorDialog = true
        this.errorMessage = message
      },
      startStatusPolling() {
        let fetchStatus = async () => {
          let statusResponse = await fetch(
            `${API_URL}/magic-castle/${this.clusterName}/status`
          )
          const {status} = await statusResponse.json()

          if (this.currentStatus !== status) {

            // The cluster status changed or was fetched for the first time
            await this.loadCluster()
            if (this.currentStatus !== null) {
              this.showStatusDialog(status)
            }
          }
          this.currentStatus = status
        }

        this.statusPoller = setInterval(fetchStatus, POLL_STATUS_INTERVAL)
      },
      showStatusDialog(status) {
        switch (status) {
          case ClusterStatusCode.BUILD_SUCCESS:
            this.showSuccess()
            break
          case ClusterStatusCode.IDLE:
            this.showError('The server is still idle')
            break
          case ClusterStatusCode.BUILD_ERROR:
            this.showError('Terraform returned an error while creating the cluster.')
            break
          case ClusterStatusCode.DESTROY_ERROR:
            this.showError('Terraform returned an error while destroying the cluster.')
        }
      },
      stopStatusPolling() {
        clearInterval(this.statusPoller)
      },
      async loadFieldsPossibleValues() {
        let response = await fetch(`${API_URL}/fields/magic-castle`, {
          method: 'GET'
        })
        this.fieldsPossibleValues = await response.json()
      },
      async createCluster() {
        try {
          let response = await fetch(`${API_URL}/magic-castle`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.magicCastle)
            }
          )
          if (!response.ok)
            throw Error('You provided one or many invalid cluster parameters.')

          await this.$router.push({path: `/clusters/${this.magicCastle.cluster_name}`})
        } catch (e) {
          this.showError(e.message)
        }
      },
      async loadCluster() {
        try {
          let response = await fetch(`${API_URL}/magic-castle/${this.clusterName}`,
            {
              method: 'GET'
            })
          if (!response.ok)
            throw Error('The cluster is invalid.')

          this.magicCastle = await response.json()

        } catch (e) {
          console.log(e.message)
        }
      },
      unloadCluster() {
        this.magicCastle = null
        this.currentStatus = null
      },
      async modifyCluster() {
        try {
          let response = await fetch(`${API_URL}/magic-castle/${this.magicCastle.cluster_name}`,
            {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.magicCastle)
            }
          )
          if (!response.ok)
            throw Error('You provided one or many invalid cluster parameters.')
          this.unloadCluster()
        } catch (e) {
          this.showError(e.message)
        }
      },
      async deleteCluster() {
        try {
          let response = await fetch(`${API_URL}/magic-castle/${this.magicCastle.cluster_name}`,
            {
              method: 'DELETE',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.magicCastle)
            }
          )
          if (!response.ok)
            throw Error('The server returned an error.')
          this.unloadCluster()
        } catch (e) {
          this.showError(e.message)
        }
      }
    },
  }
</script>

<style scoped>

</style>
