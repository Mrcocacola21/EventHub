import { Link } from "react-router-dom";

import Button from "../components/common/Button.jsx";

export default function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-xl rounded-lg border border-amber-200 bg-amber-50 p-8 text-center">
      <p className="text-sm font-semibold uppercase text-amber-700">403</p>
      <h1 className="mt-3 text-3xl font-semibold text-amber-950">
        Access denied
      </h1>
      <p className="mt-3 text-sm leading-6 text-amber-800">
        You do not have permission to access this organizer workspace.
      </p>
      <div className="mt-6">
        <Button as={Link} to="/" variant="secondary">
          Back home
        </Button>
      </div>
    </div>
  );
}
