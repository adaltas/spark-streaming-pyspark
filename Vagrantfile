# -*- mode: ruby -*-
# vi: set ft=ruby :

box = "centos/7"

$ambari_server=<<SCRIPT
wget -q http://public-repo-1.hortonworks.com/ambari/centos7/2.x/updates/2.7.3.0/ambari.repo -O /etc/yum.repos.d/ambari.repo
yum install -q -y ambari-server
ambari-server setup -s
ambari-server start -s
yum -q -y install http://ftp.iij.ad.jp/pub/db/mysql/Downloads/Connector-J/mysql-connector-java-8.0.15-1.el7.noarch.rpm
ambari-server setup -s --jdbc-db=mysql --jdbc-driver=/usr/share/java/mysql-connector-java-8.0.15.jar
export JAVA_HOME=/usr/jdk64/jdk1.8.0_112
export PATH=$JAVA_HOME/bin:$PATH
SCRIPT

$prep_hivedb=<<SCRIPT
wget http://repo.mysql.com/mysql57-community-release-el7-9.noarch.rpm -O mysql57-community-release-el7-9.noarch.rpm
rpm -Uvh mysql57-community-release-el7-9.noarch.rpm
yum-config-manager --enable mysql57-community-release-el7-9.noarch.rpm 
yum install -q -y mysql mysql-community-server
systemctl start mysqld.service
TEMPPASS=$(grep 'temporary password is generated' /var/log/mysqld.log | sed 's/.*:\s//')
mysql --connect-expired-password -uroot -p$TEMPPASS <<- EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY 'MyNewPass4!';
CREATE DATABASE hive DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;
USE hive
CREATE USER hive IDENTIFIED BY 'NewHivePass4!';
GRANT ALL PRIVILEGES ON hive.* TO 'hive' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EOF
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.ssh.insert_key = false
  config.vm.box_check_update = false
  config.vm.provider :virtualbox do |vb|
    config.vbguest.no_remote = true
    config.vbguest.auto_update = false
  end
  
  config.vm.define :master01 do |node|
    node.vm.box = box
    node.vm.hostname = "master01.cluster"
    node.vm.network :private_network, ip: "10.10.10.11"
    node.vm.network :forwarded_port, guest: 22, host: 24011, auto_correct: true
    config.vm.synced_folder ".", "/vagrant", type: "rsync", rsync__exclude: ".git/"
    # vagrant rsync-auto

    # SSH setup
    # make sure to generate ~/.ssh/id_rsa_ex.pub with ssh-keygen
    config.vm.provision "file", source: "~/.ssh/id_rsa_ex.pub", destination: "/tmp/authorized_keys"
    config.vm.provision "shell" do |s|
      s.inline = <<-SHELL
        mkdir -p -m 700 /root/.ssh
        cat /tmp/authorized_keys >> /root/.ssh/authorized_keys
        rm /tmp/authorized_keys
      SHELL
    end
    
    node.vm.provision :shell, path: "bootstrap.sh", 
      env: {"NODE" => "master01", "HNAME" => "master01.cluster"}
    node.vm.provision :shell, inline: $ambari_server
    node.vm.provision :shell, inline: $prep_hivedb
    node.vm.provider "virtualbox" do |d|
      d.memory = 5120
      d.cpus = 1
    end
  end

  config.vm.define :master02 do |node|
    node.vm.box = box
    node.vm.hostname = "master02.cluster"
    node.vm.network :private_network, ip: "10.10.10.12"
    node.vm.network :forwarded_port, guest: 22, host: 24012, auto_correct: true
    config.vm.synced_folder ".", "/vagrant", type: "rsync", rsync__exclude: ".git/"
    # vagrant rsync-auto

    # SSH setup
    # make sure to generate ~/.ssh/id_rsa_ex.pub with ssh-keygen
    config.vm.provision "file", source: "~/.ssh/id_rsa_ex.pub", destination: "/tmp/authorized_keys"
    config.vm.provision "shell" do |s|
      s.inline = <<-SHELL
        mkdir -p -m 700 /root/.ssh
        cat /tmp/authorized_keys >> /root/.ssh/authorized_keys
        rm /tmp/authorized_keys
      SHELL
    end
    
    node.vm.provision :shell, path: "bootstrap.sh", 
      env: {"NODE" => "master02", "HNAME" => "master02.cluster"}
    node.vm.provider "virtualbox" do |d|
      d.memory = 6144
      d.cpus = 1
    end
  end
    
  # *** WORKERS ***
  worker_memory = 7168

  config.vm.define :worker01 do |node|
    node.vm.box = box
    node.vm.hostname = "worker01.cluster"
    node.vm.network :private_network, ip: "10.10.10.16"
    node.vm.network :forwarded_port, guest: 22, host: 24015, auto_correct: true
    
    # SSH setup
    # make sure to generate ~/.ssh/id_rsa_ex.pub with ssh-keygen
    config.vm.provision "file", source: "~/.ssh/id_rsa_ex.pub", destination: "/tmp/authorized_keys"
    config.vm.provision "shell" do |s|
      s.inline = <<-SHELL
        mkdir -p -m 700 /root/.ssh
        cat /tmp/authorized_keys >> /root/.ssh/authorized_keys
        rm /tmp/authorized_keys
      SHELL
    end
    
    node.vm.provision :shell, path: "bootstrap.sh", 
      env: {"NODE" => "worker01", "HNAME" => "worker01.cluster"}
    
    node.vm.provider "virtualbox" do |d|
      d.memory = worker_memory
      d.cpus = 3
      d.customize ["modifyvm", :id, "--ioapic", "on"]
    end
  end
  
  config.vm.define :worker02 do |node|
    node.vm.box = box
    node.vm.hostname = "worker02.cluster"
    node.vm.network :private_network, ip: "10.10.10.17"
    node.vm.network :forwarded_port, guest: 22, host: 24016, auto_correct: true
    
    # SSH setup
    # make sure to generate ~/.ssh/id_rsa_ex.pub with ssh-keygen
    config.vm.provision "file", source: "~/.ssh/id_rsa_ex.pub", destination: "/tmp/authorized_keys"
    config.vm.provision "shell" do |s|
      s.inline = <<-SHELL
        mkdir -p -m 700 /root/.ssh
        cat /tmp/authorized_keys >> /root/.ssh/authorized_keys
        rm /tmp/authorized_keys
      SHELL
    end
    
    node.vm.provision :shell, path: "bootstrap.sh", 
      env: {"NODE" => "worker02", "HNAME" => "worker02.cluster"}
    
    node.vm.provider "virtualbox" do |d|
      d.memory = worker_memory
      d.cpus = 2
      d.customize ["modifyvm", :id, "--ioapic", "on"]
    end
  end
  
end
