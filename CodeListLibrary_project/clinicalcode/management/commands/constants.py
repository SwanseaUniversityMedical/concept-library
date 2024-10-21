import enum

class IterableMeta(enum.EnumMeta):
    """
        Metaclass that defines additional methods
        of operation and interaction with enums

    """
    def from_name(cls, name):
        if name in cls:
            return getattr(cls, name)
    
    def __contains__(cls, lhs):
        try:
            cls(lhs)
        except ValueError:
            return lhs in cls.__members__.keys()
        else:
            return True

class GraphType(int, enum.Enum, metaclass=IterableMeta):
    """
        Parsed from input file to determine how to handle the data
        
        e.g. { type: 'CODE_CATEGORIES' } within `./data/graphs/icd10_categories.json`

    """
    CODE_CATEGORIES = 0
    ANATOMICAL_CATEGORIES = 1
    SPECIALITY_CATEGORIES = 2

class LogType(int, enum.Enum, metaclass=IterableMeta):
    """
        Enum that reflects the output style, as described by the BaseCommand log style

        See ref @ https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/#django.core.management.BaseCommand.style

    """
    SUCCESS = 1
    NOTICE = 2
    WARNING = 3
    ERROR = 4
