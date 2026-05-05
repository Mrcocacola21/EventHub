import { useEffect, useState } from "react";

import Badge from "../components/common/Badge.jsx";
import Button from "../components/common/Button.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import Input from "../components/common/Input.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { getApiErrorMessage } from "../utils/errors.js";

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [form, setForm] = useState({
    username: "",
    bio: "",
    phone: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setForm({
      username: user?.username || "",
      bio: user?.profile?.bio || "",
      phone: user?.profile?.phone || "",
    });
  }, [user]);

  function updateField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      await updateProfile({
        username: form.username,
        profile: {
          bio: form.bio,
          phone: form.phone,
        },
      });
      setMessage("Profile updated.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to update profile."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h1 className="text-2xl font-semibold text-slate-950">Profile</h1>
        <dl className="mt-5 space-y-4 text-sm">
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="mt-1 font-medium text-slate-950">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Role</dt>
            <dd className="mt-1">
              <Badge variant="info">{user?.role || "USER"}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Verified</dt>
            <dd className="mt-1 text-slate-950">
              {user?.is_verified ? "Yes" : "No"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-950">Basic settings</h2>
        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <ErrorMessage message={error} />
          {message ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {message}
            </div>
          ) : null}
          <Input
            label="Username"
            name="username"
            value={form.username}
            onChange={updateField}
          />
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Bio
            </span>
            <textarea
              name="bio"
              value={form.bio}
              onChange={updateField}
              rows={4}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
            />
          </label>
          <Input
            label="Phone"
            name="phone"
            value={form.phone}
            onChange={updateField}
          />
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save profile"}
          </Button>
        </form>
      </section>
    </div>
  );
}
