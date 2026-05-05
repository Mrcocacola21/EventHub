from django.http import FileResponse
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .pdf import PDFTicketService
from .permissions import CanUseBookingTicket, IsBookingOwnerOrAdminOrEventOrganizer
from .serializers import BookingCreateSerializer, BookingSerializer
from .services import BookingService, TicketValidationService


@extend_schema_view(
    list=extend_schema(tags=["Bookings"], summary="List accessible bookings"),
    create=extend_schema(
        tags=["Bookings"],
        summary="Create booking",
        description=(
            "Creates a booking atomically. sold_count, price_at_purchase, QR code "
            "and PDF ticket are generated server-side."
        ),
        request=BookingCreateSerializer,
        responses=BookingSerializer,
        examples=[
            OpenApiExample(
                "Create booking",
                value={"ticket_type_id": 1},
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Bookings"], summary="Get booking"),
)
class BookingViewSet(viewsets.ModelViewSet):
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = Booking.objects.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
            "ticket_type__event__category",
        )
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()

        if self.action in ("retrieve", "cancel", "use", "download_pdf"):
            return queryset

        user = self.request.user
        if user.is_superuser or getattr(user, "is_admin_role", False):
            return queryset

        if getattr(user, "is_organizer", False):
            return queryset.filter(
                Q(user=user) | Q(ticket_type__event__organizer=user)
            )

        return queryset.filter(user=user)

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def get_permissions(self):
        if self.action == "use":
            return [CanUseBookingTicket()]
        if self.action in ("retrieve", "cancel", "download_pdf"):
            return [IsBookingOwnerOrAdminOrEventOrganizer()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        output_serializer = BookingSerializer(
            booking,
            context=self.get_serializer_context(),
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Bookings"],
        summary="List current user's bookings",
        responses=BookingSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = BookingSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        serializer = BookingSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Bookings"],
        summary="Cancel booking",
        request=None,
        responses=BookingSerializer,
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        booking = self.get_object()
        booking = BookingService.cancel_booking(
            booking=booking,
            user=request.user,
            request=request,
        )
        serializer = BookingSerializer(
            booking,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Bookings"],
        summary="Use/validate booking ticket",
        description="Only event organizer/admin can validate a paid, unused booking.",
        request=None,
        responses=BookingSerializer,
    )
    @action(detail=True, methods=["post"])
    def use(self, request, *args, **kwargs):
        booking = self.get_object()
        booking = TicketValidationService.use_booking(
            booking_id=booking.id,
            checked_by_user=request.user,
            request=request,
        )
        serializer = BookingSerializer(
            booking,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Bookings"],
        summary="Download PDF ticket",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="PDF ticket file (application/pdf).",
            )
        },
    )
    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request, *args, **kwargs):
        booking = self.get_object()
        if not booking.pdf_ticket:
            PDFTicketService.generate_for_booking(booking)
            booking.refresh_from_db()

        filename = f"booking_{booking.id}_ticket.pdf"
        booking.pdf_ticket.open("rb")
        return FileResponse(
            booking.pdf_ticket,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )
