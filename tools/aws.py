#!/usr/bin/env python


import argparse

import boto3


def get_instances_by_node_names(ec2, nodes):
    for node_name in nodes:
        if not node_name:
            continue
        if node_name.startswith('ip-'):
            ip = node_name[3:].replace('-', '.')
        else:
            ip = node_name
        instances = list(ec2.instances.filter(Filters=[{
            'Name': 'private-ip-address',
            'Values': [ip],
        }]))
        if len(instances) != 1:
            print('Invalid node: {}'.format(ip))
            continue
        yield instances[0]


def tag_instances(ec2, nodes):
    for instance in get_instances_by_node_names(ec2, nodes):
        result = instance.create_tags(
            Tags=[{'Key': 'k8s-deployed', 'Value': 'true'}])
        print('tag', instance.id, instance.private_dns_name, result)


def untag_instances(ec2, nodes):
    for instance in get_instances_by_node_names(ec2, nodes):
        result = instance.delete_tags(
            Tags=[{'Key': 'k8s-deployed', 'Value': 'true'}])
        print('untag', instance.id, instance.private_dns_name, result)


def terminate_instances(ec2, nodes):
    for instance in get_instances_by_node_names(ec2, nodes):
        result = instance.terminate()
        print('terminate', instance.id, instance.private_dns_name, result)


def detach_instances_from_autoscaling_group(ec2, client, group_name, nodes):
    if not group_name:
        print('group name required')
        return
    result = client.detach_instances(
        InstanceIds=[i.id for i in get_instances_by_node_names(ec2, nodes)],
        AutoScalingGroupName=group_name,
        ShouldDecrementDesiredCapacity=True
    )
    print(result)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'cmd', choices=['tag', 'untag', 'detach', 'terminate'])
    parser.add_argument(
        '-g', '--group', help='autoscaling group, required by cmd `detach`')
    parser.add_argument(
        'nodes', help='deployed nodes, split with comma or space')
    args = parser.parse_args()

    nodes = set()
    for i in args.nodes.strip().split(','):
        for j in i.split():
            nodes.add(j.strip())

    ec2 = boto3.resource('ec2')
    asg_client = boto3.client('autoscaling')

    if args.cmd == 'tag':
        tag_instances(ec2, nodes)
    elif args.cmd == 'untag':
        untag_instances(ec2, nodes)
    elif args.cmd == 'terminate':
        terminate_instances(ec2, nodes)
    elif args.cmd == 'detach':
        detach_instances_from_autoscaling_group(
            ec2, asg_client, args.group, nodes)


if __name__ == '__main__':
    main()
