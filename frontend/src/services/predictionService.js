function formatApiError(error, fallbackMessage) {
  if (typeof error === "string" && error.trim()) return error;

  if (Array.isArray(error)) {
    const messages = error.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item.msg === "string") {
        const location = Array.isArray(item.loc) ? item.loc.at(-1) : "";
        return location ? `${location}: ${item.msg}` : item.msg;
      }
      return null;
    }).filter(Boolean);

    if (messages.length) return messages.join(" ");
  }

  return fallbackMessage;
}

export async function requestPrediction(formValues) {
  const response = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formValues),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(formatApiError(data.error, "Prediction failed. Please check the entered values."));
  }
  return data;
}

export async function fetchDashboard() {
  const response = await fetch("/api/dashboard");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Dashboard request failed.");
  return data;
}

export async function fetchCustomerHistory(customerCode) {
  const response = await fetch(`/api/customers/${encodeURIComponent(customerCode.trim())}`);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Customer lookup failed. Please try again.");
  }
  if (!response.ok) throw new Error(formatApiError(data.error, "Customer lookup failed."));
  return data;
}
