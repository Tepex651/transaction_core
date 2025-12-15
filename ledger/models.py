from django.core.validators import MinValueValidator
from django.db import models

from wallet.models import Wallet


class TransactionDirection(models.TextChoices):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionKind(models.TextChoices):
    TRANSFER = "transfer"
    FEE = "fee"
    REFUND = "refund"


# Create your models here.
class Transaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.RESTRICT, related_name="transactions"
    )

    direction = models.CharField(
        choices=TransactionDirection.choices, max_length=6, editable=False
    )
    kind = models.CharField(
        choices=TransactionKind.choices, max_length=8, editable=False
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        editable=False,
    )

    reference_id = models.UUIDField(editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["reference_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(direction__in=TransactionDirection.values),
                name="transaction_direction_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=TransactionKind.values),
                name="transaction_kind_valid",
            ),
        ]
