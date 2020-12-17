#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Christian Felder <webmaster@bsm-felder.de>
# GNU Lesser General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/lgpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()
        config = self._task.args.get("config", None)

        if not config:
            result["failed"] = True
            result["msg"] = "config is required"

        # decrypt config if vault-encrypted
        module_args["config"] = self._loader.get_real_file(config)

        result.update(self._execute_module(
            module_name="l3o.ldap3_orm.ldap_entry",
            module_args=module_args,
            task_vars=task_vars, tmp=tmp)
        )
        return result
