import { Download } from "lucide-react";
import { useState } from "react";

import { downloadBookingPdf } from "../../api/bookings.js";
import { downloadBlob } from "../../utils/download.js";
import { getApiErrorMessage } from "../../utils/errors.js";
import Button from "../common/Button.jsx";
import ErrorMessage from "../common/ErrorMessage.jsx";

export default function PdfDownloadButton({
  bookingId,
  filename,
  size = "sm",
  variant = "secondary",
  className = "",
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    if (!bookingId) {
      return;
    }

    setError("");
    setIsDownloading(true);

    try {
      const blob = await downloadBookingPdf(bookingId);
      downloadBlob(blob, filename || `eventhub-booking-${bookingId}.pdf`);
    } catch (requestError) {
      setError(
        getApiErrorMessage(requestError, "Unable to download PDF ticket."),
      );
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className={className}>
      <Button
        size={size}
        variant={variant}
        onClick={handleDownload}
        disabled={isDownloading || !bookingId}
      >
        <Download className="h-4 w-4" aria-hidden="true" />
        {isDownloading ? "Downloading..." : "Download PDF ticket"}
      </Button>
      {error ? <div className="mt-3"><ErrorMessage message={error} /></div> : null}
    </div>
  );
}
