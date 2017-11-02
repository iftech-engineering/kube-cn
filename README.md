# boot-cn
easy kubernetes deployment / management with ansible in GFW
Now supports kubernetes 1.8.2

## Submodules
* forked version of kubespray (https://github.com/januszry/kubespray.git)

## System requirements:
* Now only AWS is supported
* Tested OS and kernel: CentOS 7 with kernel >= 4.12
* See requirements.txt

## CAUTION for AMI for kubernetes machines
* If you don't want to use proxy, don't set `http_proxy, https_proxy or no_proxy` to empty string. Comment them out or you'll get a wrong configuration file in /etc/systemd/system/docker.service.d;
* DONOT enable docker.service with `systemctl enable docker.service` before add the machine to cluster, or our docker configuration will not take effect.

## Deploy and config
1. Choose an unique environment name (will be referred to as `<env>` later) since this tool supports deployment of multiple environments.
1. Export environment variables: `export kenv=<env> && export KUBECONFIG=~/.kube/env-$kenv/config`
1. Install requirements: `pip install -r requirements.txt`
1. Launch machines
    * etcd machines: `m4.large * 3` tagged with `k8s-group=etcd`
    * master machines: `c4.large * 2` tagged with `k8s-group=kube-master`
    * node machines: anytype, at least one, tagged with `k8s-group=kube-node,k8s-node-role=<role>`
1. Tag above machines with: `ansible-app=ansible-k8s,k8s-env=<env>`
1. (Optional) Tag node machines with: `k8s-node-role=<role>`, which will make the nodes be labeled with `role=<role>`
1. Add apiserver (master instances) behind a loadbalancer
1. Modify vars in `ans/inventory/group_vars/all.yml` (Optional, you can also set them as extra vars in the next 2 steps)
    * `apiserver_loadbalancer_domain_name`: address of the loadbalancer for apiserver
    * `loadbalancer_apiserver.address`: same as above
    * `loadbalancer_apiserver.port`
    * `bootstrap_os`
1. Deploy: `ansible-playbook -i inventory/inv-ec2.py -u <username> -b kubespray/cluster.yml`
1. Scale: `ansible-playbook -i inventory/inv-ec2.py -u <username> -b kubespray/scale.yml`
1. Copy kubeconfig: `ansible-playbook -i inventory/inv-ec2.py -u <username> playbooks/kubeconfig.yml`
1. Check cluster is running: `kubectl cluster-info && kubectl get nodes --show-labels`
1. To manage multiple environments with kubectl, you have several choices since kubeconfig is copied to `~/.kube/env-<env>` (will be referred to as `<home>` later)
    * specify kubeconfig: `kubectl --kubeconfig <home> ...`
    * export one time then call `kubectl` freely in current terminal session: `export KUBECONFIG=<home>/config`
    * make symlink manually: `ln -sf <home>/config ~/.kube/config && ln -sf <home>/ssl ~/.kube/ssl`
1. To remove node:
    1. `kubectl drain <node>`
    1. `kubectl delete node <node>`
    1. on master: `calicoctl delete node <node>`
    1. (Optional) `tools/aws.py detach -g <group> <node>`
    1. (Optional) `tools/aws.py terminate <node>`


## Other works
1. Expand disk if necessary
    * e.g. `xfs_growfs /var/lib/docker`
1. Label nodes tagged with `k8s-node-role` with the role and other labels:
    * `ansible-playbook -i inventory/inv-ec2.py -u <username> playbooks/label.yml`
    * `kubectl get nodes --show-labels` (now nodes have more labels)
1. To mark nodes as deployed:
    * `tools/aws.py tag <list of nodes separated by blank or comma>`
