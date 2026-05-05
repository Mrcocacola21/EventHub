import EmptyState from "../common/EmptyState.jsx";
import { getMediaUrl } from "../../utils/media.js";

export default function QrCodeBlock({ qrCode }) {
  if (!qrCode) {
    return (
      <EmptyState
        title="QR code is not available yet"
        description="The backend will generate a QR code for eligible tickets."
      />
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-slate-950">QR code</h2>
      <div className="mt-4 flex justify-center rounded-lg bg-slate-50 p-5">
        <img
          src={getMediaUrl(qrCode)}
          alt="Booking QR code"
          className="h-56 w-56 rounded-md object-contain"
        />
      </div>
    </div>
  );
}
