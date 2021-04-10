import { ADJECTIVES, NAMES } from "@/models/petname";

const PASSWORD_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

export const generatePetName = () => {
  const adjective = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)];
  const name = NAMES[Math.floor(Math.random() * NAMES.length)];
  return `${adjective}-${name}`;
};

export const generatePassword = (options = { length: 12 }) => {
  let password = "";
  for (let i = 0; i < options.length; i++) {
    password += PASSWORD_CHARSET[Math.floor(Math.random() * PASSWORD_CHARSET.length)];
  }
  return password;
};
