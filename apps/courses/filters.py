import django_filters

from .models import Course


class CourseFilter(django_filters.FilterSet):
    platform = django_filters.UUIDFilter(field_name='platform_id')
    platform_name = django_filters.CharFilter(field_name='platform__name', lookup_expr='iexact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    level = django_filters.CharFilter(field_name='level', lookup_expr='icontains')
    difficulty_level = django_filters.CharFilter(field_name='level', lookup_expr='icontains')
    min_duration = django_filters.NumberFilter(field_name='video_hours', lookup_expr='gte')
    max_duration = django_filters.NumberFilter(field_name='video_hours', lookup_expr='lte')

    class Meta:
        model = Course
        fields = []
