from django.urls import path

from dj_elastictranscoder.views import endpoint


urlpatterns = [path("endpoint/", endpoint)]
