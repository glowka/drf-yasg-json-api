from django.utils.inspect import get_func_args
from rest_framework import routers


def _basename_or_base_name(basename):
    # freaking DRF... TODO: remove when dropping support for DRF 3.8
    if 'basename' in get_func_args(routers.BaseRouter.register):
        return {'basename': basename}
    else:
        return {'base_name': basename}
