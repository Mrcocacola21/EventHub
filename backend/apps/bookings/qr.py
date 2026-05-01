from io import BytesIO

import qrcode
from django.core import signing
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError


class QRCodeService:
    @classmethod
    def build_token(cls, booking):
        payload = {
            "booking_id": booking.id,
            "user_id": booking.user_id,
            "ticket_type_id": booking.ticket_type_id,
        }
        return signing.dumps(payload)

    @classmethod
    def generate_for_booking(cls, booking, force=False):
        if booking.qr_code and not force:
            return booking.qr_code

        token = cls.build_token(booking)
        image = qrcode.make(token)
        buffer = BytesIO()
        image.save(buffer, format="PNG")

        if booking.qr_code and force:
            booking.qr_code.delete(save=False)

        booking.qr_code.save(
            f"booking_{booking.id}_qr.png",
            ContentFile(buffer.getvalue()),
            save=True,
        )
        return booking.qr_code

    @staticmethod
    def parse_token(token):
        try:
            return signing.loads(token)
        except signing.BadSignature as exc:
            raise ValidationError("Invalid QR token.") from exc
