# Generated by Django 3.2.8 on 2021-12-07 05:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20211207_0319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='beneficiary',
            name='date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
