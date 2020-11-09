#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Christian Felder <webmaster@bsm-felder.de>
# GNU Lesser General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/lgpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: ldap_entry
author:
    - Christian Felder (@cfelder)
short_description: Add or remove LDAP entries based on ldap3-orm models
version_added: "1.0.0"
description:
  - Add or remove LDAP entries based on ldap3-orm models.
  - Modifies existing entries.
  - Uses ldap3_orm configuration files. 
requirements:
  - "ldap3_orm >= 2.6.0"
options:
  config:
    description:
      - ldap3-orm configuration file (name or full qualified path)
      - See U(http://code.bsm-felder.de/doc/ldap3-orm/latest/classes/config.html)
        for an overview.
    required: True
    type: str
  dn:
    description:
      - Distinguished name, an unique identifier in your ldap tree
      - This attribute can be defined as a template using python's built-in
        C(format) function. All attributes defined in I(attributes)
        will be expanded. Furthermore the generated DN will be normalized
        and escaped using the C(ldap3.utils.dn.safe_dn) function.
    required: True
    type: str
  objectClass:
    description:
      - One or multiple object class(es) which should be included in the
        generated model.
      - Required when I(state=present) or when using templates in dn.
    required: False
  attributes:
    description:
      - Attributes necessary to create an entry defined by I(objectClass).
      - Attribute keys may be used as templates in I(dn) and are replaced
        with its values
      - Required when I(state=present) or when using templates in dn. 
  state:
    description:
      - Whether a ldap entry should be present or absent
    default: present
    type str
    choices:
      - present
      - absent
'''


EXAMPLES = r'''
- name: Create or Update entry
  l3o.ldap3_orm.ldap_entry:
    config: default
    dn: "uid={uid},ou=People,dc=example,dc=com"
    objectClass: inetOrgPerson
    attributes:
      uid: guest
      sn: User
      cn: Guest User

- name: Delete entry using objectClass and attributes with templated dn
  l3o.ldap3_orm.ldap_entry:
    config: default
    state: absent
    dn: "uid={uid},ou=People,dc=example,dc=com"
    objectClass: inetOrgPerson
    attributes:
      uid: guest
      sn: Mustermann 42
      cn: Max Mustermann 42

- name: Delete entry using dn only
  l3o.ldap3_orm.ldap_entry:
    config: default
    state: absent
    dn: "uid=guest,ou=People,dc=example,dc=com"

# Reuses existing ldap3_orm configuration files
# see: :py:class:`~ldap3_orm.config.config` for more details
# example configuration file, e.g.
# ~/.config/ldap3-orm/default
#
#url = "ldaps://ldap.example.com"
#base_dn = "dc=example,dc=com"

#connconfig = dict(
#    user = "cn=Directory Manager",
#    password = "KL!p5SPi;zMhsgbL@utAFVMWuLDoy!2xJE1@zJ3Gl3o=",
#)
'''


RETURN = r'''
actions:
  description:
    - Human-readable representation of actions performed on the ldap server
  returned: always
  type: list
  sample:
    - Created dn 'uid=guest,ou=People,dc=example,dc=com'
    - Modified dn 'uid=guest,ou=People,dc=example,dc=com'
    - Deleted dn 'uid=guest,ou=People,dc=example,dc=com'
'''


import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.six import string_types

try:
    import ldap3_orm
    from ldap3 import ALL_ATTRIBUTES, BASE
    from ldap3_orm import EntryType
    from ldap3_orm._config import read_config, config
    from ldap3_orm._connection import create_connection
except ImportError:
    IMPORT_ERROR = traceback.format_exc()
    ldap3_orm = None


class LdapEntry(object):

    def __init__(self, module, results):
        object.__init__(self)

        self.module = module
        self.results = results
        self.state = self.module.params.get("state")

        self.object_classes = self.module.params.get("objectClass")
        self.dn =  self.module.params.get("dn")
        self.attributes = self.module.params.get("attributes")

        # create config singleton and connection
        config.apply(read_config(self.module.params.get("config")))
        self.connection = create_connection(config.url, config.connconfig)

        if self.state == "present":
            self.present()
        if self.state == "absent":
            self.absent()

    def _get_entry(self):
        if self.object_classes and self.dn and self.module.params["attributes"]:
            cls = EntryType(self.dn, self.object_classes, self.connection)
            entry = cls(**self.module.params["attributes"])
            search_dn = entry.entry_dn
        else:
            entry = None
            search_dn = self.dn
        self.connection.search(search_dn, "(objectClass=top)", BASE,
                               attributes=ALL_ATTRIBUTES)

        # return EntryType and search result
        if self.connection.entries:
            return entry, self.connection.entries[0]
        return entry, None

    def absent(self):
        origin = self._get_entry()[1]
        if origin:
            if self.connection.delete(origin.entry_dn):
                self.results["changed"] = True
                self.results["actions"].append(
                    "Deleted dn '{}'".format(origin.entry_dn))
            else:
                self.module.fail_json(
                    msg="Could not delete dn '{}'. {}".format(
                        origin.entry_dn, self.connection.result["message"]))

    def present(self):
        entry, origin = self._get_entry()
        # if entry already exists, update existing entry
        if origin:
            origin = origin.entry_writable()
            # add missing classes
            missing_classes = set(entry.objectClass) - set(origin.objectClass)
            if missing_classes:
                origin.objectClass += missing_classes
            # update values in origin from new instance entry
            for attr in entry.entry_attributes:
                if attr in "objectClass":
                    continue
                attribute = getattr(entry, attr)
                if getattr(origin, attr) != attribute:
                    setattr(origin, attr, attribute.value)

            if origin.entry_changes:
                if origin.entry_commit_changes():
                    self.results["changed"] = True
                    self.results["actions"].append(
                        "Modified dn '{}'".format(entry.entry_dn))
                else:
                    self.module.fail_json(
                        msg="Could not modify dn '{}'. {}".format(
                            entry.entry_dn, self.connection.result["message"]))
        else:
            # create new entry
            self.connection.add(entry.entry_dn, entry.object_classes,
                                entry.entry_attributes_as_dict)

            self.results["changed"] = True
            self.results["actions"].append("Created dn '{}'".format(entry.entry_dn))

def main():
    module = AnsibleModule(
        argument_spec=dict(
            config=dict(type="str", required=True),
            attributes=dict(default={}, type="dict"),
            cls=dict(type="str"),
            objectClass=dict(type='raw'),
            dn=dict(type="str"),
            state=dict(type="str", default="present",
                       choices=["absent", "present"]),
        ),
        supports_check_mode=True,
        mutually_exclusive=(
            ["cls", "objectClass"],
            ["cls", "dn"],
        )
    )

    if not ldap3_orm:
        module.fail_json(msg=missing_required_lib("ldap3_orm"),
                         exception=IMPORT_ERROR)

    # Check if objectClass is present when needed
    if module.params["state"] == "present" and not module.params["cls"]:
        if module.params["objectClass"] is None:
            module.fail_json(msg="At least one objectClass must be provided.")
        if module.params["dn"] is None:
            module.fail_json(msg="dn must be provided when using objectClass")

        # Check if objectClass is of the correct type
        if not (isinstance(module.params["objectClass"], string_types) or
                isinstance(module.params["objectClass"], list)):
            module.fail_json(
                msg="objectClass must be either a string or a list.")

    results = dict(
        changed=False,
        actions=[],
    )
    LdapEntry(module, results)
    module.exit_json(**results)

if __name__ == "__main__":
    main()
