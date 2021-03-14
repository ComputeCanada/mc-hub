# GitHub Actions secret files

This directory contains encrypted files that are decrypted by GitHub actions during the continuous integration workflow. The files are encrypted and decrypted with a single passphrase that is shared amongst the repository maintainers.

### Encrypting a secret file

````shell
gpg --symmetric --cipher-algo AES256 --output ./.github/secrets/clouds.yaml.gpg clouds.yaml
````

### Decrypting a secret file

````shell
gpg --decrypt --output clouds.yaml ./.github/secrets/clouds.yaml.gpg
````