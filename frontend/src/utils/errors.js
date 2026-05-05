export function getApiErrorMessage(error, fallback = "Something went wrong.") {
  const data = error?.response?.data;
  const status = error?.response?.status;

  if (status === 403 && !data?.detail) {
    return "You do not have permission to perform this action.";
  }

  if (!data) {
    return error?.message || fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  if (data.detail) {
    return data.detail;
  }

  if (Array.isArray(data.non_field_errors)) {
    return data.non_field_errors.join(" ");
  }

  const [firstKey] = Object.keys(data);
  const firstValue = data[firstKey];

  if (!firstKey) {
    return fallback;
  }

  if (Array.isArray(firstValue)) {
    return `${firstKey}: ${firstValue.join(" ")}`;
  }

  if (typeof firstValue === "object" && firstValue !== null) {
    return `${firstKey}: ${JSON.stringify(firstValue)}`;
  }

  return `${firstKey}: ${firstValue}`;
}
