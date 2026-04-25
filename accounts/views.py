from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .forms import RegisterForm
from manga import selectors

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

class CustomLogoutView(LogoutView):
    pass
class LibraryView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/library.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        active_tab = self.request.GET.get('tab', 'reading')
        list_types = ['reading', 'plan_to_read', 'completed', 'on_hold', 'dropped']
        if active_tab == 'history':
            ctx['history'] = selectors.get_user_read_history(user, limit=100)
        elif active_tab in list_types:
            ctx['bookmarks'] = selectors.get_user_bookmarks(user, list_type=active_tab)
        else:
            active_tab = 'reading'
            ctx['bookmarks'] = selectors.get_user_bookmarks(user, list_type='reading')
        ctx['counts'] = {
            lt: selectors.get_user_bookmarks(user, list_type=lt).count()
            for lt in list_types
        }
        ctx['history_count'] = selectors.get_user_read_history(user, limit=9999).count()
        ctx['active_tab'] = active_tab
        ctx['bookmark_choices'] = [
            ('reading', 'Reading'),
            ('plan_to_read', 'Plan to Read'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('dropped', 'Dropped'),
        ]
        return ctx
