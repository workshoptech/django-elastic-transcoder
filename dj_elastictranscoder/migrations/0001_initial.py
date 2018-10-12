# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EncodeJob',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('state', models.PositiveIntegerField(default=0, db_index=True, choices=[(0, 'Submitted'), (1, 'Progressing'), (2, 'Error'), (3, 'Warning'), (4, 'Complete')])),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=models.deletion.CASCADE)),
            ],
        ),
    ]
