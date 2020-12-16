Ansible Collection - l3o.ldap3_orm
==================================

This repo hosts the ``l3o.ldap3_orm`` Ansible Collection.

Example Playbook
----------------

To use a module from this collection, please reference the full namespace,
collection name, and modules name that you want to use, e.g: 

```yaml
    - name: Using ldap3_orm collection
      hosts: localhost
      tasks:
        - name: Create or Update entry on ldap server referenced in default
          l3o.ldap3_orm.ldap_entry:
            config: default
            dn: "uid={uid},ou=People,dc=example,dc=com"
            objectClass: inetOrgPerson
            attributes:
              uid: guest
              sn: User
              cn: Guest User
```

Ansible dynamic inventory plugin for ipaHostGroups
--------------------------------------------------

This collection provides a dynamic inventory plugin for creating an inventory
from ``ipaHostGroup`` entries on a freeipa server.

* [Hostgroup inventory plugin](README-freeipa_ldap3_orm.md)


License
-------

LGPLv3+

Author Information
------------------

Christian Felder
