from django.contrib import admin

from .models import Course, CourseTag, Platform, Tag


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url')
    search_fields = ('name',)


class CourseTagInline(admin.TabularInline):
    model = CourseTag
    extra = 0
    raw_id_fields = ('tag',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'price', 'currency', 'rating', 'review_count', 'is_active')
    list_filter = ('platform', 'is_active', 'currency')
    search_fields = ('title', 'external_id', 'instructor_name')
    raw_id_fields = ('platform',)
    inlines = [CourseTagInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name',)
