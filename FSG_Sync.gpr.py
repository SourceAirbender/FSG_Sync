# first version



register(GRAMPLET,
         id = "FSG_Sync Gramplet",
         name = _("FSG_Sync"),
         description = _("Gramps & FamilySearch Integration"),
         status = STABLE,
         fname="FSG_Sync.py",
         height=100,
         expand=True,
         gramplet = 'FSG_Sync',
         gramplet_title=_("FSG_Sync_v6"),
         detached_width = 500,
         detached_height = 500,
         version = 'alpha v1.0.2',
         gramps_target_version= '5.2',
         navtypes=["Person"],
         requires_mod=["packaging","requests"],
         )

