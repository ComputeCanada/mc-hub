from enum import Enum


class AuthType(Enum):
    SAML = "SAML"
    TOKEN = "TOKEN"
    NONE = "NONE"
