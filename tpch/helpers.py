from . import utils


class TpchComponent():
    def __init__(self, conf, dsn, logger, track):
        self.dsn = dsn
        self.conf = conf
        self.logger = logger
        self.track = track

    def log(self, message, *args):
        if args:
            self.logger.info('%%s: %s' % message, self.system, *args)
        else:
            self.logger.info('%s: %s', self.system, message)


class Schema(TpchComponent):
    def __init__(self, conf, dsn, schema, logger, track):
        super().__init__(conf, dsn, logger, track)
        self.schema = schema

    def install_schema(self, name, filename, tracking=True, silent=False):
        "Install the FILENAME in target database using pgsql"
        if not silent:
            self.log("Installing schema: %s", name)

        start, secs = utils.run_schema_file(self.dsn,
                                            filename,
                                            self.system,
                                            self.logger)
        if tracking:
            self.track.register_job(name, start=start, secs=secs)

        return start, secs
