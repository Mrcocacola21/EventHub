import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";

import { formatDateTime, formatPrice } from "../../utils/formatters.js";
import Badge from "../common/Badge.jsx";
import Button from "../common/Button.jsx";
import TicketTypeForm from "./TicketTypeForm.jsx";

export default function TicketTypeTable({
  tickets = [],
  onUpdate,
  onDelete,
  updatingId,
  deletingId,
  updateError = "",
}) {
  const [editingId, setEditingId] = useState(null);

  async function handleUpdate(ticket, payload) {
    await onUpdate(ticket, payload);
    setEditingId(null);
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Ticket</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Sales window</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {tickets.map((ticket) => (
              <tr key={ticket.id} className="align-top">
                <td className="px-4 py-4">
                  <p className="font-medium text-slate-950">{ticket.name}</p>
                  <p className="mt-1 max-w-xs text-xs text-slate-500">
                    {ticket.description || "No description"}
                  </p>
                  {editingId === ticket.id ? (
                    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <TicketTypeForm
                        initialValues={ticket}
                        onSubmit={(payload) => handleUpdate(ticket, payload)}
                        onCancel={() => setEditingId(null)}
                        submitLabel="Update ticket"
                        isSubmitting={updatingId === ticket.id}
                        apiError={updateError}
                      />
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {formatPrice(ticket.price)}
                </td>
                <td className="px-4 py-4 text-slate-600">
                  <p>{ticket.quantity}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Sold {ticket.sold_count || 0} / Available{" "}
                    {ticket.available_quantity ?? "TBD"}
                  </p>
                </td>
                <td className="px-4 py-4 text-slate-600">
                  <p>{formatDateTime(ticket.sales_start)}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    to {formatDateTime(ticket.sales_end)}
                  </p>
                </td>
                <td className="px-4 py-4">
                  <Badge variant={ticket.is_active ? "success" : "default"}>
                    {ticket.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setEditingId(ticket.id)}
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => onDelete(ticket)}
                      disabled={deletingId === ticket.id}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                      {deletingId === ticket.id ? "Deleting..." : "Delete"}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
