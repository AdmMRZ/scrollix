from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.shortcuts import render
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
    partial_template = 'accounts/_library_content.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(request, self.partial_template, context)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        active_tab = self.request.GET.get('tab', 'reading')
        
        ctx.update(self._get_tab_data(user, active_tab))
        ctx.update(self._get_counters(user))
        
        ctx['active_tab'] = ctx.get('active_tab', active_tab)
        ctx['bookmark_choices'] = self._get_bookmark_choices()
        
        return ctx

    def _get_tab_data(self, user, tab_name: str) -> dict:
        list_types = ['reading', 'plan_to_read', 'completed', 'on_hold', 'dropped']
        
        if tab_name == 'history':
            return {'history': selectors.get_user_read_history(user, limit=20)}
            
        if tab_name not in list_types:
            tab_name = 'reading'
            
        return {
            'bookmarks': selectors.get_user_bookmarks(user, list_type=tab_name),
            'active_tab': tab_name 
        }

    def _get_counters(self, user) -> dict:
        list_types = ['reading', 'plan_to_read', 'completed', 'on_hold', 'dropped']
        return {
            'counts': {
                lt: selectors.get_user_bookmarks(user, list_type=lt).count()
                for lt in list_types
            },
            'history_count': selectors.get_user_read_history(user, limit=20).count()
        }

    def _get_bookmark_choices(self) -> list:
        return [
            ('reading', 'Reading'),
            ('plan_to_read', 'Plan to Read'),
            ('completed', 'Completed'),
            ('on_hold', 'On Hold'),
            ('dropped', 'Dropped'),
        ]
