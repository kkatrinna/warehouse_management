from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо войти в систему')
            return redirect('warehouse:login')

        if not request.user.is_staff:
            messages.error(request, 'Недостаточно прав для выполнения этого действия')
            return redirect('warehouse:product_list')

        return view_func(request, *args, **kwargs)

    return wrapper