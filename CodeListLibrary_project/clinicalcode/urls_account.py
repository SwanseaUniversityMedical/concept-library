"""URLs & Views _assoc._ with user accounts and their management."""

from django.urls import re_path as url
from django.contrib.auth import views as auth_views

from clinicalcode.views.Account import AccountResetConfirmView, AccountManagementResultView

# Account interface
urlpatterns = [
    ## Sign in/out
    url('login/', auth_views.LoginView.as_view(), name='login'),
    url('logout/', auth_views.LogoutView.as_view(), name='logout'),

    ## Reset password request
    url(
        route=r'^password_reset/$',
        view=auth_views.PasswordResetView.as_view(template_name='registration/request_reset.html'),
        name='password_reset',
    ),
    url(
        route=r'^password_reset/done/$',
        view=AccountManagementResultView.as_view(
          template_title='Password Reset Request',
          template_target='registration/messages/reset_requested.html',
        ),
        name='password_reset_done'
    ),

    ## Reset password impl
    url(
        route=r'^reset/(?P<uidb64>[_\-A-Za-z0-9+\/=]+)/(?P<token>[_\-A-Za-z0-9+\/=]+)/$',
        view=AccountResetConfirmView.as_view(template_name='registration/reset_form.html'),
        name='password_reset_confirm',
    ),
    url(
        route=r'^reset/done/$',
        view=AccountManagementResultView.as_view(
          requires_auth=True,
          template_title='Password Reset Success',
          template_target='registration/messages/reset_done.html',
          template_prompt_signin=False,
          template_incl_redirect=False,
        ),
        name='password_reset_complete'
    ),

    ## Change password
    url(
        route=r'^password_change/$',
        view=auth_views.PasswordChangeView.as_view(template_name='registration/change_form.html'),
        name='password_change'
    ),
    url(
        route=r'^password_change/done/$',
        view=AccountManagementResultView.as_view(
          requires_auth=True,
          template_title='Password Change Success',
          template_target='registration/messages/change_done.html',
          template_prompt_signin=False,
          template_incl_redirect=False,
        ),
        name='password_change_done'
    ),
]
