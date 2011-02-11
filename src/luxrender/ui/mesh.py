# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Daniel Genrich
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
import bpy
from properties_data_mesh import MeshButtonsPanel

from extensions_framework.ui import property_group_renderer

@bpy.utils.register_class
class meshes(MeshButtonsPanel, property_group_renderer, bpy.types.Panel):
	bl_label = 'LuxRender Mesh Options'
	COMPAT_ENGINES = {'luxrender'}
	
	display_property_groups = [
		( ('mesh',), 'luxrender_mesh' )
	]
	
	def draw(self, context):
		if context.object.luxrender_object.append_external_mesh and context.object.luxrender_object.hide_proxy_mesh:
			msg = 'Mesh options not available when\n' \
				'object is using external PLY mesh\n' \
				'and hide proxy mesh is set.'
			for t in msg.split('\n'):
				self.layout.label(t)
		else:
			super().draw(context)
