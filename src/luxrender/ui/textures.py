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

from properties_texture import context_tex_datablock
from properties_texture import TextureButtonsPanel

from ef.ui import context_panel
from ef.ui import described_layout

from ef.ef import ef

import luxrender.properties.texture
from ..properties.util import has_property
from ..properties.texture import FloatTexture, ColorTexture

# TODO: Not sure how to morph type of tex1/tex2 from Float/Color depending on context
#TF_tex1 = FloatTexture('texture', 'tex1', 'Texture 1', 'luxrender_texture')
#TF_tex2 = FloatTexture('texture', 'tex2', 'Texture 2', 'luxrender_texture')

TF_amount			= FloatTexture('texture', 'amount', 'Amount', 'luxrender_texture')
TF_brickmodtex		= FloatTexture('texture', 'f_brickmodtex', 'Mod Tex', 'luxrender_texture')
TF_brickrun			= FloatTexture('texture', 'f_brickrun', 'Run', 'luxrender_texture')
TF_bricktex			= FloatTexture('texture', 'f_bricktex', 'Tex', 'luxrender_texture')
TF_mortartex		= FloatTexture('texture', 'f_mortartex', 'Mortar Tex', 'luxrender_texture')
TF_tex1				= FloatTexture('texture', 'f_tex1', 'Tex 1', 'luxrender_texture')
TF_tex2				= FloatTexture('texture', 'f_tex2', 'Tex 2', 'luxrender_texture')
TF_inside			= FloatTexture('texture', 'inside', 'Inside', 'luxrender_texture')
TF_outside			= FloatTexture('texture', 'outside', 'Outside', 'luxrender_texture')

def texture_visibility():
	vis = {}
	
	vis.update( TF_amount.get_visibility() )
	vis.update( TF_brickmodtex.get_visibility() )
	vis.update( TF_brickrun.get_visibility() )
	vis.update( TF_bricktex.get_visibility() )
	vis.update( TF_mortartex.get_visibility() )
	vis.update( TF_tex1.get_visibility() )
	vis.update( TF_tex2.get_visibility() )
	vis.update( TF_inside.get_visibility() )
	vis.update( TF_outside.get_visibility() )
	
	return vis

class texture_editor(context_panel, TextureButtonsPanel, described_layout):
	'''
	Texture Editor UI Panel
	'''
	
	bl_label = 'LuxRender Textures'
	COMPAT_ENGINES = {'luxrender'}
	
	property_group = luxrender.properties.texture.luxrender_texture
	
	# prevent creating luxrender_texture property group in Scene
	property_group_non_global = True
	
	def poll(self, context):
		'''
		Only show LuxRender panel with 'Plugin' texture type
		'''
		
		return TextureButtonsPanel.poll(self, context) and context.texture.type == 'PLUGIN'
	
	@staticmethod
	def property_reload():
		for tex in bpy.data.textures:
			texture_editor.property_create(tex)
			
	@staticmethod
	def property_create(texture):
		if not hasattr(texture, texture_editor.property_group.__name__):
			ef.init_properties(texture, [{
				'type': 'pointer',
				'attr': texture_editor.property_group.__name__,
				'ptype': texture_editor.property_group,
				'name': texture_editor.property_group.__name__,
				'description': texture_editor.property_group.__name__
			}], cache=False)
			ef.init_properties(texture_editor.property_group, texture_editor.properties, cache=False)
	
	# Overridden to provide data storage in the texture, not the scene
	def draw(self, context):
		if context.texture is not None:
			texture_editor.property_create(context.texture)
		
			for p in self.controls:
				self.draw_column(p, self.layout, context.texture, supercontext=context)
				
	controls = [
		'texture',
	] + \
	TF_amount.get_controls() + \
	TF_brickmodtex.get_controls() + \
	TF_brickrun.get_controls() + \
	TF_bricktex.get_controls() + \
	TF_mortartex.get_controls() + \
	TF_tex1.get_controls() + \
	TF_tex2.get_controls() + \
	TF_inside.get_controls() + \
	TF_outside.get_controls()
	
	visibility = texture_visibility()
	
	properties = [
		{
			'attr': 'texture',
			'type': 'enum',
			'name': 'Type',
			'description': 'LuxRender Texture Type',
			'items': [
				('bilerp', 'bilerp', 'bilerp'),
				('blackbody', 'blackbody', 'blackbody'),
				('brick', 'brick', 'brick'),
				('cauchy', 'cauchy', 'cauchy'),
				('checkerboard', 'checkerboard', 'checkerboard'),
				('constant', 'constant', 'constant'),
				('dots', 'dots', 'dots'),
				('equalenergy', 'equalenergy', 'equalenergy'),
				('fbm', 'fbm', 'fbm'),
				('frequency', 'frequency', 'frequency'),
				('gaussian', 'gaussian', 'gaussian'),
				('harlequin', 'harlequin', 'harlequin'),
				('imagemap', 'imagemap', 'imagemap'),
				('irregulardata', 'irregulardata', 'irregulardata'),
				('lampspectrum', 'lampspectrum', 'lampspectrum'),
				('marble', 'marble', 'marble'),
				('mix', 'mix', 'mix'),
				('regulardata', 'regulardata', 'regulardata'),
				('scale', 'scale', 'scale'),
				('sellmeier', 'sellmeier', 'sellmeier'),
				('tabulateddata', 'tabulateddata', 'tabulateddata'),
				('tabulatedfresnel', 'tabulatedfresnel', 'tabulatedfresnel'),
				('uv', 'uv', 'uv'),
				('windy', 'windy', 'windy'),
				('wrinkled', 'wrinkled', 'wrinkled'),
			],
		},
	] + \
	TF_amount.get_properties() + \
	TF_brickmodtex.get_properties() + \
	TF_brickrun.get_properties() + \
	TF_bricktex.get_properties() + \
	TF_mortartex.get_properties() + \
	TF_tex1.get_properties() + \
	TF_tex2.get_properties() + \
	TF_inside.get_properties() + \
	TF_outside.get_properties()
