import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser, loginUser, logoutUser, registerUser } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const token = localStorage.getItem("agentguard_token");
      const cachedUser = localStorage.getItem("agentguard_user");
      return token && cachedUser ? JSON.parse(cachedUser) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(() => {
    try {
      return Boolean(localStorage.getItem("agentguard_token") && !localStorage.getItem("agentguard_user"));
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!localStorage.getItem("agentguard_token")) {
      setUser(null);
      setLoading(false);
      return;
    }

    // A cached profile lets the workspace render immediately; validate the token
    // in the background and clear the session if the server rejects it.
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);

    getCurrentUser({ signal: controller.signal })
      .then((currentUser) => {
        localStorage.setItem("agentguard_user", JSON.stringify(currentUser));
        setUser(currentUser);
      })
      .catch(() => {
        // apiRequest clears the token on 401; transient network errors should not
        // sign the user out or discard the locally cached profile.
        if (!localStorage.getItem("agentguard_token")) {
          logoutUser();
          setUser(null);
        }
      })
      .finally(() => {
        window.clearTimeout(timeout);
        setLoading(false);
      });
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, []);

  async function register(username, email, password) {
    return registerUser(username, email, password);
  }

  async function login(username, password) {
    const data = await loginUser(username, password);
    setUser(data.user);
    return data;
  }

  function logout() {
    logoutUser();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
