from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import feedback_widget.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[
                    ('bug', 'Bug'),
                    ('tips', 'Tip / suggestion'),
                    ('question', 'Question'),
                    ('other', 'Other'),
                ], default='bug', max_length=20)),
                ('message', models.TextField()),
                ('url', models.CharField(blank=True, default='', max_length=1000)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('screen_size', models.CharField(blank=True, default='', max_length=30)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='submitted_feedback', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Feedback',
                'verbose_name_plural': 'Feedback',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FeedbackScreenshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('image', models.FileField(upload_to=feedback_widget.models._screenshot_upload_path)),
                ('url', models.CharField(blank=True, default='',
                    help_text='URL where the screenshot was captured.', max_length=1000)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('feedback', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='screenshots', to='feedback_widget.feedback')),
            ],
            options={
                'ordering': ['sort_order', 'created_at'],
            },
        ),
    ]
