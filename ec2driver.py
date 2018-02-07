#! /usr/bin/env python3

import os
import sys
import time
import boto3

from datetime import date, datetime
from collections import namedtuple

from driver.setup import Setup
from driver.instance import Instance
from driver.rds import RDS
from driver.aurora import Aurora

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
    print("%20s %25s %15s %15s" % ("Instance Id", "KeyName", "Status", "Public IP"))
    print("%20s %25s %15s %15s" % ("-" * 20, "-" * 25, "-" * 10, "-" * 15))
    for instance in ec2.instances.all():
        print("%20s %25s %15s %15s" % (instance.id,
                                       instance.key_name,
                                       instance.state['Name'],
                                       instance.public_ip_address))

@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def ip(ctx, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.public_ip())
    else:
        click.echo('option JSON is mandatory')


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def wait(ctx, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.wait_for_public_ip())

    else:
        click.echo('option JSON is mandatory')


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def start(ctx, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.start())
    else:
        click.echo('option JSON is mandatory')


@ec2.command()
@click.option('--json',
              required=True,
              type=click.Path(exists=True),
              help='already stored AWS JSON output for an instance')
@click.pass_context
def stop(ctx, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.stop())
    else:
        click.echo('option JSON is mandatory')


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
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('ec2', conf.region)
        instance = Instance(conf, conn, json)
        click.echo(instance.run())
    else:
        click.echo('option JSON is mandatory')



@click.group()
def rds():
    pass

@rds.command()
def list():
    client = boto3.client('rds')
    rdslist = client.describe_db_instances()

    if 'DBInstances' in rdslist:
        print("%20s %20s %20s %10s" % ("Instance Id", "Instance Class", "Engine", "Status"))
        print("%20s %20s %20s %10s" % ("-" * 20, "-" * 20, "-" * 20, "-" * 10))
        for instance in rdslist['DBInstances']:
            print("%20s %20s %20s %10s" % (instance['DBInstanceIdentifier'],
                                           instance['DBInstanceClass'],
                                           instance['Engine'],
                                           instance['DBInstanceStatus']))

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
        print("%20s %12s %20s" % ("Cluster Id", "Status", "Engine"))
        print("%20s %12s %20s" % ("-" * 20, "-" * 12, "-" * 20))
        for cluster in clist['DBClusters']:
            print("%20s %12s %20s" % (cluster['DBClusterIdentifier'],
                                      cluster['Status'],
                                      cluster['Engine']))

@aurora.command()
@click.option('--json',
              required=True,
              type=click.Path(),
              help='Filename where to store AWS JSON output for an Aurora instance.')
@click.pass_context
def create(ctx, json):
    if json:
        conf = ctx.obj['CONFIG']
        conn = boto3.client('rds', conf.region)
        aurora = Aurora(conf, conn, json)
        click.echo(aurora.create())
    else:
        click.echo('option JSON is mandatory')

@aurora.command()
@click.option('--json',
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
@click.option('--config',
              type=click.Path(exists=True),
              help='configuration file [.ini]')
@click.pass_context
def cli(ctx,config):
    ctx.obj['CONFIG'] = Setup(config)

cli.add_command(ec2)
cli.add_command(rds)
cli.add_command(aurora)

if __name__ == '__main__':
    cli(obj={})
