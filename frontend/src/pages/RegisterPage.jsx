import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import Button from "../components/common/Button.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import Input from "../components/common/Input.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { getApiErrorMessage } from "../utils/errors.js";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, register } = useAuth();
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    password_confirm: "",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isLoading) {
    return <LoadingSpinner label="Checking session" />;
  }

  if (isAuthenticated) {
    return <Navigate to="/profile" replace />;
  }

  function updateField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await register(form);
      navigate("/profile", { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to create account."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-950">Register</h1>
        <p className="mt-2 text-sm text-slate-600">
          Create a basic EventHub user account.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <ErrorMessage message={error} />
          <Input
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={updateField}
            required
          />
          <Input
            label="Username"
            name="username"
            autoComplete="username"
            value={form.username}
            onChange={updateField}
          />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={updateField}
            required
          />
          <Input
            label="Confirm password"
            name="password_confirm"
            type="password"
            autoComplete="new-password"
            value={form.password_confirm}
            onChange={updateField}
            required
          />
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>
      </div>
    </div>
  );
}
