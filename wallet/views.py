from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from wallet.serializers import TransferSerializer
from wallet.service import WalletService


class TransferAPIView(APIView):
    """
    POST /api/transfer
    {
        "wallet_from": "<uuid>",
        "wallet_to": "<uuid>",
        "amount": "100.50"
    }
    """

    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = WalletService()

        try:
            service.transfer(
                wallet_id_from=data["wallet_from"],
                wallet_id_to=data["wallet_to"],
                amount=data["amount"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Transfer successful"}, status=status.HTTP_200_OK)
