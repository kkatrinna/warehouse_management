from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Category, StockMovement


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'sku', 'description', 'price',
                  'quantity', 'min_quantity', 'location', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if Product.objects.filter(sku=sku).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Товар с таким артикулом уже существует')
        return sku


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'reason']
        widgets = {
            'reason': forms.TextInput(attrs={'placeholder': 'Например: Продажа, возврат, инвентаризация...'})
        }

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        quantity = cleaned_data.get('quantity')
        product = cleaned_data.get('product')

        if movement_type == 'out' and product and quantity:
            if product.quantity < quantity:
                raise forms.ValidationError(
                    f'Недостаточно товара на складе. Доступно: {product.quantity}'
                )
        return cleaned_data


class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию или артикулу...'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Все категории",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    in_stock = forms.BooleanField(
        required=False,
        label='Только в наличии',
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    low_stock = forms.BooleanField(
        required=False,
        label='Только с остатком ниже минимума',
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class InvoiceGenerateForm(forms.Form):
    items = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    def clean_items(self):
        items = self.cleaned_data.get('items')
        if not items:
            raise forms.ValidationError('Добавьте хотя бы один товар')
        return items