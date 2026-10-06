export function usernameError(value) {
  const username = value.trim();
  if (username.includes("@")) {
    return "Enter your username, not your email address. Use the username you chose when registering.";
  }
  if (username.length < 3 || username.length > 60) {
    return "Your username must be between 3 and 60 characters.";
  }
  if (!/^[a-zA-Z0-9_.-]+$/.test(username)) {
    return "Your username can contain only letters, numbers, dots, underscores, and hyphens.";
  }
  return "";
}
