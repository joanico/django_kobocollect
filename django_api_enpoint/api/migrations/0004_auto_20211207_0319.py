# Generated by Django 3.2.8 on 2021-12-07 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_meal'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Meal',
        ),
        migrations.AlterField(
            model_name='beneficiary',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
