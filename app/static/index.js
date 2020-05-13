const API_URL = 'http://localhost:5000/api'
const IDLE_STATUS = 'idle', RUNNING_STATUS = 'running', SUCCESS_STATUS = 'success', ERROR_STATUS = 'error'
const POLL_STATUS_INTERVAL = 1000

new Vue({
    el: '#app',
    vuetify: new Vuetify(),
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
                // Magic Castle creation request
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
                    throw new Error('You provided one or many invalid cluster parameters.')

                // Magic Castle status polling
                let statusFetcher = async () => {
                    let statusResponse = await fetch(
                        API_URL + '/magic-castle/' + this.magicCastle.cluster_name + '/status'
                    )
                    const {status} = await statusResponse.json()
                    if (status !== RUNNING_STATUS) {
                        clearInterval(statusPoller)
                        switch (status) {
                            case SUCCESS_STATUS:
                                this.showSuccess()
                                break
                            case IDLE_STATUS:
                                this.showError('The server is still idle')
                                break
                            case ERROR_STATUS:
                                this.showError('Terraform returned an error while creating the cluster.')
                                break
                            default:
                                this.showError('An unknown status code was sent by the server')
                        }
                    }
                }
                let statusPoller = setInterval(statusFetcher, POLL_STATUS_INTERVAL)

            } catch (e) {
                this.showError(e.message)
            }
        }
    }
})