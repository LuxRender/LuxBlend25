# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
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

from luxrender.ui.materials import luxrender_material_base

class ui_luxrender_material(luxrender_material_base, bpy.types.Panel):
	'''
	Material Editor UI Panel
	'''
	
	bl_label	= 'LuxRender Materials'
	
	display_property_groups = [
		( ('material',), 'luxrender_material' )
	]
	
	def draw(self, context):
		row = self.layout.row(align=True)
		row.menu("LUXRENDER_MT_presets_material", text=bpy.types.LUXRENDER_MT_presets_material.bl_label)
		row.operator("luxrender.preset_material_add", text="", icon="ZOOMIN")
		row.operator("luxrender.preset_material_add", text="", icon="ZOOMOUT").remove_active = True
		
		super().draw(context)
