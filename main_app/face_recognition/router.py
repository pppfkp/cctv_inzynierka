class TimescaleRouter:
    timescaleDb = 'timescale'
    defaultDb = 'default'

    def db_for_read(self, model, **hints):
        """
        Direct read operations for 'Recognition' to the Timescale database.
        """
        if model._meta.model_name == 'recognition':
            return self.timescaleDb
        return self.defaultDb

    def db_for_write(self, model, **hints):
        """
        Direct write operations for 'Recognition' to the Timescale database.
        """
        if model._meta.model_name == 'recognition':
            return self.timescaleDb
        return self.defaultDb

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Allow migrations for 'Recognition' only on the Timescale database,
        and other models on the default database.
        """
        if model_name == 'recognition':
            return db == self.timescaleDb
        return db == self.defaultDb
