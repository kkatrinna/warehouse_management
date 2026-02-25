from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse, FileResponse
import json
from .models import Product, Category, StockMovement, Invoice, InvoiceItem
from .forms import (
    UserRegisterForm, ProductForm, StockMovementForm,
    ProductSearchForm, InvoiceGenerateForm
)
from .decorators import admin_required
from .utils import generate_invoice_pdf, generate_invoice_number


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('warehouse:product_list')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Вы успешно вошли в систему')
            return redirect('warehouse:product_list')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('warehouse:login')


# Товары
@login_required
def product_list(request):
    form = ProductSearchForm(request.GET)
    products = Product.objects.select_related('category', 'created_by').all()

    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        in_stock = form.cleaned_data.get('in_stock')
        low_stock = form.cleaned_data.get('low_stock')

        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(sku__icontains=query)
            )
        if category:
            products = products.filter(category=category)
        if in_stock:
            products = products.filter(quantity__gt=0)
        if low_stock:
            products = products.filter(quantity__lte=F('min_quantity'))

    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_value = sum(p.get_total_value() for p in products)

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_products': products.count(),
        'total_value': total_value,
    }
    return render(request, 'warehouse/product_list.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    movements = StockMovement.objects.filter(product=product).select_related('created_by')[:10]

    context = {
        'product': product,
        'movements': movements,
    }
    return render(request, 'warehouse/product_detail.html', context)


@admin_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Товар "{product.name}" успешно создан')
            return redirect('warehouse:product_detail', pk=product.pk)
    else:
        form = ProductForm()

    return render(request, 'warehouse/product_form.html', {
        'form': form,
        'title': 'Добавление товара'
    })


@admin_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар успешно обновлен')
            return redirect('warehouse:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(request, 'warehouse/product_form.html', {
        'form': form,
        'title': f'Редактирование товара: {product.name}'
    })


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Товар "{product_name}" удален')
        return redirect('warehouse:product_list')

    return render(request, 'warehouse/product_confirm_delete.html', {
        'product': product
    })


@login_required
def stock_movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            messages.success(
                request,
                f'{"Приход" if movement.movement_type == "in" else "Расход"} товара успешно зарегистрирован'
            )
            return redirect('warehouse:product_detail', pk=movement.product.pk)
    else:
        form = StockMovementForm()
        product_id = request.GET.get('product')
        if product_id:
            form.fields['product'].initial = product_id

    return render(request, 'warehouse/stock_movement_form.html', {
        'form': form,
        'title': 'Движение товара'
    })


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('created_by').all().order_by('-created_at')

    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'warehouse/invoice_list.html', {'page_obj': page_obj})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related('items__product'),
        pk=pk
    )

    return render(request, 'warehouse/invoice_detail.html', {'invoice': invoice})


@login_required
def invoice_generate(request):
    if request.method == 'POST':
        form = InvoiceGenerateForm(request.POST)
        if form.is_valid():
            items_data = json.loads(request.POST.get('items', '[]'))

            if not items_data:
                messages.error(request, 'Не выбрано ни одного товара')
                return redirect('warehouse:invoice_generate')

            for item in items_data:
                product = Product.objects.get(pk=item['id'])
                if product.quantity < item['quantity']:
                    messages.error(
                        request,
                        f'Недостаточно товара "{product.name}" на складе. Доступно: {product.quantity}'
                    )
                    return redirect('warehouse:invoice_generate')

            invoice = Invoice.objects.create(
                number=generate_invoice_number(),
                created_by=request.user
            )

            for item in items_data:
                product = Product.objects.get(pk=item['id'])

                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=item['quantity'],
                    price=float(product.price)
                )

                StockMovement.objects.create(
                    product=product,
                    movement_type='out',
                    quantity=item['quantity'],
                    reason=f'Списание по накладной №{invoice.number}',
                    created_by=request.user
                )

            pdf_items = [
                {
                    'name': Product.objects.get(pk=item['id']).name,
                    'sku': Product.objects.get(pk=item['id']).sku,
                    'quantity': item['quantity'],
                    'price': float(Product.objects.get(pk=item['id']).price)
                }
                for item in items_data
            ]

            generate_invoice_pdf(invoice, pdf_items)

            messages.success(request, f'Накладная №{invoice.number} успешно создана')
            return redirect('warehouse:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceGenerateForm()
        products = Product.objects.filter(quantity__gt=0).select_related('category')

    return render(request, 'warehouse/invoice_generate.html', {
        'form': form,
        'products': products
    })


@login_required
def invoice_download_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.pdf_file:
        return FileResponse(
            invoice.pdf_file.open('rb'),
            as_attachment=True,
            filename=f'invoice_{invoice.number}.pdf'
        )
    else:
        messages.error(request, 'PDF файл не найден')
        return redirect('warehouse:invoice_detail', pk=pk)


@login_required
def api_product_search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(sku__icontains=query),
        quantity__gt=0
    )[:10]

    data = [
        {
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'price': float(p.price),
            'quantity': p.quantity,
            'category': p.category.name if p.category else 'Без категории'
        }
        for p in products
    ]

    return JsonResponse(data, safe=False)

@login_required
def api_product_stock(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'quantity': product.quantity,
            'price': float(product.price)
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)