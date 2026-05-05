import { Link } from "react-router-dom";

import Button from "../components/common/Button.jsx";

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl rounded-lg border border-slate-200 bg-white p-8 text-center">
      <p className="text-sm font-semibold uppercase text-slate-500">404</p>
      <h1 className="mt-3 text-3xl font-semibold text-slate-950">
        Page not found
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        The route does not exist in the EventHub frontend foundation.
      </p>
      <div className="mt-6">
        <Button as={Link} to="/" variant="secondary">
          Back home
        </Button>
      </div>
    </div>
  );
}
