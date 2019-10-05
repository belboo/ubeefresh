from enum import Enum


class FreshArticleType(Enum):
    PERMANENT = 1
    WORKAROUND = 2


class FreshStatus(Enum):
    DRAFT = 1
    PUBLISHED = 2


class FreshVisibility(Enum):
    ALL_USERS = 1
    LOGGED_IN = 2
    AGENTS = 3
    SELECTED_COMPANIES = 4


class UbeeFreshAPIError(Enum):
    NOT_FOUND = 1
    EXISTS = 2
    METHOD_NOT_ALLOWED = 5
    OTHER = 10
