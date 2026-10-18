
from decimal import Decimal

from django.db import models


class Unit(models.TextChoices):
    PIECE = 'piece', 'Piece'
    BAG = 'bag', 'Bag'


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='products',
    )
    name = models.CharField(
        max_length=150,
        help_text='e.g. Pampers Large',
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
    )
    mrp = models.DecimalField(
        'MRP per piece',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Printed MRP per piece',
    )
    price = models.DecimalField(
        'Price per piece',
        max_digits=10,
        decimal_places=2,
    )
    pieces_per_bag = models.PositiveIntegerField(
        default=1,
        help_text='Number of pieces per bag or pack',
    )
    bag_piece_rate = models.DecimalField(
        'Bag piece rate',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            'Price per piece when purchased by bag. '
            'If empty, the price per piece is used.'
        ),
    )
    stock = models.PositiveIntegerField(
        default=0,
        help_text='Total stock in pieces',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['brand__name', 'name']
        unique_together = ('brand', 'name')

    @property
    def bag_rate(self):
        piece_rate = (
            self.bag_piece_rate
            if self.bag_piece_rate is not None
            else self.price
        )
        return piece_rate * Decimal(self.pieces_per_bag)

    def __str__(self):
        return self.name


class Scheme(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='schemes',
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.BAG,
    )
    min_quantity = models.PositiveIntegerField(
        help_text='Minimum quantity required',
    )
    free_quantity = models.PositiveIntegerField(
        default=0,
        help_text='Free quantity in the same unit',
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Optional discount percentage',
    )
    description = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['product', 'unit', 'min_quantity']

    def __str__(self):
        return (
            f'{self.product.name}: {self.min_quantity} {self.unit} '
            f'-> {self.free_quantity} free / '
            f'{self.discount_percent}%'
        )
