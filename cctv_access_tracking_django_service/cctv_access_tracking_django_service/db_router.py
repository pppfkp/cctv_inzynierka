class AccessTrackingRouter:
    """
    A router to control database operations for models in the access_tracking_api app.
    """

    def db_for_read(self, model, **hints):
        """
        Attempts to read access_tracking_api models go to 'timescale'.
        """
        if model._meta.app_label == 'access_tracking_api':
            return 'timescale'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write access_tracking_api models go to 'timescale'.
        """
        if model._meta.app_label == 'access_tracking_api':
            return 'timescale'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation if both models are in the access_tracking_api app.
        """
        if obj1._meta.app_label == 'access_tracking_api' and obj2._meta.app_label == 'access_tracking_api':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure that models in the access_tracking_api app only appear in the 'timescale' database.
        """
        if app_label == 'access_tracking_api':
            return db == 'timescale'
        return db == 'default'
