from rest_framework import serializers


class RAGGenerateRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(
        max_length=500,
        help_text='Learning topic or goal (e.g. "machine learning untuk data science")'
    )
    budget_idr = serializers.IntegerField(
        required=False, allow_null=True,
        help_text='Maximum budget in IDR (optional filter)'
    )
    level = serializers.CharField(
        required=False, allow_null=True, max_length=50,
        help_text='Preferred course level (Beginner/Intermediate/Advanced)'
    )

    def validate_topic(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Topic must be at least 3 characters.")
        return value.strip()