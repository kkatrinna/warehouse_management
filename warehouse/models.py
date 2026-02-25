from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db.models import F


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('Название', max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Категория',
        related_name='products'
    )
    sku = models.CharField('Артикул', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.IntegerField('Количество', validators=[MinValueValidator(0)])
    min_quantity = models.IntegerField(
        'Минимальное количество',
        default=0,
        help_text='При достижении этого количества товар подсвечивается'
    )
    location = models.CharField('Местоположение', max_length=100, blank=True)
    image = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Добавил',
        related_name='products_created'
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    def get_total_value(self):
        return self.price * self.quantity


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Приход'),
        ('out', 'Расход'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар',
        related_name='movements'
    )
    movement_type = models.CharField('Тип', max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField('Количество', validators=[MinValueValidator(1)])
    reason = models.CharField('Причина', max_length=200)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Движение товара'
        verbose_name_plural = 'Движения товаров'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.movement_type == 'out':
            self.product.quantity -= self.quantity
        else:
            self.product.quantity += self.quantity
        self.product.save()


class Invoice(models.Model):
    number = models.CharField('Номер накладной', max_length=50, unique=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Создал'
    )
    pdf_file = models.FileField('PDF файл', upload_to='invoices/', blank=True, null=True)

    class Meta:
        verbose_name = 'Накладная'
        verbose_name_plural = 'Накладные'
        ordering = ['-created_at']

    def __str__(self):
        return f"Накладная №{self.number} от {self.created_at.strftime('%d.%m.%Y')}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Накладная'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    quantity = models.IntegerField('Количество', validators=[MinValueValidator(1)])
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция накладной'
        verbose_name_plural = 'Позиции накладной'

    def get_total(self):
        return self.price * self.quantity