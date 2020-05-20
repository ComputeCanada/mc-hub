<template>

  <div>
    <v-container>
      <v-card max-width="500" class="mx-auto" :loading="loading" :disabled="loading">
        <v-card-title class="mx-auto">
          Cluster creation
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="createCluster">
            <v-text-field v-model="magicCastle.cluster_name" label="Cluster name"></v-text-field>
            <v-text-field v-model="magicCastle.domain" label="Domain"></v-text-field>
            <v-text-field v-model="magicCastle.image" label="Image"></v-text-field>
            <v-text-field v-model.number="magicCastle.nb_users" type="number" label="Number of users"></v-text-field>

            <!-- Instances -->
            <v-text-field
              v-model="magicCastle.instances.mgmt.type"
              label="Management (mgmt) instance type"
            ></v-text-field>
            <v-text-field
              v-model.number="magicCastle.instances.mgmt.count"
              type="number"
              label="Management (mgmt) instance count"
            ></v-text-field>
            <v-text-field v-model="magicCastle.instances.login.type" label="Login instance type"></v-text-field>
            <v-text-field
              v-model.number="magicCastle.instances.login.count"
              type="number"
              label="Login instance count"
            ></v-text-field>
            <v-text-field v-model="magicCastle.instances.node.type" label="Node instance type"></v-text-field>
            <v-text-field
              v-model.number="magicCastle.instances.node.count"
              type="number"
              label="Node instance count"
            ></v-text-field>

            <!-- Storage -->
            <v-text-field v-model="magicCastle.storage.type" label="Storage type"></v-text-field>
            <v-text-field
              v-model.number="magicCastle.storage.home_size"
              type="number"
              label="Storage home size (GiB)"
            ></v-text-field>
            <v-text-field
              v-model.number="magicCastle.storage.project_size"
              type="number"
              label="Storage project size (GiB)"
            ></v-text-field>
            <v-text-field
              v-model.number="magicCastle.storage.scratch_size"
              type="number"
              label="Storage scratch size (GiB)"
            ></v-text-field>

            <v-text-field v-model="magicCastle.public_keys[0]" label="Public key"></v-text-field>

            <v-text-field v-model="magicCastle.guest_passwd" label="Guest password (optional)"></v-text-field>

            <v-text-field
              v-model="magicCastle.os_floating_ips[0]"
              @change="osFloatingIpsUpdated"
              label="OpenStack floating IP (optional)"
            ></v-text-field>

            <v-btn type="submit" color="primary" class="text-right" :loading="loading" :disabled="loading" large
            >Spawn
            </v-btn>
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

  const POLL_STATUS_INTERVAL = 1000

  export default {
    name: "ClusterEditor",

    data: function () {
      return {
        loading: false,
        successDialog: false,
        errorDialog: false,
        errorMessage: '',
        magicCastle: {
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
          public_keys: ["ssh-rsa ..."],
          guest_passwd: "",
          os_floating_ips: []
        }
      }
    },
    methods: {
      osFloatingIpsUpdated() {
        // When the floating IP text field is empty, we need to empty the floating IPs array
        if (this.magicCastle.os_floating_ips[0] === '') {
          this.magicCastle.os_floating_ips = []
        }
      },
      showSuccess() {
        this.loading = false
        this.successDialog = true
      },
      showError(message) {
        this.loading = false
        this.errorDialog = true
        this.errorMessage = message
      },
      async createCluster() {
        this.loading = true

        try {
          // Magic Castle cluster creation request
          let creationResponse = await fetch(API_URL + '/magic-castle',
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(this.magicCastle)
            }
          )
          if (!creationResponse.ok)
            throw 'You provided one or many invalid cluster parameters.'

          // Magic Castle cluster status polling
          let statusFetcher = async () => {
            let statusResponse = await fetch(
              API_URL + '/magic-castle/' + this.magicCastle.cluster_name + '/status'
            )
            const {status} = await statusResponse.json()

            if (status !== ClusterStatusCode.BUILD_RUNNING) {
              clearInterval(statusPoller)
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
                default:
                  this.showError('An unexpected status code was sent by the server: ' + status)
              }
            }
          }
          let statusPoller = setInterval(statusFetcher, POLL_STATUS_INTERVAL)

        } catch (e) {
          this.showError(e.message)
        }
      }
    }
  }
</script>

<style scoped>

</style>