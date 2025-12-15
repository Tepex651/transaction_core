from decimal import Decimal
from uuid import UUID

from django.db.models import F

from wallet.models import Wallet


class WalletRepository:
    def get_by_id_with_lock(self, id: UUID) -> Wallet:
        return Wallet.objects.select_for_update().get(id=id)

    def decrement_balance_if_enough(self, id: UUID, amount: Decimal) -> bool:
        updated_count = Wallet.objects.filter(id=id, balance__gte=amount).update(
            balance=F("balance") - amount
        )

        return updated_count > 0

    def increment_balance(self, id: UUID, amount: Decimal) -> None:
        Wallet.objects.filter(id=id).update(balance=F("balance") + amount)

    def get_by_id(self, id: UUID) -> Wallet:
        return Wallet.objects.get(id=id)
