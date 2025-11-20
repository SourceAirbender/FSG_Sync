from __future__ import annotations

import logging

from gramps.gen.plug.menu import FilterOption, NumberOption, BooleanOption
from gramps.gen.filters import CustomFilters, GenericFilterFactory, rules
from gramps.gui.plug import MenuToolOptions
from gramps.gen.const import GRAMPS_LOCALE as glocale

logger = logging.getLogger(__name__)

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class CompareOptions(MenuToolOptions):
    """Builds the menu options for the FamilySearch Compare batch tool."""

    def __init__(self, name, person_id=None, dbstate=None):
        logger.debug("CompareOptions.__init__(name=%s, person_id=%s)", name, person_id)
        self.db = dbstate.get_database() if dbstate else None
        super().__init__(name, person_id, dbstate)

    def add_menu_options(self, menu):
        logger.debug("CompareOptions.add_menu_options")
        self._add_general_options(menu)

    def _add_general_options(self, menu):
        logger.debug("CompareOptions._add_general_options")
        category_name = _("FamilySearch Compare Options")

        # Days between runs
        self._opt_days_between = NumberOption(
            _("Days between comparisons"), 0, 0, 99
        )
        self._opt_days_between.set_help(
            _("Number of days between two comparisons.")
        )
        menu.add_option(category_name, "gui_days", self._opt_days_between)

        # Force compare
        self._opt_force = BooleanOption(_("Force comparison"), True)
        self._opt_force.set_help(
            _(
                "Compare regardless of the number of days since the last run."
            )
        )
        menu.add_option(category_name, "gui_needed", self._opt_force)

        # Person Filter
        all_persons_rule = rules.person.Everyone([])
        filter_option = FilterOption(_trans.gettext("Person Filter"), 0)
        menu.add_option(category_name, "Person", filter_option)

        filter_list = CustomFilters.get_filters("Person")
        GenericFilter = GenericFilterFactory("Person")
        all_filter = GenericFilter()
        all_filter.set_name(
            _trans.gettext("All %s") % (_trans.gettext("Persons"))
        )
        all_filter.add_rule(all_persons_rule)

        # Only add the generic filter if it isn't already in the menu
        if not any(fltr.get_name() == all_filter.get_name() for fltr in filter_list):
            filter_list.insert(0, all_filter)
        filter_option.set_filters(filter_list)
