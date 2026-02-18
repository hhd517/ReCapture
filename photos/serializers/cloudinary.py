from rest_framework import serializers


class CloudinarySignRequestSerializer(serializers.Serializer):
    filename = serializers.CharField()
    file_hash = serializers.CharField(min_length=64, max_length=64)


class CloudinaryConfirmRequestSerializer(serializers.Serializer):
    filename = serializers.CharField()
    file_hash = serializers.CharField(min_length=64, max_length=64)

    public_id = serializers.CharField()
    secure_url = serializers.URLField()

    bytes = serializers.IntegerField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    format = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CloudinaryConfirmBatchRequestSerializer(serializers.Serializer):
    items = CloudinaryConfirmRequestSerializer(many=True)