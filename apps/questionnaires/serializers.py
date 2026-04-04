from rest_framework import serializers

from .models import Question, UserQuestionnaireAnswer


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


class AnswerItemSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    answer_option = serializers.CharField(max_length=16)


class UserQuestionnaireAnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.UUIDField(source='question.id', read_only=True)
    order_number = serializers.IntegerField(source='question.order_number', read_only=True)

    class Meta:
        model = UserQuestionnaireAnswer
        fields = ('id', 'question_id', 'order_number', 'answer_option', 'submitted_at')
