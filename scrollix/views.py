from django.shortcuts import render


def _render_error_page(
    request,
    *,
    status_code: int,
    title: str,
    message: str,
    can_retry: bool = False,
):
    context = {
        'error_code': status_code,
        'error_title': title,
        'error_message': message,
        'can_retry': can_retry,
    }
    return render(request, 'errors/error.html', context=context, status=status_code)


def error_400(request, exception):
    return _render_error_page(
        request,
        status_code=400,
        title='Bad Request',
        message='The request could not be processed. Please check your input and try again.',
    )


def error_403(request, exception):
    return _render_error_page(
        request,
        status_code=403,
        title='Access Denied',
        message='You do not have permission to access this page.',
    )


def error_404(request, exception):
    return _render_error_page(
        request,
        status_code=404,
        title='Page Not Found',
        message='The page you are looking for might have been moved, deleted, or the URL is incorrect.',
    )


def error_500(request):
    return _render_error_page(
        request,
        status_code=500,
        title='Internal Server Error',
        message='Something went wrong on our end. Please try again later.',
        can_retry=True,
    )


def service_unavailable(request):
    return _render_error_page(
        request,
        status_code=503,
        title='Service Unavailable',
        message='The service is temporarily unavailable due to maintenance. Please try again shortly.',
    )