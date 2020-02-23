import pytest

from django.db import models


class MyModel(models.Model):
    name = models.CharField(max_length=255)


class TestNoop:
    @pytest.mark.django_db
    def test_noop(self):
        instance = MyModel(name='qwerty')
        instance.save()
