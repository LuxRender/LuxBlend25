# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Jens Verwiebe, Jason Clarke
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

import re

import bpy

from extensions_framework import declarative_property_group

from .. import LuxRenderAddon
from ..properties.texture import (
	FloatTextureParameter, ColorTextureParameter, FresnelTextureParameter,
	import_paramset_to_blender_texture, shorten_name, refresh_preview
)
from ..export import ParamSet, process_filepath_data
from ..export.materials import (
	MaterialCounter, ExportedMaterials, ExportedTextures, add_texture_parameter, get_texture_from_scene
)
from ..outputs import LuxManager, LuxLog
from ..util import dict_merge

from ..properties.material import * # for now just the big hammer for starting autogenerate sockets

def add_nodetype(layout, type):
	layout.operator('node.add_node', text=type.bl_label).type = type.bl_rna.identifier

@LuxRenderAddon.addon_register_class
class lux_node_Materials_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_materials"
	bl_label = "Materials"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_material_carpaint_node)
		add_nodetype(layout, bpy.types.luxrender_material_cloth_node)
#		add_nodetype(layout, bpy.types.luxrender_material_glass_node)
#		add_nodetype(layout, bpy.types.luxrender_material_glass2_node)
#		add_nodetype(layout, bpy.types.luxrender_material_glossy_node)
#		add_nodetype(layout, bpy.types.luxrender_material_glossycoating_node)
#		add_nodetype(layout, bpy.types.luxrender_material_glossytranslucent_node)
		add_nodetype(layout, bpy.types.luxrender_material_matte_node)
		add_nodetype(layout, bpy.types.luxrender_material_mattetranslucent_node)
		add_nodetype(layout, bpy.types.luxrender_material_metal_node)
		add_nodetype(layout, bpy.types.luxrender_material_metal2_node)
#		add_nodetype(layout, bpy.types.luxrender_material_mirror_node)
		add_nodetype(layout, bpy.types.luxrender_material_mix_node)
		add_nodetype(layout, bpy.types.luxrender_material_null_node)
#		add_nodetype(layout, bpy.types.luxrender_material_roughglass_node)
#		add_nodetype(layout, bpy.types.luxrender_material_scatter_node)
#		add_nodetype(layout, bpy.types.luxrender_material_shinymetal_node)
#		add_nodetype(layout, bpy.types.luxrender_material_velvet_node)

@LuxRenderAddon.addon_register_class
class lux_node_Outputs_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_outputs"
	bl_label = "Outputs"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_material_output_node)

@LuxRenderAddon.addon_register_class
class lux_node_Lights_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_lights"
	bl_label = "Lights"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_light_area_node)
		
@LuxRenderAddon.addon_register_class
class lux_node_Textures_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_textures"
	bl_label = "Textures"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_texture_blender_clouds_node)
		add_nodetype(layout, bpy.types.luxrender_texture_fbm_node)
		add_nodetype(layout, bpy.types.luxrender_texture_harlequin_node)
		add_nodetype(layout, bpy.types.luxrender_texture_blender_musgrave_node)
		add_nodetype(layout, bpy.types.luxrender_texture_windy_node)
		add_nodetype(layout, bpy.types.luxrender_texture_wrinkled_node)

@LuxRenderAddon.addon_register_class
class lux_node_Spectra_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_spectra"
	bl_label = "Spectra"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_texture_blackbody_node)
		add_nodetype(layout, bpy.types.luxrender_texture_colordepth_node)
		add_nodetype(layout, bpy.types.luxrender_texture_gaussian_node)
		add_nodetype(layout, bpy.types.luxrender_texture_tabulateddata_node)
		
@LuxRenderAddon.addon_register_class
class lux_node_Frensel_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_fresnel"
	bl_label = "Fresnel Data"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_texture_fresnelcolor_node)
		add_nodetype(layout, bpy.types.luxrender_texture_fresnelname_node)


@LuxRenderAddon.addon_register_class
class lux_node_Volumes_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_volumes"
	bl_label = "Volumes"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_volume_clear_node)
		add_nodetype(layout, bpy.types.luxrender_volume_homogeneous_node)

@LuxRenderAddon.addon_register_class
class luxrender_mat_node_editor(bpy.types.NodeTree):
	'''Experiment in making a node editor for Lux'''

	bl_idname = 'luxrender_material_nodes'
	bl_label = 'LuxRender Material Nodes'
	bl_icon = 'MATERIAL'
	
	@classmethod
	def poll(cls, context):
		return context.scene.render.engine == 'LUXRENDER_RENDER'
		
	def draw_add_menu(self, context, layout):
		layout.label('LuxRender Node Types')
		layout.menu("Lux_NODE_outputs")
		layout.menu("Lux_NODE_materials")
		layout.menu("Lux_NODE_textures")
		layout.menu("Lux_NODE_spectra")
		layout.menu("Lux_NODE_fresnel")
		layout.menu("Lux_NODE_volumes")
		layout.menu("Lux_NODE_lights")


# Material nodes alphabetical
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_carpaint(bpy.types.Node):
	# Description string
	'''Car paint material node'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'luxrender_material_carpaint_node'
	# Label for nice name display
	bl_label = 'Car Paint Material'
	# Icon identifier
	bl_icon = 'MATERIAL'

	for prop in luxrender_mat_carpaint.properties:
		if prop['attr'].startswith('name'):
			carpaint_items = prop['items']
	
	carpaint_presets = bpy.props.EnumProperty(name='Car Paint Presets', description='Luxrender Carpaint Presets', items=carpaint_items, default='-')
	
	def init(self, context):
		self.inputs.new('NodeSocketColor', 'Diffuse Color')
		self.inputs.new('NodeSocketColor', 'Specular Color 1')
		self.inputs.new('NodeSocketFloat', 'R1')
		self.inputs.new('NodeSocketFloat', 'M1')
		self.inputs.new('NodeSocketColor', 'Specular Color 2')
		self.inputs.new('NodeSocketFloat', 'R2')
		self.inputs.new('NodeSocketFloat', 'M2')
		self.inputs.new('NodeSocketColor', 'Specular Color 3')
		self.inputs.new('NodeSocketFloat', 'R3')
		self.inputs.new('NodeSocketFloat', 'M3')
		self.inputs.new('NodeSocketColor', 'Absorbtion Color')
		self.inputs.new('NodeSocketFloat', 'Absorbtion Depth')
		

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'carpaint_presets')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_cloth(bpy.types.Node):
	'''Cloth material node'''
	bl_idname = 'luxrender_material_cloth_node'
	bl_label = 'Cloth Material'
	bl_icon = 'MATERIAL'
	
	for prop in luxrender_mat_cloth.properties:
		if prop['attr'].startswith('presetname'):
			cloth_items = prop['items']

	fabric_type = bpy.props.EnumProperty(name='Cloth Fabric', description='Luxrender Cloth Fabric', items=cloth_items, default='denim')
	repeat_u = bpy.props.FloatProperty(name='Repeat U', default=100.0)
	repeat_v = bpy.props.FloatProperty(name='Repeat V', default=100.0)

	
	def init(self, context):
		self.inputs.new('NodeSocketColor', 'Warp Diffuse Color')
		self.inputs.new('NodeSocketColor', 'Warp Specular Color')
		self.inputs.new('NodeSocketColor', 'Weft Diffuse Color')
		self.inputs.new('NodeSocketColor', 'Weft Specular Color')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'fabric_type')
		layout.prop(self, 'repeat_u')
		layout.prop(self, 'repeat_v')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_matte(bpy.types.Node):
	'''Matte material node'''
	bl_idname = 'luxrender_material_matte_node'
	bl_label = 'Matte Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('NodeSocketColor', 'Diffuse Color')
		self.inputs.new('NodeSocketFloat', 'Sigma')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mattetranslucent(bpy.types.Node):
	'''Matte material node'''
	bl_idname = 'luxrender_material_mattetranslucent_node'
	bl_label = 'Matte Translucent Material'
	bl_icon = 'MATERIAL'
	
	def init(self, context):
		self.inputs.new('NodeSocketBool', 'Energy Conserving')
		self.inputs.new('NodeSocketColor', 'Refection Color')
		self.inputs.new('NodeSocketColor', 'Transmission Color')
		self.inputs.new('NodeSocketFloat', 'Sigma')
		
		self.outputs.new('NodeSocketShader', 'Surface')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal(bpy.types.Node):
	'''Metal material node'''
	bl_idname = 'luxrender_material_metal_node'
	bl_label = 'Metal Material'
	bl_icon = 'MATERIAL'
	
#	for prop in luxrender_mat_metal.properties:
#		print("-------------", prop['type'], prop['attr']) # all properties material has
	
	for prop in luxrender_mat_metal.properties:
		if prop['attr'].startswith('name'):
			metal_presets = prop['items']
	
	metal_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal Preset', items=metal_presets, default='aluminium')
	
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic roughness', default=False)
# 	use_exponent = bpy.props.BoolProperty(name='Use Exponent', description='Use exponent', default=False)
		
	def init(self, context):
		self.inputs.new('NodeSocketFloat', 'U-Roughness')
		self.inputs.new('NodeSocketFloat', 'V-Roughness')
# 		self.inputs.new('NodeSocketFloat', 'U-Exponent')
# 		self.inputs.new('NodeSocketFloat', 'V-Exponent')

		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'metal_preset')
		layout.prop(self, 'use_anisotropy')
# 		layout.prop(self, 'use_exponent')

	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal2(bpy.types.Node):
	'''Metal2 material node'''
	bl_idname = 'luxrender_material_metal2_node'
	bl_label = 'Metal2 Material'
	bl_icon = 'MATERIAL'
	
	for prop in luxrender_mat_metal2.properties:
		if prop['attr'].startswith('metaltype'):
			metal2_types = prop['items']
	
	for prop in luxrender_mat_metal2.properties:
		if prop['attr'].startswith('preset'):
			metal2_presets = prop['items']

	metal2_type = bpy.props.EnumProperty(name='Type', description='Luxrender Metal2 Type', items=metal2_types, default='preset')
	metal2_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal2 Preset', items=metal2_presets, default='aluminium')
	metal2_nkfile = bpy.props.StringProperty(name='Nk File', description='Nk file path', subtype='FILE_PATH')
	
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False)
#	use_exponent = bpy.props.BoolProperty(name='Use Exponent', description='Anisotropic Roughness', default=False)
	
	def init(self, context):
		self.inputs.new('NodeSocketFloat', 'U-Roughness')
		self.inputs.new('NodeSocketFloat', 'V-Roughness')
#		self.inputs.new('NodeSocketFloat', 'U-Exponent')
#		self.inputs.new('NodeSocketFloat', 'V-Exponent')
		
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'metal2_type')
		if self.metal2_type == 'preset':
			layout.prop(self, 'metal2_preset')
		if self.metal2_type == 'nk':
			layout.prop(self, 'metal2_nkfile')
		layout.prop(self, 'use_anisotropy')
#		layout.prop(self, 'use_exponent')

	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mix(bpy.types.Node):
	'''Mix material node'''
	bl_idname = 'luxrender_material_mix_node'
	bl_label = 'Mix Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('NodeSocketFloat', 'Mix Amount')
		self.inputs.new('NodeSocketShader', 'Material 1')
		self.inputs.new('NodeSocketShader', 'Material 2')


		self.outputs.new('NodeSocketShader', 'Surface')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_null(bpy.types.Node):
	'''Null material node'''
	bl_idname = 'luxrender_material_null_node'
	bl_label = 'Null Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.outputs.new('NodeSocketShader', 'Surface')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'
		
#Volume and area light nodes

@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_clear(bpy.types.Node):
	'''Clear volume node'''
	bl_idname = 'luxrender_volume_clear_node'
	bl_label = 'Clear Volume'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_fresnel_socket', 'IOR')
		self.inputs.new('NodeSocketColor', 'Absorption Color')

		self.outputs.new('NodeSocketShader', 'Volume')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'
		
@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_homogeneous(bpy.types.Node):
	'''Homogeneous volume node'''
	bl_idname = 'luxrender_volume_homogeneous_node'
	bl_label = 'Homogeneous Volume'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_fresnel_socket', 'IOR')
		self.inputs.new('NodeSocketColor', 'Absorption Color')
		self.inputs.new('NodeSocketColor', 'Scattering Color')
		self.inputs.new('NodeSocketColor', 'Asymmetry')

		self.outputs.new('NodeSocketShader', 'Volume')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'
		
@LuxRenderAddon.addon_register_class
class luxrender_light_area_node(bpy.types.Node):
	'''A custom node'''
	bl_idname = 'luxrender_light_area_node'
	bl_label = 'Area Light'
	bl_icon = 'LAMP'

	gain = bpy.props.FloatProperty(name='Gain', default=1.0)

	def init(self, context):
		self.inputs.new('NodeSocketColor', 'Light Color')
		
		self.outputs.new('NodeSocketShader', 'Emission')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'gain')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'

@LuxRenderAddon.addon_register_class
class luxrender_material_output_node(bpy.types.Node):
	'''A custom node'''
	bl_idname = 'luxrender_material_output_node'
	bl_label = 'Material Output'
	bl_icon = 'MATERIAL'
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Surface')
		self.inputs.new('NodeSocketShader', 'Interior Volume')
		self.inputs.new('NodeSocketShader', 'Exterior Volume')
		self.inputs.new('NodeSocketShader', 'Emission')
		
	#This node is only for the Lux node-tree
	@classmethod	
	def poll(cls, tree):
		return tree.bl_idname == 'luxrender_material_nodes'


# Custom socket types
		
@LuxRenderAddon.addon_register_class
class luxrender_fresnel_socket(bpy.types.NodeSocket):
	# Description string
	'''Fresnel texture I/O socket'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'luxrender_fresnel_socket'
	# Label for nice name display
	bl_label = 'IOR socket'
	
	
	fresnel = bpy.props.FloatProperty(name='IOR', description='Optical dataset', default=1.52)
	
	# Optional function for drawing the socket input value
	def draw(self, context, layout, node):
		layout.prop(self, 'fresnel', text=self.name)
	
	# Socket color
	def draw_color(self, context, node):
		return (0.33, 0.6, 0.85, 1.0)
