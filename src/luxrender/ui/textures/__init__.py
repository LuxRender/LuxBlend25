# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Exporter Framework - LuxRender Plug-in
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

from properties_texture import TextureButtonsPanel

from ef.ui import described_layout
from ef.ef import ef

def discover_float_color(context):
	'''
	Try to determine whether to display float-type controls or color-type
	controls for this texture, depending on which type of texture slot
	it has been loaded into.
	
	There will be issues if the same texture is used both as a float and
	a colour, since the type returned will be the first one found only.
	'''
	
	float_col = False
	
	if context.object.type == 'LAMP':
			lm = context.object.data.luxrender_lamp
			for p in dir(lm):
				if p.endswith('_texturename') and getattr(lm, p) == context.texture.name:
					tex_slot = p.replace('_texturename', '')
					return getattr(lm, tex_slot)
			# then search in textures
			for ts in context.object.data.texture_slots:
				if hasattr(ts, 'texture') and hasattr(ts.texture, 'luxrender_texture'):
					lt = ts.texture.luxrender_texture
					for p in dir(lt):
						if p.endswith('_texturename') and getattr(lt, p) == context.texture.name:
							tex_slot = p.replace('_texturename', '')
							return getattr(lt, tex_slot)
	else:
		for ms in context.object.material_slots:
			# first search in the parent object's materials
			lm = ms.material.luxrender_material
			for p in dir(lm):
				if p.endswith('_texturename') and getattr(lm, p) == context.texture.name:
					tex_slot = p.replace('_texturename', '')
					return getattr(lm, tex_slot)
			
			# then search in textures
			for ts in ms.material.texture_slots:
				if hasattr(ts, 'texture') and hasattr(ts.texture, 'luxrender_texture'):
					lt = ts.texture.luxrender_texture
					for p in dir(lt):
						if p.endswith('_texturename') and getattr(lt, p) == context.texture.name:
							tex_slot = p.replace('_texturename', '')
							return getattr(lt, tex_slot)
	
	return float_col

class luxrender_texture_base(TextureButtonsPanel, described_layout):
	COMPAT_ENGINES = {'luxrender'}
	property_group_non_global = True
	
	@classmethod
	def property_reload(r_class):
		for tex in bpy.data.textures:
			r_class.property_create(tex.luxrender_texture)
	
	@classmethod
	def property_create(r_class, lux_tex_property_group):
		if not hasattr(lux_tex_property_group, r_class.property_group.__name__):
			ef.init_properties(lux_tex_property_group, [{
				'type': 'pointer',
				'attr': r_class.property_group.__name__,
				'ptype': r_class.property_group,
				'name': r_class.property_group.__name__,
				'description': r_class.property_group.__name__
			}], cache=False)
			ef.init_properties(r_class.property_group, r_class.properties, cache=False)
	
	# Overridden to provide data storage in the material, not the scene
	def draw(self, context):
		if context.texture is not None:
			self.property_create(context.texture.luxrender_texture)
			
			for p in self.controls:
				self.draw_column(p, self.layout, context.texture.luxrender_texture, supercontext=context)
				
	def poll(self, context):
		'''
		Only show LuxRender panel with 'Plugin' texture type, and
		if luxrender_texture.type in LUX_COMPAT
		'''
		
		return TextureButtonsPanel.poll(self, context) and context.texture.type == 'PLUGIN' and context.texture.luxrender_texture.type in self.LUX_COMPAT

