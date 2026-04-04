from django.contrib import admin

from .models import Question, UserQuestionnaireAnswer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'section', 'question_text', 'input_type')
    list_filter = ('section',)
    search_fields = ('question_text', 'variable_key')
    ordering = ('order_number',)


@admin.register(UserQuestionnaireAnswer)
class UserQuestionnaireAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question', 'answer_option', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('user__email', 'question__question_text')
    raw_id_fields = ('user', 'question')
