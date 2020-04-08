import pytest

from django.db import models


class MyModel(models.Model):
    name = models.CharField(max_length=255)


@pytest.mark.django_db
def test_django_models_setup():
    instance = MyModel(name='qwerty')
    instance.save()
