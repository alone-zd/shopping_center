# Generated by Django 3.1.5 on 2021-02-20 01:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_activate',
            field=models.BooleanField(default=False, verbose_name='邮箱验证状态'),
        ),
    ]
