from django.contrib import admin

from .models import Badge, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'level', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('category', 'level', 'is_active')
    search_fields = ('code', 'name', 'description')
    ordering = ('sort_order', 'category', 'level')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_via_course', 'earned_via_learning_path', 'earned_at')
    list_filter = ('badge__category', 'badge__level', 'earned_at')
    search_fields = ('user__email', 'badge__code', 'badge__name')
    raw_id_fields = ('user', 'badge', 'earned_via_course', 'earned_via_learning_path')
    readonly_fields = ('earned_at',)
    ordering = ('-earned_at',)
