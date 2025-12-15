from decimal import Decimal
from uuid import UUID

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from ledger.models import Transaction, TransactionDirection, TransactionKind
from ledger.repository import LedgerRepository
from wallet.models import Wallet
from wallet.repository import WalletRepository
from wallet.service import ADMIN_WALLET_ID, COMMISSION_PERCENT, COMMISSION_THRESHOLD, WalletService


class WalletServiceTest(TestCase):
    def setUp(self):
        self.wallet1 = Wallet.objects.create(balance=Decimal("100.00"))
        self.wallet2 = Wallet.objects.create(balance=Decimal("50.00"))

        self.service = WalletService(
            repository=WalletRepository(), ledger_repository=LedgerRepository()
        )

    def test_successful_transfer(self):
        amount = Decimal("30.00")
        self.service.transfer(
            wallet_id_from=self.wallet1.id, wallet_id_to=self.wallet2.id, amount=amount
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()

        self.assertEqual(self.wallet1.balance, Decimal("70.00"))
        self.assertEqual(self.wallet2.balance, Decimal("80.00"))

        tx_debit = Transaction.objects.get(
            wallet=self.wallet1, direction=TransactionDirection.DEBIT, kind=TransactionKind.TRANSFER,
        )
        tx_credit = Transaction.objects.get(
            wallet=self.wallet2, direction=TransactionDirection.CREDIT, kind=TransactionKind.TRANSFER,
        )
        self.assertEqual(tx_debit.amount, amount)
        self.assertEqual(tx_credit.amount, amount)
        self.assertEqual(tx_credit.reference_id, tx_debit.reference_id)

    def test_insufficient_balance(self):
        amount = Decimal("200.00")
        with self.assertRaises(ValueError) as context:
            self.service.transfer(
                wallet_id_from=self.wallet1.id,
                wallet_id_to=self.wallet1.id,
                amount=amount,
            )
        self.assertEqual(str(context.exception), "Insufficient balance")

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()
        self.assertEqual(self.wallet1.balance, Decimal("100.00"))
        self.assertEqual(self.wallet2.balance, Decimal("50.00"))

        self.assertFalse(Transaction.objects.exists())

    def test_transfer_with_commission_to_admin_wallet(self):
        """
        amount > COMMISSION_THRESHOLD
        commission should be debited from sender
        and credited to admin wallet
        """

        # Arrange
        sender = Wallet.objects.create(balance=Decimal("2000.00"))
        receiver = Wallet.objects.create(balance=Decimal("100.00"))

        admin_wallet = Wallet.objects.create(
            id=UUID(ADMIN_WALLET_ID),
            balance=Decimal("0.00"),
        )

        service = WalletService(
            repository=WalletRepository(),
            ledger_repository=LedgerRepository(),
        )

        amount = Decimal("1500.00")
        self.assertGreater(amount, COMMISSION_THRESHOLD)

        commission = (
            amount * COMMISSION_PERCENT / Decimal("100")
        ).quantize(Decimal("0.01"))

        # Act
        service.transfer(
            wallet_id_from=sender.id,
            wallet_id_to=receiver.id,
            amount=amount,
        )

        # Assert balances
        sender.refresh_from_db()
        receiver.refresh_from_db()
        admin_wallet.refresh_from_db()

        self.assertEqual(
            sender.balance,
            Decimal("2000.00") - amount - commission,
        )
        self.assertEqual(
            receiver.balance,
            Decimal("100.00") + amount,
        )
        self.assertEqual(
            admin_wallet.balance,
            commission,
        )

        # Assert transactions
        tx_transfer_debit = Transaction.objects.get(
            wallet=sender,
            direction=TransactionDirection.DEBIT,
            kind=TransactionKind.TRANSFER,
        )

        tx_fee_debit = Transaction.objects.get(
            wallet=sender,
            direction=TransactionDirection.DEBIT,
            kind=TransactionKind.FEE,
        )

        tx_fee_credit = Transaction.objects.get(
            wallet=admin_wallet,
            direction=TransactionDirection.CREDIT,
            kind=TransactionKind.FEE,
        )

        self.assertEqual(tx_fee_debit.amount, commission)
        self.assertEqual(tx_fee_credit.amount, commission)

        # All operations must be linked
        self.assertEqual(tx_fee_debit.reference_id, tx_transfer_debit.reference_id)
        self.assertEqual(tx_fee_credit.reference_id, tx_transfer_debit.reference_id)


class TransferAPITest(APITestCase):
    def setUp(self):
        self.wallet_from = Wallet.objects.create(balance=Decimal("100.00"))
        self.wallet_to = Wallet.objects.create(balance=Decimal("50.00"))
        print(self.wallet_from.id, self.wallet_to.id)
        self.url = reverse("api-transfer")

    def test_multiple_transfers_atomic(self):
        amount = Decimal("15.00")
        responses = []

        for _ in range(10):
            data = {
                "wallet_from": str(self.wallet_from.id),
                "wallet_to": str(self.wallet_to.id),
                "amount": str(amount),
            }
            response = self.client.post(self.url, data, format="json")
            responses.append(response)

        success_count = sum(1 for r in responses if r.status_code == 200)
        self.assertEqual(success_count, 6)

        self.wallet_from.refresh_from_db()
        self.wallet_to.refresh_from_db()

        self.assertGreaterEqual(self.wallet_from.balance, 0)

        self.assertEqual(
            self.wallet_to.balance, Decimal("50.00") + amount * success_count
        )

        debit_count = Transaction.objects.filter(
            wallet=self.wallet_from, direction=TransactionDirection.DEBIT, kind=TransactionKind.TRANSFER,
        ).count()
        credit_count = Transaction.objects.filter(
            wallet=self.wallet_to, direction=TransactionDirection.CREDIT, kind=TransactionKind.TRANSFER,
        ).count()
        self.assertEqual(debit_count, success_count)
        self.assertEqual(credit_count, success_count)
