from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from mumbai import models

class Command(BaseCommand):
    help = "Instantiates the pg_trgm indexes"

    def handle(self, *args, **options):
        cursor = connection.cursor()
        for name in dir(models):
            model = getattr(models, name)
            if not hasattr(model, "objects") or \
               not isinstance(model.objects, models.TrigramSearchManager):
                continue
            table = model._meta.db_table
            for column in model.objects.trigram_columns:
                sql = """CREATE INDEX %s_%s_trgm_idx ON %s USING gin (%s gin_trgm_ops);""" % (
                        table, column, table, column)
                cursor.execute(sql)
        cursor.execute("COMMIT;")
