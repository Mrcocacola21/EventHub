from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .qr import QRCodeService


class PDFTicketService:
    @classmethod
    def generate_for_booking(cls, booking, force=False):
        if booking.pdf_ticket and not force:
            return booking.pdf_ticket

        if not booking.qr_code:
            QRCodeService.generate_for_booking(booking)
            booking.refresh_from_db()

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 60

        pdf.setTitle(f"EventHub Ticket #{booking.id}")
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, y, "EventHub Ticket")
        y -= 40

        event = booking.ticket_type.event
        lines = [
            ("Booking ID", booking.id),
            ("Event title", event.title),
            ("Event start", cls._format_datetime(event.start_datetime)),
            ("Event end", cls._format_datetime(event.end_datetime)),
            ("Event location", event.location),
            ("Ticket type", booking.ticket_type.name),
            ("Price at purchase", f"{booking.price_at_purchase}"),
            ("User email", booking.user.email),
            ("Booking status", booking.status),
            ("Is used", "Yes" if booking.is_used else "No"),
            ("Created at", cls._format_datetime(booking.created_at)),
        ]

        pdf.setFont("Helvetica", 11)
        for label, value in lines:
            pdf.drawString(50, y, f"{label}: {value}")
            y -= 20

        if booking.qr_code:
            qr_image = cls._read_qr_image(booking)
            if qr_image is not None:
                pdf.drawImage(
                    qr_image,
                    50,
                    max(y - 180, 80),
                    width=160,
                    height=160,
                    preserveAspectRatio=True,
                    mask="auto",
                )

        pdf.showPage()
        pdf.save()

        if booking.pdf_ticket and force:
            booking.pdf_ticket.delete(save=False)

        booking.pdf_ticket.save(
            f"booking_{booking.id}_ticket.pdf",
            ContentFile(buffer.getvalue()),
            save=True,
        )
        return booking.pdf_ticket

    @staticmethod
    def _format_datetime(value):
        if not value:
            return ""
        return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _read_qr_image(booking):
        try:
            booking.qr_code.open("rb")
            return ImageReader(BytesIO(booking.qr_code.read()))
        finally:
            booking.qr_code.close()
