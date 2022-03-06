# JSON Configuration

MC Hub's configuration is mostly stored in a single file named `configuration.json`.

An example `configuration.json` is shown below.

```json
{
  "auth_type": ["NONE"],
  "admins": [],
  "cors_allowed_origins": ["https://mc-hub.example.com"],
  "domains": {
    "calculquebec.cloud": {
      "dns_provider": "cloudflare"
    },
    "c3.ca": {
      "dns_provider": "gcloud"
    }
  },
  "dns_providers": {
    "cloudflare": {
      "magic_castle_configuration": {
        "email": "you@example.com"
      },
      "environment_variables": {
        "CLOUDFLARE_API_TOKEN": "EXAMPLE_TOKEN",
        "CLOUDFLARE_ZONE_API_TOKEN": "EXAMPLE_TOKEN",
        "CLOUDFLARE_DNS_API_TOKEN": "EXAMPLE_TOKEN"
      }
    },
    "gcloud": {
      "magic_castle_configuration": {
        "email": "you@example.com",
        "project": "your-project-id",
        "zone_name": "your-zone-name"
      },
      "environment_variables": {
        "GOOGLE_CREDENTIALS": "/home/mcu/credentials/gcloud-key.json",
        "GCE_SERVICE_ACCOUNT_FILE": "/home/mcu/credentials/gcloud-key.json"
      }
    }
  }
}
```

Here is a description of the purpose of each entry in the configuration.

### `auth_type`

Either `"NONE"` or `"SAML"`.

This entry is set to `"NONE"` by default. This means that your app doesn't require users to be authenticated, or has an authentication mechanism which is hidden from MC Hub. This value is what the vast majority of users should be using.

If you are using a SAML authentication mechanism, you can set `auth_type` to `"SAML"`. In this case, you will need to setup a reverse proxy that sends the following headers (corresponding to LDAP entries) to MC Hub: `eduPersonPrincipalName`, `givenName`, `surname` and `mail`. With SAML authentication, each cluster is owned by a user, represented by its `eduPersonPrincipalName`. For more information on how to setup SAML authentication, read [Adding SAML Authentication and HTTPS to MC Hub](https://github.com/ComputeCanada/magic_castle-ui/wiki/Adding-SAML-Authentication-and-HTTPS-to-Magic-Castle-UI).

### `admins` (optional)

A list of users with administrator rights. This entry is ignored when `auth_type` is set to `"NONE"`.

If `auth_type` is set to `"SAML"`, the values contained in `admins` are strings reprensenting the `eduPersonPrincipalName` attribute of the user. Administrators can view, modify and delete clusters created by any other user.

### `cors_allowed_origins`

A list of origins allowed making HTTP requests to the server. This should be set to the frontend base URL. 

For instance, if you are running MC Hub locally, this may be set to `http://localhost:5000`. If you are running an additional Node development server, you can also add its url, which may look like `http://localhost:8080`. 

Otherwise, if you are running MC Hub in production, the origin url may look like `https://mc.computecanada.dev` (without an explicit port number).

> Note: The * wildcard origin can be used but is not recommended for security reasons. This way, a malicious web page could view and edit your clusters. 

### `domains`

An object where each key represents the domain name and the value represents the domain configuration. Only domains specified in this object can be selected in the UI.

Each domain object can contain an optional `dns_provider` entry.

If `dns_provider` is **provided**, MC Hub will enable the DNS module in Magic Castle, which is required for many features (including JupyterHub, Globus and FreeIPA). The value associated with `dns_provider` must correspond to a configuration in the `dns_providers` object. Here is an example domain with the DNS module enabled:

```json
"example.com": {"dns_provider": "cloudflare"}
```

If `dns_provider` is **not provided**, MC Hub will disable the DNS module in Magic Castle. This is useful if you don't own a domain or have API keys from CloudFlare or Google Cloud to manage one. Here is an example domain with the DNS module disabled:

```json
"example.com": {}
```

### `dns_providers` (optional)

MC Hub supports two DNS providers: Cloudflare and Google cloud.

### `dns_providers.cloudflare.magic_castle_configuration.email`

Your email address. This email is used by Let's Encrypt to send important account notifications regarding your SSL certificate status.

### `dns_providers.cloudflare.environment_variables`

According to [Magic Castle's documentation](https://github.com/ComputeCanada/magic_castle/tree/master/docs#612-cloudflare-api-token), you will need to create a custom API token in the [Cloudflare API tokens page](https://dash.cloudflare.com/profile/api-tokens).

Give the following permissions to the token.

| Section |       Subsection | Permission |
| ------- | ---------------: | ---------: |
| Account | Account Settings |       Read |
| Zone    |    Zone Settings |       Read |
| Zone    |             Zone |       Read |
| Zone    |              DNS |      Write |

Create the token and copy its value in the three environment variables. Here is an example with the token `EXAMPLE_TOKEN`.

```json
{
  "CLOUDFLARE_API_TOKEN": "EXAMPLE_TOKEN",
  "CLOUDFLARE_ZONE_API_TOKEN": "EXAMPLE_TOKEN",
  "CLOUDFLARE_DNS_API_TOKEN": "EXAMPLE_TOKEN"
}
```

### `dns_providers.gcloud.magic_castle_configuration.email`

Your email address. This email is used by Let's Encrypt to send important account notifications regarding your SSL certificate status.

### `dns_providers.gcloud.magic_castle_configuration.project`

The project ID of your Google Cloud project.

### `dns_providers.gcloud.magic_castle_configuration.zone_name`

The name of the Google Cloud managed zone.

### `dns_providers.gcloud.environment_variables`

The environment variables required by Google Cloud refer to the path of the Google Cloud account's JSON key, which is always located in `/home/mcu/credentials/gcloud-key.json` in MC Hub. You don't need to modify this.
