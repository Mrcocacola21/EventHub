import { useState } from "react";
import { SearchCheck } from "lucide-react";

import Button from "../common/Button.jsx";
import Input from "../common/Input.jsx";

export default function QrCheckForm({ onCheck, isChecking = false }) {
  const [value, setValue] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    onCheck(value.trim());
  }

  return (
    <form
      className="rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={handleSubmit}
    >
      <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
        <Input
          label="Booking ID or QR token"
          name="qr_value"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Enter numeric booking ID"
        />
        <Button type="submit" disabled={isChecking || !value.trim()}>
          <SearchCheck className="h-4 w-4" aria-hidden="true" />
          {isChecking ? "Checking..." : "Check ticket"}
        </Button>
      </div>
    </form>
  );
}
