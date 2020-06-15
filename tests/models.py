# Global test models, define test-specific models locally in test_* files
from django.db import models


class Member(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class Project(models.Model):
    name = models.CharField(max_length=100)
    archived = models.BooleanField()
    members = models.ManyToManyField(Member, related_name='projects')
    owner_member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
    sub_projects = models.ManyToManyField('self')
