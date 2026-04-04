import uuid

from django.conf import settings
from django.db import models


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.PositiveSmallIntegerField(unique=True, db_index=True)
    section = models.CharField(max_length=255)
    question_text = models.TextField()
    input_type = models.CharField(max_length=64, blank=True)
    options_json = models.JSONField()
    variable_key = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = 'questions'
        ordering = ['order_number']

    def __str__(self):
        return f'{self.order_number}. {self.question_text[:50]}'


class UserQuestionnaireAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='questionnaire_answers',
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='user_answers',
    )
    answer_option = models.CharField(max_length=16)
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_questionnaire_answers'
        constraints = [
            models.UniqueConstraint(fields=['user', 'question'], name='uniq_user_questionnaire_answer'),
        ]
        ordering = ['question__order_number']

    def __str__(self):
        return f'{self.user_id} -> Q{self.question_id}: {self.answer_option}'
