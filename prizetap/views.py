from django.shortcuts import get_object_or_404
import rest_framework.exceptions
from rest_framework.response import Response
from rest_framework.generics import ListAPIView,CreateAPIView
from rest_framework.permissions import IsAuthenticated
from authentication.models import NetworkTypes
from .models import Raffle, RaffleEntry
from .serializers import RaffleSerializer, RaffleEntrySerializer
from .utils import create_uint32_random_nonce
from .validators import has_weekly_credit_left

from permissions.models import Permission


class RaffleListView(ListAPIView):
    queryset = Raffle.objects.filter(is_active=True)
    serializer_class = RaffleSerializer

class RaffleEnrollmentView(CreateAPIView):
    permission_classes = [IsAuthenticated]

    def can_enroll_in_raffle(self, raffle: Raffle):
        if not raffle.is_claimable:
            raise rest_framework.exceptions.PermissionDenied(
                "Can't enroll in this raffle"
            )
        
    def check_user_permissions(self, raffle: Raffle, user_profile):
        for permission in raffle.permissions.all():
            permission: Permission
            if not permission.is_valid(
                user_profile, raffle=raffle
            ):
                raise rest_framework.exceptions.PermissionDenied(
                    permission.response()
                    if permission.response() is not None
                    else "You do not have permission to enroll in this raffle"
                )

    def check_user_weekly_credit(self, user_profile):
        if not has_weekly_credit_left(user_profile):
            raise rest_framework.exceptions.PermissionDenied(
                "You have reached your weekly enrollment limit"
            )

    def check_user_has_wallet(self, user_profile):
        if not user_profile.wallets.filter(wallet_type=NetworkTypes.EVM).exists():
            raise rest_framework.exceptions.PermissionDenied(
                "You have not connected an EVM wallet to your account"
            )

    def post(self, request, pk):
        user_profile = request.user.profile
        raffle = get_object_or_404(Raffle, pk=pk)
        
        self.can_enroll_in_raffle(raffle)

        self.check_user_weekly_credit(user_profile)

        self.check_user_permissions(raffle, user_profile)

        self.check_user_has_wallet(user_profile)

        nonce = create_uint32_random_nonce()

        raffle_entry = RaffleEntry.objects.create(
            user_profile=user_profile,
            nonce=nonce,
            signature=raffle.generate_signature(
                user_profile.wallets.get(wallet_type=NetworkTypes.EVM).address, nonce
            ),
            raffle=raffle,
        )

        return Response(
            {
                "detail": "Signature Created Successfully",
                "signature": RaffleEntrySerializer(raffle_entry).data,
            },
            status=200,
        )
