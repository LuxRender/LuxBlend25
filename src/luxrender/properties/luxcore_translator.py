# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Simon Wendsche (BYOB)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#

from ..extensions_framework import declarative_property_group
from ..extensions_framework.validate import Logic_OR as O, Logic_Operator as LO, Logic_AND as A

from .. import LuxRenderAddon


@LuxRenderAddon.addon_register_class
class luxcore_translatorsettings(declarative_property_group):
    """
    Storage class for LuxCore translator settings.
    """

    ef_attach_to = ['Scene']

    controls = [
        'override_materials',
        ['override_glass', 'override_lights', 'override_null']
    ]

    visibility = {
        'override_glass': {'override_materials': True},
        'override_lights': {'override_materials': True},
        'override_null': {'override_materials': True},
    }

    alert = {}

    properties = [
        {
            'type': 'bool',
            'attr': 'override_materials',
            'name': 'Override Materials (Clay Render)',
            'description': 'Replace all scene materials with a white matte material',
            'default': False,
            'save_in_preset': True
        },
        {
            'type': 'bool',
            'attr': 'override_glass',
            'name': 'Glass',
            'description': 'Replace glass materials, too',
            'default': False,
            'save_in_preset': True
        },
        {
            'type': 'bool',
            'attr': 'override_lights',
            'name': 'Emission',
            'description': 'Replace light emitting materials, too (turning them off)',
            'default': False,
            'save_in_preset': True
        },
        {
            'type': 'bool',
            'attr': 'override_null',
            'name': 'Null',
            'description': 'Replace null materials, too',
            'default': False,
            'save_in_preset': True
        },
    ]
