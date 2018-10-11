Django Elastic Transcoder
=========================

`django-elastic-transcoder` is an [Django]{.title-ref} app, let you
integrate AWS Elastic Transcoder in Django easily.

What is provided in this package?

-   `Transcoder` class
-   URL endpoint for receive SNS notification
-   Signals for PROGRESS, ERROR, COMPLETE
-   `EncodeJob` model

Workflow
--------

![image]

Install
-------

First, install `dj_elastictranscode` with `pip`

``` {.sourceCode .sh}
$ pip install django-elastic-transcoder
```

Then, add `dj_elastictranscoder` to `INSTALLED_APPS`

``` {.sourceCode .python}
INSTALLED_APPS = (
    ...
    'dj_elastictranscoder',
    ...
)
```

Bind `urls.py`

``` {.sourceCode .python}
urlpatterns = patterns('',
    ...
    url(r'^elastictranscoder/', include('dj_elastictranscoder.urls')),
    ...
)
```

Migrate

``` {.sourceCode .sh}
$ ./manage.py migrate
```

Setting up AWS Elastic Transcoder
---------------------------------

1.  Create a new `Pipeline` in AWS Elastic Transcoder.
2.  Hookup every available Transcoder Notification to an SNS Topic.
3.  Subscribe to the SNS Topics using the protocol HTTPS/HTTP.
4.  Ready to encode and receieve notifications on progress!

Required Django settings
------------------------

Please settings up variables below to make this app works.

```python
# Optional: Provide the variable name where we can find the AWS Access Key
# Defaults to "AWS_ACCESS_KEY"
SNS_ACCESS_KEY_NAME = <name of the access key settings variable>
# Optional: Provide the variable name where we can find the AWS Secret Access Key
# Defaults to "AWS_SECRET_ACCESS_KEY"
SNS_SECRET_KEY_NAME = <name of the secret key settings variable>

AWS_ACCESS_KEY_ID = <your aws access key id>
AWS_SECRET_ACCESS_KEY = <your aws secret access key>
# Defaults to "eu-west-1"
AWS_REGION = <aws region>
```

Usage
-----

For instance, encode an mp3

```python
from dj_elastictranscoder.transcoder import Transcoder

input = {
    'Key': 'input/SampleVideo_1280x720_5mb.mp4', 
    'FrameRate': 'auto',
    'Resolution': 'auto',
    'AspectRatio': 'auto',
    'Interlaced': 'false',
    'Container': 'auto',
}

input = {
    'Key': 'path/to/input.mp3', 
}

outputs = [{
    'Key': 'path/to/output.mp3',
    'PresetId': '1351620000001-300040' # for example: 128k mp3 audio preset
}]

outputs =[
    {
        'Key': 'HLS_2M',
        'ThumbnailPattern': 'thumb-{count}',
        'PresetId': '1471250797416-4bhqrz',
        'SegmentDuration': '10',
    },
    {
        'Key': 'HLS_1M',
        'ThumbnailPattern': '',
        'PresetId': '1351620000001-200030',
        'SegmentDuration': '10',
    },
    {
        'Key': 'HLS_400K',
        'ThumbnailPattern': '',
        'PresetId': '1351620000001-200050',
        'SegmentDuration': '10',
    },
]

output_key_prefix = 'output/'

playlists=[
    {
        'Name': 'master',
        'Format': 'HLSv3',
        'OutputKeys': [
            'HLS_2M',
            'HLS_1M',
            'HLS_400K',
        ],
    },
]

pipeline_id = '<pipeline_id>'

transcoder = Transcoder(pipeline_id)

transcoder.create_job_and_encode(input, outputs, obj, **{"OutputKeyPrefix": output_key_prefix, "Playlists": playlists})

# Or you can start the encoding process and create an EncodeJob manually
transcoder.encode(input, outputs, **{"OutputKeyPrefix": output_key_prefix, "Playlists": playlists})
transcoder.create_job_for_object(obj)


# Transcoder can also work standalone without Django
# just pass region and required aws key/secret to Transcoder, when initiate

transcoder = Transcoder(pipeline_id, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
```

Setting Up an AWS SNS Topic & Subscribing
-----------------------------------------

AWS Elastic Transcoder can send various SNS notifications to notify your application of transcoding progress, these include `PROGRESS`, `ERROR`, `WARNING` and `COMPLETE`

This package provides an endpoint within your application to receieve these notifications (the notifications are a POST request from SNS). This allows you to receive updates on transcoding progress without having to check yourself. This also provides a mechanism through which you can persist the transcode state of particular objects in your database and receive information about where the transcoded files exist on Amazon S3.

To get started, go to the SNS section in the AWS Console to choose a topic and subscribe with the url below.

`http://<your-domain>/elastictranscoder/endpoint/`

Before notification get started to work, you have to activate an SNS subscription. This is carried out automatically by the endpoint, but you will receive an email with details of the activation.

After subscribing is complete, you can receive SNS notifications from your transcoding pipeline.

Signals
=======

This package provides various signals for you to get notifications, and do more things with this data. You can check the signals usage in
tests.py for more usage example.

-   transcode\_onprogress
-   transcode\_onerror
-   transcode\_oncomplete

  [image]: https://github.com/StreetVoice/django-elastic-transcoder/blob/master/docs/images/workflow.jpg
