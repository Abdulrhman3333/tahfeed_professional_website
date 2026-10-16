from django import template
from quran_center.models import UserRole

register = template.Library()


@register.filter
def has_role(user, role_code):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, role__code=role_code).exists()


@register.filter
def dict_get(value, key):
    if isinstance(value, dict):
        return value.get(key)
    return None
