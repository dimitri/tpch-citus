import os.path
import psycopg2
from datetime import datetime

from . import initdb
from datetime import date, datetime

SCHEMA = os.path.join(os.path.dirname(__file__),
                      '..',
                      '..',
                      'schema',
                      'tracking.sql')


class Tracking():

    def __init__(self, conf, system, name):
        self.conf = conf
        self.system = system
        self.name = name
        self.dsn = self.conf.results.dsn

    def fetch_benchmark_id(self):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = 'select id from run where name = %s'
        curs.execute(sql, (self.name,))
        self.id, = curs.fetchone()
        conn.commit()
        return self.id

    def register_benchmark(self, schedule):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into run(name, system, setup, schedule, start, sf)
     values (%s, %s, %s, %s, now(), %s)
  returning id;
"""
        curs.execute(sql, (self.name,
                           self.system,
                           self.conf.to_json(),
                           schedule,
                           self.conf.scale.factor))
        self.id, = curs.fetchone()

        conn.commit()
        return self.id

    def register_run_time(self, duration):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
update run
   set duration = %s * interval '1 sec'
 where id = %s
"""
        curs.execute(sql, (duration, self.id))
        conn.commit()
        return

    def register_job(self, job_name, start, secs=None, steps=None):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into job(run, name, steps, start, duration)
     values (%s, %s, %s, %s, %s * interval '1 sec')
  returning id;
"""
        curs.execute(sql, (self.id, job_name, steps, start, secs))

        job_id, = curs.fetchone()

        conn.commit()
        return job_id

    def register_job_time(self, job_id, duration):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
update job
   set duration = %s * interval '1 sec'
 where id = %s
"""
        curs.execute(sql, (duration, job_id))
        conn.commit()
        return

    def register_query_timings(self, job_id, query_name, duration):
        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()
        sql = """
insert into query(job, name, duration)
     values (%s, %s, %s);
"""
        curs.execute(sql, (job_id, query_name, duration))
        conn.commit()
        return
