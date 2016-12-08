API Documentation
=================


Environment
+++++++++++

.. autoclass:: jujuclient.Environment
   :members: connect, close, add_local_charm_dir, add_local_charm,
             add_charm, resolve_charms, download_charm, get_charm,
             info, status, get_env_constraints, set_env_constraints,
             get_env_config, set_env_config, unset_env_config,
             set_env_agent_version, agent_version,
	     debug_log, run_on_all_machines, run, add_machine,
	     add_machines,
	     register_machine,
	     register_machines,
	     destroy_machines,
	     provisioning_script,
	     retry_provisioning,
	     wait_for_units,
	     get_watch,
	     add_relation,
	     remove_relation,
	     deploy,
	     set_config,
	     unset_config,
	     set_charm,
	     get_service,
	     get_config,
	     get_constraints,
	     set_constraints,
	     update_service,
	     destroy_service,
	     expose,
	     unexpose,
	     valid_relation_names,
	     add_units,
	     add_unit,
	     remove_units,
	     resolved,
	     get_public_address,
	     get_private_address,
	     set_annotation,
	     get_annotation


User Management
+++++++++++++++

.. autoclass:: jujuclient.UserManager
   :members: add, enable, disable, list, set_password


Charms
++++++

.. autoclass:: jujuclient.Charms
   :members: info, list


Annotations
+++++++++++

Supercedes the functionality in Environment

.. autoclass:: jujuclient.Annotations
   :members: get, set


SSH Keys
++++++++

.. autoclass:: jujuclient.KeyManager
   :members: add, delete, list, import_keys


Backups
+++++++

.. autoclass:: jujuclient.Backups
   :members: create, info, list, remove, download


HIgh Availability
+++++++++++++++++

.. autoclass:: jujuclient.HA
   :members: ensure_availability


Image Manager
+++++++++++++

.. autoclass:: jujuclient.ImageManager
   :members: list, delete

Actions
+++++++

.. autoclass:: jujuclient.Actions
   :members: service_actions, enqueue_units, cancel, info, find, all, pending, completed, cancel


Environment Manager
+++++++++++++++++++

.. autoclass:: jujuclient.EnvironmentManager
   :members: create, list
