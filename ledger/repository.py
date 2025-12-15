from decimal import Decimal
from uuid import UUID, uuid4

from ledger.models import Transaction, TransactionDirection, TransactionKind
from wallet.models import Wallet


class LedgerRepository:
    def create_transaction(
        self,
        wallet: Wallet,
        direction: TransactionDirection,
        kind: TransactionKind,
        amount: Decimal,
        reference_id: UUID | None = None,
    ) -> Transaction:
        if reference_id is None:
            reference_id = uuid4()

        tx = Transaction.objects.create(
            wallet=wallet,
            direction=direction,
            kind=kind,
            amount=amount,
            reference_id=reference_id,
        )

        return tx
