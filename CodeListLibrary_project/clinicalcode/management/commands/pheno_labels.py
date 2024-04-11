from django.core.management.base import BaseCommand
from django.db import transaction, connection

from .constants import LogType

class Command(BaseCommand):
    help = 'Various tasks associated with phenotype labeling'

    def __get_log_style(self, style):
        """
            Returns the BaseCommand's log style

            See ref @ https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/#django.core.management.BaseCommand.style
        """
        if isinstance(style, str):
            style = style.upper()
            if style in LogType.__members__:
                return getattr(self.style, style)
        elif isinstance(style, LogType):
            if style.name in LogType.__members__:
                return getattr(self.style, style.name)
        return self.style.SUCCESS

    def __log(self, message, style=LogType.SUCCESS):
        """
            Logs the incoming to the terminal if
            the verbose argument is present
        """
        if not self._verbose:
            return
        style = self.__get_log_style(style)
        self.stdout.write(style(message))

    def add_arguments(self, parser):
        """
            Handles arguments given via the CLI

        """
        parser.add_argument('-v', '--verbose', type=bool, help='Print debug information to the terminal')
        pass

    def handle(self, *args, **kwargs):
        """
            Main command handle

        """
        # init parameters
        verbose = kwargs.get('verbose')

        # det. handle
        self._verbose = verbose
