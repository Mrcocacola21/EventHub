import { useEffect, useState } from "react";

import { datetimeLocalToIso, toDatetimeLocal } from "../../utils/datetime.js";
import Button from "../common/Button.jsx";
import ErrorMessage from "../common/ErrorMessage.jsx";
import Input from "../common/Input.jsx";

function buildInitialForm(initialValues) {
  return {
    name: initialValues?.name || "",
    description: initialValues?.description || "",
    price: initialValues?.price ?? "",
    quantity: initialValues?.quantity ?? "",
    sales_start: toDatetimeLocal(initialValues?.sales_start),
    sales_end: toDatetimeLocal(initialValues?.sales_end),
    is_active: initialValues?.is_active ?? true,
  };
}

function validateForm(form, soldCount = 0) {
  const errors = {};

  if (!form.name.trim()) errors.name = "Name is required.";
  if (form.price === "" || Number(form.price) < 0) {
    errors.price = "Price must be greater than or equal to zero.";
  }
  if (!form.quantity || Number(form.quantity) <= 0) {
    errors.quantity = "Quantity must be greater than zero.";
  }
  if (Number(form.quantity) < soldCount) {
    errors.quantity = "Quantity cannot be lower than sold tickets.";
  }
  if (
    form.sales_start &&
    form.sales_end &&
    new Date(form.sales_end) <= new Date(form.sales_start)
  ) {
    errors.sales_end = "Sales end must be after sales start.";
  }

  return errors;
}

function buildPayload(form) {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    price: form.price === "" ? "0" : String(form.price),
    quantity: Number(form.quantity),
    sales_start: form.sales_start ? datetimeLocalToIso(form.sales_start) : null,
    sales_end: form.sales_end ? datetimeLocalToIso(form.sales_end) : null,
    is_active: Boolean(form.is_active),
  };
}

export default function TicketTypeForm({
  initialValues,
  onSubmit,
  onCancel,
  submitLabel = "Save ticket type",
  isSubmitting = false,
  apiError = "",
}) {
  const [form, setForm] = useState(() => buildInitialForm(initialValues));
  const [validationErrors, setValidationErrors] = useState({});
  const soldCount = Number(initialValues?.sold_count || 0);

  useEffect(() => {
    setForm(buildInitialForm(initialValues));
  }, [initialValues]);

  function updateField(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
    setValidationErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = validateForm(form, soldCount);
    setValidationErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit(buildPayload(form));
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <ErrorMessage message={apiError} />
      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Name"
          name="name"
          value={form.name}
          onChange={updateField}
          error={validationErrors.name}
        />
        <Input
          label="Price"
          name="price"
          type="number"
          min="0"
          step="0.01"
          value={form.price}
          onChange={updateField}
          error={validationErrors.price}
        />
      </div>

      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">
          Description
        </span>
        <textarea
          name="description"
          value={form.description}
          onChange={updateField}
          rows={3}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
        />
      </label>

      <div className="grid gap-4 md:grid-cols-3">
        <Input
          label="Quantity"
          name="quantity"
          type="number"
          min={Math.max(1, soldCount)}
          value={form.quantity}
          onChange={updateField}
          error={validationErrors.quantity}
        />
        <Input
          label="Sales start"
          name="sales_start"
          type="datetime-local"
          value={form.sales_start}
          onChange={updateField}
        />
        <Input
          label="Sales end"
          name="sales_end"
          type="datetime-local"
          value={form.sales_end}
          onChange={updateField}
          error={validationErrors.sales_end}
        />
      </div>

      <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
        <input
          type="checkbox"
          name="is_active"
          checked={form.is_active}
          onChange={updateField}
          className="h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-slate-400"
        />
        Active for sale
      </label>

      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}
