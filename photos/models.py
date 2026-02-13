# photos/models.py
from django.db import models
from django.contrib.auth.models import User


class GoogleCredential(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_credential")

    google_email = models.EmailField()
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_uri = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.JSONField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "google_credentials"

    def __str__(self):
        return f"{self.user.username} - {self.google_email}"


class ImportJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="import_jobs")

    job_id = models.CharField(max_length=100, unique=True)

    STATUS_CHOICES = [
        ("PICKING", "Picking"),
        ("QUEUED", "Queued"),
        ("RUNNING", "Running"),
        ("DONE", "Done"),
        ("FAILED", "Failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="QUEUED")
    source = models.CharField(max_length=20, default="GOOGLE")
    folder_id = models.CharField(max_length=255, null=True, blank=True)

    picker_session_id = models.CharField(max_length=255, null=True, blank=True)

    total_count = models.IntegerField(default=0)
    done_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    error_message = models.TextField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["picker_session_id"]),
        ]

    def __str__(self):
        return f"Job {self.job_id} - {self.status}"
