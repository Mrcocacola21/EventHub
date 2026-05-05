import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getCategories } from "../../api/events.js";
import { getListFromResponse } from "../../utils/apiData.js";
import { datetimeLocalToIso, toDatetimeLocal } from "../../utils/datetime.js";
import { getApiErrorMessage } from "../../utils/errors.js";
import { queryKeys } from "../../utils/queryKeys.js";
import Button from "../common/Button.jsx";
import ErrorMessage from "../common/ErrorMessage.jsx";
import Input from "../common/Input.jsx";
import LoadingSpinner from "../common/LoadingSpinner.jsx";

function buildInitialForm(initialValues) {
  return {
    title: initialValues?.title || "",
    description: initialValues?.description || "",
    category: initialValues?.category || initialValues?.category_detail?.id || "",
    location: initialValues?.location || "",
    start_datetime: toDatetimeLocal(initialValues?.start_datetime),
    end_datetime: toDatetimeLocal(initialValues?.end_datetime),
    max_participants: initialValues?.max_participants || "",
    cover_image: null,
  };
}

function validateForm(form) {
  const errors = {};

  if (!form.title.trim()) errors.title = "Title is required.";
  if (!form.description.trim()) errors.description = "Description is required.";
  if (!form.category) errors.category = "Category is required.";
  if (!form.location.trim()) errors.location = "Location is required.";
  if (!form.start_datetime) errors.start_datetime = "Start date is required.";
  if (!form.end_datetime) errors.end_datetime = "End date is required.";

  if (
    form.start_datetime &&
    form.end_datetime &&
    new Date(form.end_datetime) <= new Date(form.start_datetime)
  ) {
    errors.end_datetime = "End date must be after start date.";
  }

  if (
    form.max_participants !== "" &&
    Number(form.max_participants) <= 0
  ) {
    errors.max_participants = "Max participants must be greater than zero.";
  }

  return errors;
}

function buildPayload(form) {
  const basePayload = {
    title: form.title.trim(),
    description: form.description.trim(),
    category: form.category,
    location: form.location.trim(),
    start_datetime: datetimeLocalToIso(form.start_datetime),
    end_datetime: datetimeLocalToIso(form.end_datetime),
    max_participants:
      form.max_participants === "" ? null : Number(form.max_participants),
  };

  if (!form.cover_image) {
    return basePayload;
  }

  const formData = new FormData();
  Object.entries(basePayload).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  });
  formData.append("cover_image", form.cover_image);
  return formData;
}

export default function EventForm({
  initialValues,
  onSubmit,
  submitLabel = "Save event",
  isSubmitting = false,
  apiError = "",
}) {
  const [form, setForm] = useState(() => buildInitialForm(initialValues));
  const [validationErrors, setValidationErrors] = useState({});

  useEffect(() => {
    setForm(buildInitialForm(initialValues));
  }, [initialValues]);

  const categoriesQuery = useQuery({
    queryKey: queryKeys.categories,
    queryFn: getCategories,
  });

  const categories = useMemo(
    () => getListFromResponse(categoriesQuery.data),
    [categoriesQuery.data],
  );

  function updateField(event) {
    const { name, value, files } = event.target;
    setForm((current) => ({
      ...current,
      [name]: files ? files[0] || null : value,
    }));
    setValidationErrors((current) => ({ ...current, [name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = validateForm(form);
    setValidationErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit(buildPayload(form));
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <ErrorMessage message={apiError} />
      {categoriesQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            categoriesQuery.error,
            "Unable to load categories.",
          )}
        />
      ) : null}

      <Input
        label="Title"
        name="title"
        value={form.title}
        onChange={updateField}
        error={validationErrors.title}
      />

      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">
          Description
        </span>
        <textarea
          name="description"
          value={form.description}
          onChange={updateField}
          rows={5}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
        />
        {validationErrors.description ? (
          <span className="mt-1 block text-sm text-red-600">
            {validationErrors.description}
          </span>
        ) : null}
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Category
          </span>
          <select
            name="category"
            value={form.category}
            onChange={updateField}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            <option value="">Select category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
          {validationErrors.category ? (
            <span className="mt-1 block text-sm text-red-600">
              {validationErrors.category}
            </span>
          ) : null}
        </label>
        <Input
          label="Location"
          name="location"
          value={form.location}
          onChange={updateField}
          error={validationErrors.location}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Start date"
          name="start_datetime"
          type="datetime-local"
          value={form.start_datetime}
          onChange={updateField}
          error={validationErrors.start_datetime}
        />
        <Input
          label="End date"
          name="end_datetime"
          type="datetime-local"
          value={form.end_datetime}
          onChange={updateField}
          error={validationErrors.end_datetime}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Max participants"
          name="max_participants"
          type="number"
          min="1"
          value={form.max_participants}
          onChange={updateField}
          error={validationErrors.max_participants}
        />
        <Input
          label="Cover image"
          name="cover_image"
          type="file"
          accept="image/*"
          onChange={updateField}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting || categoriesQuery.isLoading}>
          {isSubmitting ? "Saving..." : submitLabel}
        </Button>
        {categoriesQuery.isLoading ? (
          <LoadingSpinner label="Loading categories" />
        ) : null}
      </div>
    </form>
  );
}
