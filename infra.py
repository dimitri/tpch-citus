#! /usr/bin/env python3

import os
import sys
import time
import boto3

from datetime import date, datetime
from collections import namedtuple

from tpch.infra.setup import Setup
from tpch.infra.instance import Instance
from tpch.infra.rds import RDS
from tpch.infra.aurora import Aurora

import click


@click.group()
def ec2():
    pass


@ec2.command()
@click.option('--json',
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.option('--id', help='Instance ID')
@click.pass_context
def status(ctx, id, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)

    if json:
        instance = Instance(conf, conn, json)
        status = instance.status()
        click.echo(status)

    elif id:
        instance = Instance(conf, conn)
        instance.id = id
        status = instance.status()
        click.echo(status)

    else:
        click.echo('Please provide either --json or --id')


@ec2.command()
def list():
    ec2 = boto3.resource('ec2')
    print("%20s %25s %15s %15s" % ("Instance Id", "KeyName",
                                   "Status", "Public IP"))
    print("%20s %25s %15s %15s" % ("-" * 20, "-" * 25, "-" * 10, "-" * 15))
    for instance in ec2.instances.all():
        print("%20s %25s %15s %15s" % (instance.id,
                                       instance.key_name,
                                       instance.state['Name'],
                                       instance.public_ip_address))
    print()


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def ip(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)
    instance = Instance(conf, conn, json)
    click.echo(instance.public_ip())


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def wait(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)
    instance = Instance(conf, conn, json)
    click.echo(instance.wait_for_public_ip())


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def start(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)
    instance = Instance(conf, conn, json)
    click.echo(instance.start())


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def stop(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)
    instance = Instance(conf, conn, json)
    click.echo(instance.stop())


@ec2.command()
@click.option('--json',
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.option('--id', help='Instance ID')
@click.pass_context
def terminate(ctx, id, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.terminate())
    elif id:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn)
        instance.id = id
        click.echo(instance.terminate())
    else:
        click.echo('options ID or JSON are mandatory, please provide one')


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(),
              help='Filename where to store AWS JSON output for an instance')
@click.pass_context
def run(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('ec2', conf.region)
    instance = Instance(conf, conn, json)
    click.echo(instance.run())


@click.group()
def rds():
    pass


@rds.command()
def list():
    client = boto3.client('rds')
    rdslist = client.describe_db_instances()

    if 'DBInstances' in rdslist:
        print("%30s %20s %20s %10s" % ("Instance Id", "Instance Class",
                                       "Engine", "Status"))
        print("%30s %20s %20s %10s" % ("-" * 30, "-" * 20, "-" * 20, "-" * 10))
        for instance in rdslist['DBInstances']:
            print("%30s %20s %20s %10s" % (instance['DBInstanceIdentifier'],
                                           instance['DBInstanceClass'],
                                           instance['Engine'],
                                           instance['DBInstanceStatus']))
    print()


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(),
              help='Filename where to store AWS JSON output for an instance')
@click.pass_context
def create(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.create())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def describe(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.describe())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def status(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.status())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def dsn(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.dsn())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def wait(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.wait_for_dsn())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def stop(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.stop())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def start(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.start())


@rds.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def delete(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    rds = RDS(conf, conn, json)
    click.echo(rds.delete())


@click.group()
def aurora():
    pass


@aurora.command()
def list():
    client = boto3.client('rds')
    clist = client.describe_db_clusters()

    if 'DBClusters' in clist:
        print("%30s %12s %20s" % ("Cluster Id", "Status", "Engine"))
        print("%30s %12s %20s" % ("-" * 30, "-" * 12, "-" * 20))
        for cluster in clist['DBClusters']:
            print("%30s %12s %20s" % (cluster['DBClusterIdentifier'],
                                      cluster['Status'],
                                      cluster['Engine']))
    print()


@aurora.command()
@click.option('--json',
              required=True,
              type=click.Path(),
              help='Filename where to store AWS JSON output '
              'for an Aurora instance.')
@click.pass_context
def create(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    aurora = Aurora(conf, conn, json)
    click.echo(aurora.create())


@aurora.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for a DB Cluster.')
@click.pass_context
def dsn(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    aurora = Aurora(conf, conn, json)
    click.echo(aurora.dsn())


@aurora.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def delete(ctx, json):
    conf = ctx.obj['CONFIG']
    conn = boto3.client('rds', conf.region)
    aurora = Aurora(conf, conn, json)
    click.echo(aurora.delete())


@click.group()
def pgsql():
    pass


@pgsql.command()
@click.pass_context
def dsn(ctx):
    conf = ctx.obj['CONFIG']
    click.echo(conf.pgsql.dsn)


@click.group()
def citus():
    pass


@citus.command()
@click.pass_context
def dsn(ctx):
    conf = ctx.obj['CONFIG']
    click.echo(conf.citus.dsn)


@click.group()
@click.option('--config',
              default='infra.ini',
              type=click.Path(exists=True),
              help='configuration file [.ini]')
@click.pass_context
def cli(ctx, config):
    ctx.obj['CONFIG'] = Setup(config)


@cli.command()
@click.argument('dsn-or-aws-file')
@click.pass_context
def dsn(ctx, dsn_or_aws_file):
    if dsn_or_aws_file[-5:] == ".json":
        if os.path.exists(dsn_or_aws_file):
            # That's an aws.out/ file, for an RDS instance
            conf = ctx.obj['CONFIG']
            conn = boto3.client('rds', conf.region)
            rds = RDS(conf, conn, dsn_or_aws_file)
            click.echo(rds.wait_for_dsn())
        else:
            raise click.ClickException('%s: file not found' % dsn_or_aws_file)
    else:
        # Citus and PostgreSQL cases:
        # arg is expected to be a DSN already
        click.echo(dsn_or_aws_file)


cli.add_command(ec2)
cli.add_command(rds)
cli.add_command(aurora)
cli.add_command(pgsql)
cli.add_command(citus)
cli.add_command(dsn)


if __name__ == '__main__':
    cli(obj={})
