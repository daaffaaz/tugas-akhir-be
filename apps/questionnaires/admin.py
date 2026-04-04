from django.contrib import admin

from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'section', 'question_text', 'input_type')
    list_filter = ('section',)
    search_fields = ('question_text', 'variable_key')
    ordering = ('order_number',)
