from rest_framework import serializers

from .models import Question


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = (
            'id',
            'order_number',
            'section',
            'question_text',
            'input_type',
            'options_json',
            'variable_key',
        )
