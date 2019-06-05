#!/usr/bin/env bash

# Boostrap each machine with Ambari prerequisites / prepare environment
echo "*** BOOSTRAPING NODE $NODE ***"

yum upgrade -q -y
yum install -q -y epel-release
yum install -q -y htop
yum install -q -y vim
yum install -q -y wget

cat > /etc/hosts <<- EOF
  10.10.10.11 master01.cluster master01
  10.10.10.12 master02.cluster master02
  10.10.10.16 worker01.cluster worker01
  10.10.10.17 worker02.cluster worker02 
EOF
cat >> /etc/sysconfig/network <<- EOF
  NETWORKING=yes
  HOSTNAME=$HNAME
EOF
sysctl -w fs.file-max=100000
yum install -y -q ntp
systemctl enable ntpd
systemctl start ntpd
systemctl disable firewalld
service firewalld stop
echo umask 0022 >> /etc/profile
setenforce 0
sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

# For Ambari 2.7.3 Minimum Java is OracleJDK JDK 1.8.0_77
# Java installation skipped - ambari-server can download it itself and share with 
# all ambari-agents

#install Python 3 from epel repository (concurrently to existing Python 2.7.5)
yum install -y -q python36
yum install -y -q python36-setuptools
easy_install-3.6 -q pip
