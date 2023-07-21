from django.conf import settings
from django.contrib.auth import logout
from django.utils.timezone import now as timezone_now
from datetime import datetime, timedelta

class SessionExpiryMiddleware:
    '''
        Middleware to det. whether a user session needs to expire
    '''
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__()

    def __get_session_options(self, request):
        if request.user.is_anonymous:
            return

        options = getattr(settings, 'SESSION_EXPIRY', None)
        if options is None:
            return

        return options

    def __session_is_expired(self, request, options):
        current_time = timezone_now()
        session_limit = options.get('SESSION_LIMIT')
        if not isinstance(session_limit, timedelta):
            return False

        last_login = request.user.last_login
        session_time = (last_login - current_time + session_limit).total_seconds()
        return session_time < 0

    def __session_reached_idle_limit(self, request, options):
        current_time = timezone_now()
        idle_limit = options.get('IDLE_LIMIT')
        if not isinstance(idle_limit, timedelta):
            return False

        last_request = current_time
        if 'last_session_request' in request.session:
            last_request = datetime.fromisoformat(request.session.get('last_session_request'))

        idle_time = (last_request - current_time + idle_limit).total_seconds()
        request.session['last_session_request'] = current_time.isoformat()
        return idle_time < 0

    def __try_expire_session(self, request, options):
        '''
            [!] Options are defined within settings.py
            Tries to expire a session if either:
                - The session length has expired after X duration
                - The user has idled between requests for X duration
        '''
        requires_logout = self.__session_is_expired(request, options) | self.__session_reached_idle_limit(request, options)

        if requires_logout:
            if 'last_session_request' in request.session:
                del request.session['last_session_request']

            logout(request)

    def __call__(self, request):
        options = self.__get_session_options(request)
        if options is not None:
            self.__try_expire_session(request, options)

        return self.get_response(request)
