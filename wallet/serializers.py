from decimal import Decimal

from rest_framework import serializers


class TransferSerializer(serializers.Serializer):
    wallet_from = serializers.UUIDField()
    wallet_to = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate_amount(self, value: Decimal):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value
