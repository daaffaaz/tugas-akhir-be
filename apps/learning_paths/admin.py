from django.contrib import admin

from .models import LearningPath, LearningPathCourse


class LearningPathCourseInline(admin.TabularInline):
    model = LearningPathCourse
    extra = 0
    raw_id_fields = ('course',)


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_saved', 'created_at')
    list_filter = ('is_saved',)
    search_fields = ('title', 'user__email')
    raw_id_fields = ('user',)
    inlines = [LearningPathCourseInline]


@admin.register(LearningPathCourse)
class LearningPathCourseAdmin(admin.ModelAdmin):
    list_display = ('learning_path', 'course', 'position', 'is_completed')
    raw_id_fields = ('learning_path', 'course')
