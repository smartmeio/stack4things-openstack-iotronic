===============================
IoTronic
===============================

IoTronic is an Internet of Things resource management service for OpenStack clouds.

IoTronic allows to manage Internet of Things resources as part of an OpenStack data center.

* Free software: Apache license
* Source: http://git.openstack.org/git/openstack/iotronic
* Bugs: http://bugs.launchpad.net/iotronic

.. contents:: Contents:
   :local:

Basic scenario
----------------------
For this installation of the Iotronic Service we are considering a scenario with the following hosts and softwares:

- Controller ( **Ubuntu linux**): Mysql, Keystone, Rabbitmq
- Iotronic ( **Ubuntu linux** ): Iotronic-conductor, iotronic-wamp-agent, crossbar
- Board: iotronic-lightining-rod

Controller host setup
----------------------
According to the `Openstack Documentation <https://docs.openstack.org/>`_ install the following softwares on the controller host:

- SQL database
- Message queue
- Memcached
- Keystone

Creation of the database
-------------------------
On the dbms create the iotronic db and configure the access for the user iotronic::

    MariaDB [(none)]> CREATE DATABASE iotronic;
    MariaDB [(none)]> GRANT ALL PRIVILEGES ON iotronic.* TO iotronic@'localhost' IDENTIFIED BY ‘IOTRONIC_DBPASS’;
    MariaDB [(none)]> GRANT ALL PRIVILEGES ON iotronic.* TO iotronic@'%' IDENTIFIED BY ‘IOTRONIC_DBPASS’;

Add the user and the enpoints on Keystone::

    source adminrc
    openstack service create iot --name Iotronic
    openstack user create --password-prompt iotronic
    
    openstack role add --project service --user iotronic admin
    openstack role add admin_iot_project
    openstack role add manager_iot_project
    openstack role add user_iot

    openstack endpoint create --region RegionOne iot public http://IP_IOTRONIC:8812
    openstack endpoint create --region RegionOne iot internal http://IP_IOTRONIC:8812
    openstack endpoint create --region RegionOne iot admin http://1IP_IOTRONIC:8812


Configuring Iotronic Host 
--------------------------

Crossbar
^^^^^^^^^^^^^^^^^^^^^
Install crossbar on the Iotronic host following the `official guide <http://crossbar.io/docs/Installation-on-Ubuntu-and-Debian/>`_


Iotronic Installation 
^^^^^^^^^^^^^^^^^^^^^
Get the source::

    git clone https://github.com/openstack/iotronic.git

add the user iotronic::
    
    useradd -m -d /var/lib/iotronic iotronic

and Iotronic::

    cd iotronic
    pip3 install -r requirements.txt 
    python3 setup.py install

create a log dir::

    mkdir -p /var/log/iotronic
    chown -R iotronic:iotronic /var/log/iotronic/

edit ``/etc/iotronic/iotronic.conf`` with the correct configuration::
    
    nano /etc/iotronic/iotronic.conf 

There is just one wamp-agent and it must be set as the registration agent::
 
  register_agent = True

populate the database::

    iotronic-dbsync


API Service Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^
Install apache and the other components::

    sudo apt-get install apache2 python-setuptools libapache2-mod-wsgi-py3

create log directory::

    touch /var/log/iotronic/iotronic-api_error.log
    touch /var/log/iotronic/iotronic-api_access.log
    chown -R iotronic:iotronic /var/log/iotronic/

copy the config apache2 file::

    cp etc/apache2/iotronic.conf /etc/apache2/sites-available/iotronic.conf

enable the configuration::

    a2ensite /etc/apache2/sites-available/iotronic.conf

restart apache::
  
  systemctl restart apache2


Starting
^^^^^^^^^^^^^^^^^^^^^
Start the service::

  systemctl enable iotronic-wamp-agent
  systemctl start iotronic-wamp-agent

  systemctl enable iotronic-conductor
  systemctl start iotronic-conductor


Board Side 
----------------------

Follow the `iotronic-lightning-rod README <https://github.com/openstack/iotronic-lightning-rod/blob/master/README.rst>`_

