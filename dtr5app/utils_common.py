from datetime import datetime

from django.db.models.query import ValuesQuerySet


def json_serializer_helper(obj):
    """JSON serializer helper for objects that are not automatically
    serializable by the default json encoder"""
    if isinstance(obj, ValuesQuerySet):
        return list(obj)
    if isinstance(obj, datetime):
        return str(obj)  # YYYY-MM-DD hh:mm:ss.ffffff

    raise TypeError("Type '{}' not serializable".format(type(obj)))
