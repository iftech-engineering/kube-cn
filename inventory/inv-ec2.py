#!/usr/bin/env python
"""
Script as dynamic inventory for ansible / ansible-playbook.

Example usage: ansible -i inv-ec2.py <group> -u <user> -b -a uptime

To deploy k8s cluster, you need following instances:
    * 2 kube-master
    * 3 etcd
    * at least 1 kube-nodes
These nodes must be tagged with [
    {
        'Name': 'ansible-app',
        'Value': 'ansible-k8s',
    },
    {
        'Name': 'k8s-group',
        'Value': group_name,
    },
]
"""

import argparse
import json
import os

import boto3


if 'kenv' not in os.environ or not os.environ['kenv'].strip():
    raise Exception('Envrionment variable <kenv> must not be empty')

include_deployed = os.environ.get('include_deployed') == 'true'

TAG_FILTERS = [
    {
        'Name': 'tag:ansible-app',
        'Values': ['ansible-k8s'],
    },
    {
        'Name': 'tag:k8s-env',
        'Values': [os.environ['kenv']],
    },
]


def get_group_and_vars_of_instance(instance):
    hostvars_of_t = {
        'instance_type':
        instance.instance_type,
        'availability_zone':
        instance.placement['AvailabilityZone'],
    }
    group = None
    deployed = False
    for t in instance.tags:
        if t['Key'] == 'k8s-group':
            group = t['Value']
        if t['Key'] == 'k8s-node-role':
            hostvars_of_t['node_role'] = t['Value']
        if not include_deployed and \
                t['Key'] == 'k8s-deployed' and \
                t['Value'] == 'true':
            deployed = True
    if group is None:
        return None, None
    if group == 'kube-node' and deployed is True:
        return None, None

    return group, hostvars_of_t


def main():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--list', action='store_true', default=True, help='List instances')
    parser.add_argument(
        '--host', help='Get all the variables about a specific instance')
    args = parser.parse_args()

    ec2 = boto3.resource('ec2')

    if args.host:
        instance = ec2.Instance(args.host)
        group, hostvars_of_t = get_group_and_vars_of_instance(instance)
        if group is None:
            print('{}')
        else:
            print(json.dumps(hostvars_of_t, indent=4))
    elif args.list:
        instances = ec2.instances.filter(Filters=TAG_FILTERS)
        hostvars = {}
        result = {
            'k8s-cluster': {
                'children': [
                    'kube-node',
                    'kube-master',
                ],
            },
            '_meta': {'hostvars': hostvars},
        }
        for i in instances:
            if i.state['Name'] != 'running':
                continue
            group, hostvars_of_t = get_group_and_vars_of_instance(i)
            hostname = i.private_dns_name.split('.')[0]
            if group is None:
                continue
            hostvars[hostname] = hostvars_of_t
            result.setdefault(group, {'hosts': []})
            result[group]['hosts'].append(hostname)
        print(json.dumps(result, indent=4))


if __name__ == '__main__':
    main()
