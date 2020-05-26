terraform {
  required_version = ">= 0.12.21"
}

module "openstack" {
  source = "{{ magic_castle_release_path }}/openstack"

  cluster_name = "{{ cluster_name }}"
  domain       = "{{ domain }}"
  image        = "{{ image }}"
  nb_users     = {{ nb_users }}

  instances = {
    {% for category, instance in instances.items() %}
      {% if category == 'node' %}
        {{ category }} = [ { type = "{{ instance.type }}", count = {{ instance.count }} } ]
      {% else %}
        {{ category }} = { type = "{{ instance.type }}", count = {{ instance.count }} }
      {% endif %}
    {% endfor %}
  }

  storage = {
    type         = "{{ storage.type }}"
    home_size    = {{ storage.home_size }}
    project_size = {{ storage.project_size }}
    scratch_size = {{ storage.scratch_size }}
  }

  public_keys = [
    "{{ public_keys | join('", "') }}"
  ]

  # Shared password, randomly chosen if blank
  guest_passwd = "{{ guest_passwd }}"

  # OpenStack specific
  os_floating_ips = [
    {% if os_floating_ips | length > 0 %}
      "{{ os_floating_ips | join('", "') }}"
    {% endif %}
  ]
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
#   source           = "{{ magic_castle_release_path }}/dns/cloudflare"
#   email            = "you@example.com"
#   name             = module.openstack.cluster_name
#   domain           = module.openstack.domain
#   public_ip        = module.openstack.ip
#   rsa_public_key   = module.openstack.rsa_public_key
#   sudoer_username  = module.openstack.sudoer_username
# }

## Uncomment to register your domain name with Google Cloud
# module "dns" {
#   source           = "{{ magic_castle_release_path }}/dns/gcloud"
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
