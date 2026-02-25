import os
from datetime import datetime
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import mm


def generate_invoice_pdf(invoice, items_data):

    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(pdf_dir, exist_ok=True)

    filename = f"invoice_{invoice.number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    elements.append(Paragraph(f"Накладная №{invoice.number}", title_style))
    elements.append(Spacer(1, 5 * mm))

    date_text = f"Дата создания: {invoice.created_at.strftime('%d.%m.%Y %H:%M')}"
    elements.append(Paragraph(date_text, normal_style))
    creator_text = f"Создал: {invoice.created_by.get_full_name() or invoice.created_by.username}"
    elements.append(Paragraph(creator_text, normal_style))
    elements.append(Spacer(1, 10 * mm))

    table_data = [
        ['№', 'Артикул', 'Наименование', 'Кол-во', 'Цена', 'Сумма']
    ]

    total_sum = 0
    for idx, item in enumerate(items_data, 1):
        total = item['price'] * item['quantity']
        total_sum += total
        table_data.append([
            str(idx),
            item['sku'],
            item['name'],
            str(item['quantity']),
            f"{item['price']:.2f}",
            f"{total:.2f}"
        ])

    table_data.append(['', '', '', '', 'ИТОГО:', f"{total_sum:.2f}"])

    table = Table(table_data, colWidths=[20, 60, 180, 40, 60, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (5, -2), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('SPAN', (0, -1), (4, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    elements.append(Paragraph("Отпустил: ____________________", normal_style))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph("Получил: ____________________", normal_style))

    doc.build(elements)

    relative_path = os.path.join('invoices', filename)
    invoice.pdf_file = relative_path
    invoice.save()

    return filepath


def generate_invoice_number():
    from .models import Invoice

    date_str = datetime.now().strftime('%Y%m%d')
    last_invoice = Invoice.objects.filter(
        number__startswith=f"INV-{date_str}"
    ).order_by('-number').first()

    if last_invoice:
        last_num = int(last_invoice.number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f"INV-{date_str}-{new_num:04d}"