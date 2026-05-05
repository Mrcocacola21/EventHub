export function formatDateTime(value) {
  if (!value) {
    return "Date TBD";
  }

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "Price TBD";
  }

  const amount = Number(value);

  if (Number.isNaN(amount)) {
    return String(value);
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

export const formatMoney = formatPrice;
