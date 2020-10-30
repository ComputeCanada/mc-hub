terraform {
  required_version = ">= 0.12.21"
}

module "openstack" {
  source = "/home/mcu/magic_castle-openstack-8.3/openstack"
  generate_ssh_key = true
  puppetenv_rev = "8.3"

  cluster_name = "missingnodes"
  domain       = "sub.example.com"
  image        = "CentOS-7-x64-2019-07"
  nb_users     = 10

  instances = {
    mgmt  = { type = "p4-6gb", count = 1 }
    login = { type = "p4-6gb", count = 1 }
    node  = [{ type = "p2-3gb", count = 1 }]
  }

  storage = {
    type         = "nfs"
    home_size    = 100
    project_size = 50
    scratch_size = 50
  }

  public_keys = []

  # Shared password, randomly chosen if blank
  guest_passwd = ""

  # OpenStack specific
  os_floating_ips = []
}

output "sudoer_username" {
  value = module.openstack.sudoer_username
}

output "guest_usernames" {
  value = module.openstack.guest_usernames
}

output "guest_passwd" {
  value = module.openstack.guest_passwd
}

output "public_ip" {
  value = module.openstack.ip
}

## Uncomment to register your domain name with CloudFlare
# module "dns" {
#   source           = "/home/mcu/magic_castle-openstack-6.4/dns/cloudflare"
#   email            = "you@example.com"
#   name             = module.openstack.cluster_name
#   domain           = module.openstack.domain
#   public_ip        = module.openstack.ip
#   rsa_public_key   = module.openstack.rsa_public_key
#   sudoer_username  = module.openstack.sudoer_username
# }

## Uncomment to register your domain name with Google Cloud
# module "dns" {
#   source           = "/home/mcu/magic_castle-openstack-6.4/dns/gcloud"
#   email            = "you@example.com"
#   project          = "your-project-name"
#   zone_name        = "you-zone-name"
#   name             = module.openstack.cluster_name
#   domain           = module.openstack.domain
#   public_ip        = module.openstack.ip
#   rsa_public_key   = module.openstack.rsa_public_key
#   sudoer_username  = module.openstack.sudoer_username
# }

# output "hostnames" {
#   value = module.dns.hostnames
# }
