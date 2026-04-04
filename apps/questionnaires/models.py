import uuid

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
