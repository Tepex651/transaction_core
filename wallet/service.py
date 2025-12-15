from decimal import Decimal
from uuid import UUID

from django.db import transaction

from ledger.models import TransactionDirection, TransactionKind
from ledger.repository import LedgerRepository
from wallet.repository import WalletRepository
from wallet.tasks import send_fake_notification

COMMISSION_THRESHOLD = Decimal("1000")
COMMISSION_PERCENT = Decimal("10")

ADMIN_WALLET_ID = "4e5dbe06-9776-476a-893a-a6ff090b49d9"


class WalletService:
    def __init__(
        self,
        repository: WalletRepository | None = None,
        ledger_repository: LedgerRepository | None = None,
    ) -> None:
        self.repository = repository or WalletRepository()
        self.ledger_repository = ledger_repository or LedgerRepository()

    def transfer(self, wallet_id_from: UUID, wallet_id_to: UUID, amount: Decimal):
        # Calculate commission
        commission = Decimal("0")
        if amount > COMMISSION_THRESHOLD:
            commission = (amount * COMMISSION_PERCENT / Decimal("100")).quantize(
                Decimal("0.01")
            )

        # Total amount to debit from sender
        total_debit = amount + commission

        with transaction.atomic():
            # Atomically check balance and debit sender
            if not self.repository.decrement_balance_if_enough(
                wallet_id_from, total_debit
            ):
                raise ValueError("Insufficient balance")

            # Credit receiver with transfer amount
            self.repository.increment_balance(wallet_id_to, amount)

            wallet_from = self.repository.get_by_id(wallet_id_from)
            wallet_to = self.repository.get_by_id(wallet_id_to)

            # Main transfer transaction (sender → receiver)
            tx_debit = self.ledger_repository.create_transaction(
                wallet=wallet_from,
                direction=TransactionDirection.DEBIT,
                kind=TransactionKind.TRANSFER,
                amount=amount,
            )

            if commission > 0:
                # Fee debit from sender
                self.ledger_repository.create_transaction(
                    wallet=wallet_from,
                    direction=TransactionDirection.DEBIT,
                    kind=TransactionKind.FEE,
                    amount=commission,
                    reference_id=tx_debit.reference_id,
                )

                # Fee credit to admin/system wallet
                admin_wallet = self.repository.get_by_id(UUID(ADMIN_WALLET_ID))
                self.repository.increment_balance(UUID(ADMIN_WALLET_ID), commission)
                self.ledger_repository.create_transaction(
                    wallet=admin_wallet,
                    direction=TransactionDirection.CREDIT,
                    kind=TransactionKind.FEE,
                    amount=commission,
                    reference_id=tx_debit.reference_id,
                )

            # Credit receiver
            self.ledger_repository.create_transaction(
                wallet=wallet_to,
                direction=TransactionDirection.CREDIT,
                kind=TransactionKind.TRANSFER,
                amount=amount,
                reference_id=tx_debit.reference_id,
            )

        # Notification
        send_fake_notification.delay(str(wallet_id_to), f"Received {amount}")
