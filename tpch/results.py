import os.path
import psycopg2

from . import initdb
from datetime import date, datetime

SCHEMA = os.path.join(os.path.dirname(__file__), 'tracking.sql')


class Results():

    def __init__(self, conf, system, name):
        self.conf = conf
        self.system = system
        self.name = name
        self.dsn = self.conf.results.dsn


    def register_benchmark(self):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into run(name, system, setup, start, sf)
     values (%s, %s, %s, now(), %s)
  returning id;
"""
        curs.execute(sql, (self.name,
                           self.system,
                           self.conf.to_json(),
                           self.conf.scale.factor))
        self.id, = curs.fetchone()

        conn.commit()
        return self.id

    def register_load(self, load_name, steps, start, secs, vsecs):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into load(run, name, steps, start, duration, vacuum_t)
     values (%s, %s, %s, %s, %s * interval '1 sec', %s * interval '1 sec');
"""
        curs.execute(sql, (self.id, load_name, steps, start, secs, vsecs))
        conn.commit()
        return

    def register_initdb_step(self, load_name, start, secs):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into load(run, name, start, duration)
     values (%s, %s, %s, %s * interval '1 sec');
"""
        curs.execute(sql, (self.id, load_name, start, secs))
        conn.commit()
        return

    def register_stream(self, stream_name, duration):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into stream(run, name, start, duration)
     values (%s, %s, now(), %s * interval '1 sec')
  returning id;
"""
        curs.execute(sql, (self.id, stream_name, duration))
        stream_id, = curs.fetchone()

        conn.commit()
        return stream_id

    def register_query_timings(self, stream_id, query_name, duration):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into query(stream, name, duration)
     values (%s, %s, %s);
"""
        curs.execute(sql, (stream_id, query_name, duration))
        conn.commit()
        return

