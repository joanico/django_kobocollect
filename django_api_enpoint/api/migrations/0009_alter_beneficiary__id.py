# Generated by Django 3.2.8 on 2022-02-05 12:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_beneficiary__id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='beneficiary',
            name='_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]