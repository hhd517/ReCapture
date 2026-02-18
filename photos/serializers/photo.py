from rest_framework import serializers
from gallery.models import Photo


class ImportGoogleRequestSerializer(serializers.Serializer):
    folderId = serializers.CharField(required=False, allow_null=True)
    dedupe = serializers.BooleanField(default=True)


class ImportJobStatusResponseSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    status = serializers.CharField()
    total = serializers.IntegerField()
    processed = serializers.IntegerField()
    failed = serializers.IntegerField()
    message = serializers.CharField(allow_blank=True, required=False)


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = [
            "id",
            "filename",
            "url",
            "file_size",
            "file_hash",
            "phash",
            "dhash",
            "ahash",
            "duplicate_of",
            "category",
            "source",
            "google_id",
            "memo",
            "width",
            "height",
            "taken_at",
            "processing_status",
            "processing_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "url",
            "file_size",
            "file_hash",
            "phash",
            "dhash",
            "ahash",
            "duplicate_of",
            "source",
            "google_id",
            "width",
            "height",
            "taken_at",
            "processing_status",
            "processing_error",
            "created_at",
            "updated_at",
        ]


class PhotoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ["category", "memo"]