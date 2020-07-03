const PASSWORD_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

export const generatePassword = (options = { length: 12 }) => {
    let password = "";
    for (let i = 0; i < options.length; i++) {
        password += PASSWORD_CHARSET[Math.floor(Math.random() * PASSWORD_CHARSET.length)];
    }
    return password;
}