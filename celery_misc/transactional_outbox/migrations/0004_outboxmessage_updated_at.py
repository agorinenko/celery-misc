from django.db import migrations, models


def fill_updated_at(apps, schema_editor):
    """ Заполняет updated_at значением created_at для существующих записей """
    OutboxMessage = apps.get_model('transactional_outbox', 'OutboxMessage')
    OutboxMessage.objects.using(schema_editor.connection.alias).update(
        updated_at=models.F('created_at')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('transactional_outbox', '0003_alter_outboxmessage_idempotency_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='outboxmessage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='Дата изменения'),
        ),
        migrations.RunPython(fill_updated_at, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='outboxmessage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата изменения'),
        ),
    ]
