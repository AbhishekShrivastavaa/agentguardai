const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

function errorMessage(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join("; ");
  return fallback;
}

// Common API request handler
async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("agentguard_token");

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("agentguard_token");
    }

    throw new Error(errorMessage(data, `Request failed: HTTP ${response.status}`));
  }

  return data;
}

// Authentication
export async function registerUser(username, email, password) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export async function loginUser(username, password) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(errorMessage(data, "Login failed"));
  }

  if (typeof data.access_token !== "string" || !data.access_token) {
    throw new Error("Login succeeded, but the server did not return a session token.");
  }

  try {
    localStorage.setItem("agentguard_token", data.access_token);
    if (data.user && typeof data.user === "object") {
      localStorage.setItem("agentguard_user", JSON.stringify(data.user));
    }
  } catch {
    throw new Error("Your browser could not save the sign-in session. Enable site storage and try again.");
  }
  return data;
}

export async function getCurrentUser(options = {}) {
  return apiRequest("/auth/me", options);
}

export function logoutUser() {
  localStorage.removeItem("agentguard_token");
  localStorage.removeItem("agentguard_user");
}

// AI Security Gateway
export async function scanPrompt(prompt, useAI = true, conversation = [], options = {}) {
  return apiRequest("/gateway/scan", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      use_ai: useAI,
      conversation,
      ...options,
    }),
  });
}

export async function evaluateAgentAction(request) {
  return apiRequest("/gateway/actions/evaluate", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function reviewAgentAction(eventId, decision, reviewer = "workspace reviewer") {
  return apiRequest(`/gateway/actions/${eventId}/${decision}`, {
    method: "POST",
    body: JSON.stringify({ reviewer }),
  });
}

// Security Events
export async function getSecurityEvents() {
  return apiRequest("/events/");
}

export async function getInventory(category) {
  const result = await apiRequest(`/inventory/${category}`);
  return result.items || [];
}

export async function createInventoryItem(category, item) {
  const { name, ...data } = item;
  return apiRequest(`/inventory/${category}`, { method: "POST", body: JSON.stringify({ name, data }) });
}

export async function updateInventoryItem(category, item) {
  const { name, registry_id, category: ignoredCategory, ...data } = item;
  return apiRequest(`/inventory/${category}/${registry_id}`, { method: "PUT", body: JSON.stringify({ name, data }) });
}

export async function deleteInventoryItem(category, registryId) {
  return apiRequest(`/inventory/${category}/${registryId}`, { method: "DELETE" });
}

// Security Policies
export async function getPolicies() {
  return apiRequest("/policies/");
}

export async function createPolicy(policy) {
  return apiRequest("/policies/", {
    method: "POST",
    body: JSON.stringify(policy),
  });
}

export async function updatePolicy(id, policy) {
  return apiRequest(`/policies/${id}`, {
    method: "PUT",
    body: JSON.stringify(policy),
  });
}

export async function deletePolicy(id) {
  return apiRequest(`/policies/${id}`, {
    method: "DELETE",
  });
}

export async function getGatewayPolicyConfig() {
  return apiRequest("/gateway/policy-config");
}

export async function saveGatewayPolicyConfig(config) {
  return apiRequest("/gateway/policy-config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

// Backend Health
export async function getBackendHealth() {
  return apiRequest("/health");
}
