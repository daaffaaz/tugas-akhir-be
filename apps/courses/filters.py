import django_filters
from django.db.models import Q

from .models import Course


class CourseFilter(django_filters.FilterSet):
    platform = django_filters.UUIDFilter(field_name='platform_id')
    platform_name = django_filters.CharFilter(field_name='platform__name', lookup_expr='iexact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    level = django_filters.CharFilter(method='filter_level_multi')
    difficulty_level = django_filters.CharFilter(method='filter_level_multi')
    min_duration = django_filters.NumberFilter(field_name='video_hours', lookup_expr='gte')
    max_duration = django_filters.NumberFilter(field_name='video_hours', lookup_expr='lte')

    class Meta:
        model = Course
        fields = []

    def filter_level_multi(self, queryset, name, value):
        # Support checkbox behavior using comma-separated levels:
        # ?level=beginner,intermediate
        levels = [v.strip() for v in str(value).split(',') if v.strip()]
        if not levels:
            return queryset

        q = Q()
        for level in levels:
            q |= Q(level__iexact=level)
        return queryset.filter(q)
