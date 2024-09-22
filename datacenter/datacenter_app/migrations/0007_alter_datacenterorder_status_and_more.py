# Generated by Django 5.1.1 on 2024-09-22 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datacenter_app', '0006_datacenterorder_total_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datacenterorder',
            name='status',
            field=models.CharField(choices=[('draft', 'Черновик'), ('deleted', 'Удален'), ('formed', 'Сформирован'), ('completed', 'Завершен'), ('rejected', 'Отклонен')], default='draft', max_length=10),
        ),
        migrations.AlterField(
            model_name='datacenterservice',
            name='status',
            field=models.CharField(choices=[('active', 'Активный'), ('deleted', 'Удален')], default='active', max_length=10),
        ),
    ]
