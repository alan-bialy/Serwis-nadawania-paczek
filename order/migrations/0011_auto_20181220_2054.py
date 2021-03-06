# Generated by Django 2.1.2 on 2018-12-20 19:54

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0010_auto_20181220_2046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='surname',
            field=models.CharField(max_length=90, validators=[django.core.validators.RegexValidator("^[a-zA-ZàáâäãåąčćęèéêëėįìíîïłńòóôöõøùúûüųūÿýżźñçčšžÀÁÂÄÃÅĄĆČĖĘÈÉÊËÌÍÎÏĮŁŃÒÓÔÖÕØÙÚÛÜŲŪŸÝŻŹÑßÇŒÆČŠŽ∂ð ,.'-]+$", 'To pole moze skladac sie tylko z liter.')]),
        ),
        migrations.AlterField(
            model_name='address',
            name='zip_code',
            field=models.CharField(max_length=6, validators=[django.core.validators.RegexValidator('\\d{2}-?\\d{3}', 'Podaj poprawny adres pocztowy NN-NNN')]),
        ),
    ]
