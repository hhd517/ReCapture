# photos/serializers/photo.py
from rest_framework import serializers

class ImportGoogleRequestSerializer(serializers.Serializer):
    """구글 Import 요청"""
    folderId = serializers.CharField(required=False, allow_null=True)
    dedupe = serializers.BooleanField(default=True)

class ImportJobStatusResponseSerializer(serializers.Serializer):
    """Import Job 상태 응답"""
    jobId = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.DictField()

class ImportJobStartResponseSerializer(serializers.Serializer):
    """Import Job 시작 응답"""
    jobId = serializers.CharField()
    status = serializers.CharField()