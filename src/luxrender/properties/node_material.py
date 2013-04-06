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
from ..properties import (luxrender_node, luxrender_material_node, get_linked_node, check_node_export_material, check_node_export_texture, check_node_get_paramset)
from ..properties.texture import (
	FloatTextureParameter, ColorTextureParameter, FresnelTextureParameter,
	import_paramset_to_blender_texture, shorten_name, refresh_preview
)
from ..export import ParamSet, process_filepath_data
from ..export.materials import (
	MaterialCounter, TextureCounter, ExportedMaterials, ExportedTextures, get_texture_from_scene
)
from ..outputs import LuxManager, LuxLog
from ..util import dict_merge

from ..properties.material import * # for now just the big hammer for starting autogenerate sockets

# Get all float properties
def get_props(TextureParameter, attribute):
	for prop in TextureParameter.get_properties():
		if prop['attr'].endswith('floatvalue'):
			value = prop[attribute]
	return value

# Colors are simpler, so we only get the colortuple here
def get_default(TextureParameter):
	TextureParameter = TextureParameter.default
	return TextureParameter

def add_nodetype(layout, type):
	layout.operator('node.add_node', text=type.bl_label).type = type.bl_rna.identifier

def get_socket_paramsets(sockets, make_texture):
	params = ParamSet()
	store_urougness = 0.0
	for socket in sockets:
		## The material panel expects an attribute "default_value", so we map our socket values here helpwise
		for attr in ('fresnel', 'color', 'amount', 'bump', 'cauchyb', 'filmidex', 'film', 'index', 'uroughness', 'vroughness', 'sigma', 'sc_asym', 'd'):
			if hasattr(socket, attr):
				value = getattr(socket, attr)
				setattr(socket, 'default_value', value)
		if not hasattr(socket, 'get_paramset'):
			print('No get_paramset() for socket %s' % socket.bl_idname)
			continue
		if socket.hide:
			print('Hidden socket %s will not be exported' % socket.bl_idname)
			continue
		if hasattr(socket, 'uroughness'):
			store_urougness = socket.uroughness
		if hasattr(socket, 'vroughness') and socket.sync_vroughness:
			socket.vroughness = store_urougness
			print("Syncing U/V-Roughness")
		params.update( socket.get_paramset(make_texture) )
	return params

#Create the submenus for the add-node menu
@LuxRenderAddon.addon_register_class
class lux_node_Materials_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_materials"
	bl_label = "Materials"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_material_carpaint_node)
		add_nodetype(layout, bpy.types.luxrender_material_cloth_node)
		add_nodetype(layout, bpy.types.luxrender_material_glass_node)
		add_nodetype(layout, bpy.types.luxrender_material_glass2_node)
		add_nodetype(layout, bpy.types.luxrender_material_glossy_node)
		add_nodetype(layout, bpy.types.luxrender_material_glossycoating_node)
		add_nodetype(layout, bpy.types.luxrender_material_glossytranslucent_node)
		add_nodetype(layout, bpy.types.luxrender_material_layered_node)
		add_nodetype(layout, bpy.types.luxrender_material_matte_node)
		add_nodetype(layout, bpy.types.luxrender_material_mattetranslucent_node)
		add_nodetype(layout, bpy.types.luxrender_material_metal_node)
		add_nodetype(layout, bpy.types.luxrender_material_metal2_node)
		add_nodetype(layout, bpy.types.luxrender_material_mirror_node)
		add_nodetype(layout, bpy.types.luxrender_material_mix_node)
		add_nodetype(layout, bpy.types.luxrender_material_null_node)
		add_nodetype(layout, bpy.types.luxrender_material_roughglass_node)
		add_nodetype(layout, bpy.types.luxrender_material_scatter_node)
		add_nodetype(layout, bpy.types.luxrender_material_velvet_node)

@LuxRenderAddon.addon_register_class
class lux_node_Inputs_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_inputs"
	bl_label = "Inputs"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_2d_coordinates_node)
		add_nodetype(layout, bpy.types.luxrender_3d_coordinates_node)
		add_nodetype(layout, bpy.types.luxrender_texture_constant_node) #Drawn as "Value", to match similar compositor/cycles node

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
		add_nodetype(layout, bpy.types.luxrender_texture_brick_node)
		add_nodetype(layout, bpy.types.luxrender_texture_bump_map_node)
		add_nodetype(layout, bpy.types.luxrender_texture_blender_clouds_node)
		add_nodetype(layout, bpy.types.luxrender_texture_fbm_node)
		add_nodetype(layout, bpy.types.luxrender_texture_image_map_node)
		add_nodetype(layout, bpy.types.luxrender_texture_blender_musgrave_node)
		add_nodetype(layout, bpy.types.luxrender_texture_normal_map_node)
		add_nodetype(layout, bpy.types.luxrender_texture_hitpointcolor_node) #These are drawn in the menu under the name "Vertex color/grey/alpha"
		add_nodetype(layout, bpy.types.luxrender_texture_hitpointgrey_node)
		add_nodetype(layout, bpy.types.luxrender_texture_hitpointalpha_node)
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
		add_nodetype(layout, bpy.types.luxrender_texture_cauchy_node)
		add_nodetype(layout, bpy.types.luxrender_texture_fresnelcolor_node)
		add_nodetype(layout, bpy.types.luxrender_texture_fresnelname_node)

@LuxRenderAddon.addon_register_class
class lux_node_Utilities_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_utilities"
	bl_label = "Utilities"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_texture_add_node)
		add_nodetype(layout, bpy.types.luxrender_texture_harlequin_node)
		add_nodetype(layout, bpy.types.luxrender_texture_mix_node)
		add_nodetype(layout, bpy.types.luxrender_texture_scale_node)
		add_nodetype(layout, bpy.types.luxrender_texture_subtract_node)
		add_nodetype(layout, bpy.types.luxrender_texture_uv_node)

@LuxRenderAddon.addon_register_class
class lux_node_Volumes_Menu(bpy.types.Menu):
	bl_idname = "Lux_NODE_volumes"
	bl_label = "Volumes"
	
	def draw(self, context):
		layout = self.layout
		add_nodetype(layout, bpy.types.luxrender_volume_clear_node)
		add_nodetype(layout, bpy.types.luxrender_volume_homogeneous_node)

#Draw the add-node menu from the submenus created above
@LuxRenderAddon.addon_register_class
class luxrender_mat_node_editor(bpy.types.NodeTree):
	'''LuxRender Material Nodes'''

	bl_idname = 'luxrender_material_nodes'
	bl_label = 'LuxRender Material Nodes'
	bl_icon = 'MATERIAL'
	
	@classmethod
	def poll(cls, context):
		return context.scene.render.engine == 'LUXRENDER_RENDER'
	
	#This function will set the current node tree to the one belonging to the active material
	@classmethod
	def get_from_context(cls, context):
		ob = context.active_object
		if ob and ob.type not in {'LAMP', 'CAMERA'}:
			ma = ob.active_material
			if ma != None:
				nt_name = ma.luxrender_material.nodetree
				if nt_name != '':
					return bpy.data.node_groups[ma.luxrender_material.nodetree], ma, ma
		# Uncomment if/when we make lamp nodes
		#	elif ob and ob.type == 'LAMP':
		#		la = ob.data
		#		nt_name = la.luxrender_lamp.nodetree
		#		if nt_name != '':
		#			return bpy.data.node_groups[la.luxrender_lamp.nodetree], la, la
		return (None, None, None)
		
	def draw_add_menu(self, context, layout):
		layout.label('LuxRender Node Types')
		layout.menu("Lux_NODE_inputs")
		layout.menu("Lux_NODE_outputs")
		layout.menu("Lux_NODE_materials")
		layout.menu("Lux_NODE_textures")
		layout.menu("Lux_NODE_spectra")
		layout.menu("Lux_NODE_fresnel")
		layout.menu("Lux_NODE_utilities")
		layout.menu("Lux_NODE_volumes")
		layout.menu("Lux_NODE_lights")


# Material nodes alphabetical
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_carpaint(luxrender_material_node):
	# Description string
	'''Car paint material node'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'luxrender_material_carpaint_node'
	# Label for nice name display
	bl_label = 'Car Paint Material'
	# Icon identifier
	bl_icon = 'MATERIAL'

    #Get menu items from old material editor properties
	for prop in luxrender_mat_carpaint.properties:
		if prop['attr'].startswith('name'):
			carpaint_items = prop['items']

	#Definitions for non-socket properties
	carpaint_presets = bpy.props.EnumProperty(name='Car Paint Presets', description='Luxrender Carpaint Presets', items=carpaint_items, default='-')

	#Definitions for sockets
	def init(self, context):
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		self.inputs.new('luxrender_TC_Ks1_socket', 'Specular Color 1')
		self.inputs.new('NodeSocketFloat', 'R1')
		self.inputs.new('NodeSocketFloat', 'M1')
		self.inputs.new('luxrender_TC_Ks2_socket', 'Specular Color 2')
		self.inputs.new('NodeSocketFloat', 'R2')
		self.inputs.new('NodeSocketFloat', 'M2')
		self.inputs.new('luxrender_TC_Ks3_socket', 'Specular Color 3')
		self.inputs.new('NodeSocketFloat', 'R3')
		self.inputs.new('NodeSocketFloat', 'M3')
		self.inputs.new('luxrender_TC_Kd_socket', 'Absorbtion Color')
		self.inputs.new('luxrender_TF_d_socket', 'Absorbtion Depth')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		
		self.outputs.new('NodeSocketShader', 'Surface')
		
	#Draw the non-socket properties
	def draw_buttons(self, context, layout):
		layout.prop(self, 'carpaint_presets')
	
	#Export routine for this node. This function stores code that LuxBlend will run when it exports materials.
	def export_material(self, make_material, make_texture):		
		mat_type = 'carpaint'
		
		carpaint_params = ParamSet()
		carpaint_params.update( get_socket_paramsets(self.inputs, make_texture) ) #have to export the sockets, or else bump/normal mapping won't work when using a preset
	
		if self.carpaint_presets != '-':
			carpaint_params.add_string('name', self.carpaint_presets)
			
		return make_material(mat_type, self.name, carpaint_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_cloth(luxrender_material_node):
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
		self.inputs.new('luxrender_TC_warp_Kd_socket', 'Warp Diffuse Color')
		self.inputs.new('luxrender_TC_warp_Ks_socket', 'Warp Specular Color')
		self.inputs.new('luxrender_TC_weft_Kd_socket', 'Weft Diffuse Color')
		self.inputs.new('luxrender_TC_weft_Ks_socket', 'Weft Specular Color')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'fabric_type')
		layout.prop(self, 'repeat_u')
		layout.prop(self, 'repeat_v')
		
	def export_material(self, make_material, make_texture):		
		mat_type = 'cloth'
		
		cloth_params = ParamSet()
		cloth_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		cloth_params.add_string('presetname', self.fabric_type)
		cloth_params.add_float('repeat_u', self.repeat_u)
		cloth_params.add_float('repeat_v', self.repeat_v)
				
		return make_material(mat_type, self.name, cloth_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glass(luxrender_material_node):
	'''Glass material node'''
	bl_idname = 'luxrender_material_glass_node'
	bl_label = 'Glass Material'
	bl_icon = 'MATERIAL'

	arch = bpy.props.BoolProperty(name='Architectural', description='Skips refraction during transmission, propagates alpha and shadow rays', default=False)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
		self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
		self.inputs.new('luxrender_TF_ior_socket', 'IOR')
		self.inputs.new('luxrender_TF_cauchyb_socket', 'Cauchy B')
		self.inputs.new('luxrender_TF_film_ior_socket', 'Film IOR')
		self.inputs.new('luxrender_TF_film_thick_socket', 'Film Thickness (nm)')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'arch')
		
	def export_material(self, make_material, make_texture):		
		mat_type = 'glass'
		
		glass_params = ParamSet()
		glass_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		glass_params.add_bool('architectural', self.arch)
		
		return make_material(mat_type, self.name, glass_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glass2(luxrender_material_node):
	'''Glass2 material node'''
	bl_idname = 'luxrender_material_glass2_node'
	bl_label = 'Glass2 Material'
	bl_icon = 'MATERIAL'

	arch = bpy.props.BoolProperty(name='Architectural', description='Skips refraction during transmission, propagates alpha and shadow rays', default=False)
	dispersion = bpy.props.BoolProperty(name='Dispersion', description='Enables chromatic dispersion, volume should have a sufficient data for this', default=False)
	
	def init(self, context):
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		
		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'arch')
		layout.prop(self, 'dispersion')
		
	def export_material(self, make_material, make_texture):		
		mat_type = 'glass2'
		
		glass2_params = ParamSet()
		
		glass2_params.add_bool('architectural', self.arch)
		glass2_params.add_bool('dispersion', self.dispersion)
		
		return make_material(mat_type, self.name, glass2_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossy(luxrender_material_node):
	'''Glossy material node'''
	bl_idname = 'luxrender_material_glossy_node'
	bl_label = 'Glossy Material'
	bl_icon = 'MATERIAL'

	def change_use_ior(self, context):
		## Specular/IOR representation switches
		self.inputs['Specular Color'].hide = self.use_ior
		self.inputs['IOR'].hide = not self.use_ior
	
	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy

	multibounce = bpy.props.BoolProperty(name='Multibounce', description='Enable surface layer multibounce', default=False)
	use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set Specularity by IOR', default=False, update=change_use_ior)
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False, update=change_use_anistropy)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
		self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
		self.inputs.new('luxrender_TF_ior_socket', 'IOR')
		self.inputs['IOR'].hide = True # initial state is hidden
		self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
		self.inputs.new('luxrender_TF_d_socket', 'Absorption depth (nm)')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')

	def draw_buttons(self, context, layout):
		layout.prop(self, 'multibounce')
		layout.prop(self, 'use_ior')
		layout.prop(self, 'use_anisotropy')

	def export_material(self, make_material, make_texture):
		mat_type = 'glossy'
		
		glossy_params = ParamSet()
		glossy_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		glossy_params.add_bool('multibounce', self.multibounce)
		
		return make_material(mat_type, self.name, glossy_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossycoating(luxrender_material_node):
	'''Glossy Coating material node'''
	bl_idname = 'luxrender_material_glossycoating_node'
	bl_label = 'Glossy Coating Material'
	bl_icon = 'MATERIAL'

	def change_use_ior(self, context):
		## Specular/IOR representation switches
		self.inputs['Specular Color'].hide = self.use_ior
		self.inputs['IOR'].hide = not self.use_ior
	
	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy
	
	multibounce = bpy.props.BoolProperty(name='Multibounce', description='Enable surface layer multibounce', default=False)
	use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set Specularity by IOR', default=False, update=change_use_ior)
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False, update=change_use_anistropy)
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Base Material')
		self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
		self.inputs.new('luxrender_TF_ior_socket', 'IOR')
		self.inputs['IOR'].hide = True # initial state is hidden
		self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
		self.inputs.new('luxrender_TF_d_socket', 'Absorption depth (nm)')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def draw_buttons(self, context, layout):
		layout.prop(self, 'multibounce')
		layout.prop(self, 'use_ior')
		layout.prop(self, 'use_anisotropy')
		
	def export_material(self, make_material, make_texture):
		mat_type = 'glossycoating'
		
		glossycoating_params = ParamSet()
		glossycoating_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		glossycoating_params.add_bool('multibounce', self.multibounce)
		
		def export_submat(socket):
			node = get_linked_node(socket)
			if not check_node_export_material(node):
				return None
			return node.export_material(make_material, make_texture)
		
		basemat_name = export_submat(self.inputs[0])
		
		glossycoating_params.add_string("basematerial", basemat_name)
		
		return make_material(mat_type, self.name, glossycoating_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossytranslucent(luxrender_material_node):
	'''Glossytranslucent material node'''
	bl_idname = 'luxrender_material_glossytranslucent_node'
	bl_label = 'Glossytranslucent Material'
	bl_icon = 'MATERIAL'
	
	def change_use_ior(self, context):
		## Specular/IOR representation switches
		self.inputs['Specular Color'].hide = self.use_ior
		self.inputs['IOR'].hide = not self.use_ior

	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy
	
	multibounce = bpy.props.BoolProperty(name='Multibounce', description='Enable surface layer multibounce', default=False)
	use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set Specularity by IOR', default=False, update=change_use_ior)
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False, update=change_use_anistropy)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		self.inputs.new('luxrender_TF_d_socket', 'Absorbtion Depth (nm)')
		self.inputs.new('luxrender_TC_Ka_socket', 'Absorbtion Color')
		self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
		self.inputs.new('luxrender_TF_ior_socket', 'IOR')
		self.inputs['IOR'].hide = True # initial state is hidden
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'multibounce')
		layout.prop(self, 'use_ior')
		layout.prop(self, 'use_anisotropy')

	def export_material(self, make_material, make_texture):
		mat_type = 'glossytranslucent'
		
		glossytranslucent_params = ParamSet()
		glossytranslucent_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		glossytranslucent_params.add_bool('multibounce', self.multibounce)
		
		return make_material(mat_type, self.name, glossytranslucent_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_layered(luxrender_material_node):
	'''Layered material node'''
	bl_idname = 'luxrender_material_layered_node'
	bl_label = 'Layered Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Material 1')
		self.inputs.new('NodeSocketFloat', 'Opacity 1')
		self.inputs.new('NodeSocketShader', 'Material 2')
		self.inputs.new('NodeSocketFloat', 'Opacity 2')
		self.inputs.new('NodeSocketShader', 'Material 3')
		self.inputs.new('NodeSocketFloat', 'Opacity 3')
		self.inputs.new('NodeSocketShader', 'Material 4')
		self.inputs.new('NodeSocketFloat', 'Opacity 4')

		
		self.outputs.new('NodeSocketShader', 'Surface')
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_matte(luxrender_material_node):
	'''Matte material node'''
	bl_idname = 'luxrender_material_matte_node'
	bl_label = 'Matte Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')
		
	def export_material(self, make_material, make_texture):
		mat_type = 'matte'
		
		matte_params = ParamSet()
		matte_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, matte_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mattetranslucent(luxrender_material_node):
	'''Mattetranslucent material node'''
	bl_idname = 'luxrender_material_mattetranslucent_node'
	bl_label = 'Matte Translucent Material'
	bl_icon = 'MATERIAL'
	
	energyconsrv = bpy.props.BoolProperty(name='Energy Conserving', default=True)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
		self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
		self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		
		self.outputs.new('NodeSocketShader', 'Surface')

	def export_material(self, make_material, make_texture):
		mat_type = 'mattetranslucent'
		
		mattetranslucent_params = ParamSet()
		mattetranslucent_params.update( get_socket_paramsets(self.inputs, make_texture) )
		mattetranslucent_params.add_bool('energyconserving', self.energyconsrv)
		
		return make_material(mat_type, self.name, mattetranslucent_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal(luxrender_material_node):
	'''Metal material node'''
	bl_idname = 'luxrender_material_metal_node'
	bl_label = 'Metal Material'
	bl_icon = 'MATERIAL'
	
	for prop in luxrender_mat_metal.properties:
		if prop['attr'].startswith('name'):
			metal_presets = prop['items']

	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy
	
	metal_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal Preset', items=metal_presets, default='aluminium')
	
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic roughness', default=False, update=change_use_anistropy)
	metal_nkfile = bpy.props.StringProperty(name='Nk File', description='Nk file path', subtype='FILE_PATH')
		
	def init(self, context):
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'metal_preset')
		if self.metal_preset == 'nk':
			layout.prop(self, 'metal_nkfile')
		layout.prop(self, 'use_anisotropy')
	
	def export_material(self, make_material, make_texture):
		print('export node: metal')
		
		mat_type = 'metal'
		
		metal_params = ParamSet()
		metal_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		if self.metal_preset == 'nk':	# use an NK data file
			# This function resolves relative paths (even in linked library blends)
			# and optionally encodes/embeds the data if the setting is enabled
			process_filepath_data(LuxManager.CurrentScene, self, self.metal_nkfile, metal_params, 'filename')
		else:
			# use a preset name
			metal_params.add_string('name', self.metal_preset)
		
		return make_material(mat_type, self.name, metal_params)
	
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal2(luxrender_material_node):
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

	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy

# 	metal2_type = bpy.props.EnumProperty(name='Type', description='Luxrender Metal2 Type', items=metal2_types, default='preset')
# 	metal2_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal2 Preset', items=metal2_presets, default='aluminium')
# 	metal2_nkfile = bpy.props.StringProperty(name='Nk File', description='Nk file path', subtype='FILE_PATH')
	
	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False, update=change_use_anistropy)
	
	def init(self, context):
		self.inputs.new('luxrender_fresnel_socket', 'IOR')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
# 		layout.prop(self, 'metal2_type')
# 		if self.metal2_type == 'preset':
# 			layout.prop(self, 'metal2_preset')
# 		if self.metal2_type == 'nk':
# 			layout.prop(self, 'metal2_nkfile')
		layout.prop(self, 'use_anisotropy')
	
	def export_material(self, make_material, make_texture):		
		mat_type = 'metal2'
		
		metal2_params = ParamSet()
		metal2_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, metal2_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mirror(luxrender_material_node):
	'''Mirror material node'''
	bl_idname = 'luxrender_material_mirror_node'
	bl_label = 'Mirror Material'
	bl_icon = 'MATERIAL'

	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
		self.inputs.new('luxrender_TF_film_ior_socket', 'Film IOR')
		self.inputs.new('luxrender_TF_film_thick_socket', 'Film Thickness (nm)')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')

		self.outputs.new('NodeSocketShader', 'Surface')

	def export_material(self, make_material, make_texture):		
		mat_type = 'mirror'
		
		mirror_params = ParamSet()
		mirror_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, mirror_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mix(luxrender_material_node):
	'''Mix material node'''
	bl_idname = 'luxrender_material_mix_node'
	bl_label = 'Mix Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_TF_amount_socket', 'Mix Amount')
		self.inputs.new('NodeSocketShader', 'Material 1')
		self.inputs.new('NodeSocketShader', 'Material 2')
		
		self.outputs.new('NodeSocketShader', 'Surface')
		
	def export_material(self, make_material, make_texture):
		print('export node: mix')
		
		mat_type = 'mix'
		
		mix_params = ParamSet()
		mix_params.update( get_socket_paramsets([self.inputs[0]], make_texture) )
		
		def export_submat(socket):
			node = get_linked_node(socket)
			if not check_node_export_material(node):
				return None
			return node.export_material(make_material, make_texture)
		
		mat1_name = export_submat(self.inputs[1])
		mat2_name = export_submat(self.inputs[2])
		
		mix_params.add_string("namedmaterial1", mat1_name)
		mix_params.add_string("namedmaterial2", mat2_name)
		
		return make_material(mat_type, self.name, mix_params)
		
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_null(luxrender_material_node):
	'''Null material node'''
	bl_idname = 'luxrender_material_null_node'
	bl_label = 'Null Material'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.outputs.new('NodeSocketShader', 'Surface')
		
	def export_material(self, make_material, make_texture):		
		mat_type = 'null'
		
		null_params = ParamSet()		
		
		return make_material(mat_type, self.name, null_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_roughglass(luxrender_material_node):
	'''Rough Glass material node'''
	bl_idname = 'luxrender_material_roughglass_node'
	bl_label = 'Rough Glass Material'
	bl_icon = 'MATERIAL'
	
	def change_use_anistropy(self, context):
		self.inputs['V-Roughness'].sync_vroughness = not self.use_anisotropy

	use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness', default=False, update=change_use_anistropy)
	dispersion = bpy.props.BoolProperty(name='Dispersion', description='Enables chromatic dispersion, volume should have a sufficient data for this', default=False)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
		self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
		self.inputs.new('luxrender_TF_ior_socket', 'IOR')
		self.inputs.new('luxrender_TF_cauchyb_socket', 'Cauchy B')
		self.inputs.new('luxrender_TF_bump_socket', 'Bump')
		self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
		self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')

		self.outputs.new('NodeSocketShader', 'Surface')

	def draw_buttons(self, context, layout):
		layout.prop(self, 'use_anisotropy')
		layout.prop(self, 'dispersion')

	def export_material(self, make_material, make_texture):		
		mat_type = 'roughglass'
		
		roughglass_params = ParamSet()
		roughglass_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		roughglass_params.add_bool('dispersion', self.dispersion)
		
		return make_material(mat_type, self.name, roughglass_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_scatter(luxrender_material_node):
	'''Scatter material node'''
	bl_idname = 'luxrender_material_scatter_node'
	bl_label = 'Scatter Material'
	bl_icon = 'MATERIAL'
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		self.inputs.new('luxrender_SC_asymmetry_socket', 'Asymmetry')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'scatter'
		
		scatter_params = ParamSet()
		scatter_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, scatter_params)

@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_velvet(luxrender_material_node):
	'''Velvet material node'''
	bl_idname = 'luxrender_material_velvet_node'
	bl_label = 'Velvet Material'
	bl_icon = 'MATERIAL'

	advanced = bpy.props.BoolProperty(name='Advanced', description='Advanced Velvet Parameters', default=False)
	thickness = bpy.props.FloatProperty(name='Thickness', description='', default=0.1, subtype='NONE', min=-0.0, max=1.0, soft_min=-0.0, soft_max=1.0, precision=2)
	p1 = bpy.props.FloatProperty(name='p1', description='', default=-2.0, subtype='NONE', min=-100.0, max=100.0, soft_min=-100.0, soft_max=100.0, precision=2)
	p2 = bpy.props.FloatProperty(name='p2', description='', default=-10.0, subtype='NONE', min=-100.0, max=100.0, soft_min=-100.0, soft_max=100.0, precision=2)
	p3 = bpy.props.FloatProperty(name='p2', description='', default=-2.0, subtype='NONE', min=-100.0, max=100.0, soft_min=-100.0, soft_max=100.0, precision=2)
	
	def init(self, context):
		self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'advanced')
		layout.prop(self, 'thickness')
		if self.advanced:
			layout.prop(self, 'p1')
			layout.prop(self, 'p2')
			layout.prop(self, 'p3')

	def export_material(self, make_material, make_texture):
		mat_type = 'velvet'
		
		velvet_params = ParamSet()
		velvet_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		velvet_params.add_float('thickness', self.thickness)
		velvet_params.add_float('p1', self.p1)
		velvet_params.add_float('p2', self.p2)
		velvet_params.add_float('p3', self.p3)
		
		return make_material(mat_type, self.name, velvet_params)

@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_clear(luxrender_material_node):
	'''Clear volume node'''
	bl_idname = 'luxrender_volume_clear_node'
	bl_label = 'Clear Volume'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_fresnel_socket', 'IOR')
		self.inputs.new('luxrender_AC_color_socket', 'Absorption Color')

		self.outputs.new('NodeSocketShader', 'Volume')
		
@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_homogeneous(luxrender_material_node):
	'''Homogeneous volume node'''
	bl_idname = 'luxrender_volume_homogeneous_node'
	bl_label = 'Homogeneous Volume'
	bl_icon = 'MATERIAL'

	def init(self, context):
		self.inputs.new('luxrender_fresnel_socket', 'IOR')
		self.inputs.new('luxrender_AC_color_socket', 'Absorption Color')
		self.inputs.new('luxrender_SC_color_socket', 'Scattering Color')
		self.inputs.new('luxrender_SC_asymmetry_socket', 'Asymmetry')
		
		self.outputs.new('NodeSocketShader', 'Volume')
		
@LuxRenderAddon.addon_register_class
class luxrender_light_area_node(luxrender_material_node):
	'''A custom node'''
	bl_idname = 'luxrender_light_area_node'
	bl_label = 'Area Light'
	bl_icon = 'LAMP'

	gain = bpy.props.FloatProperty(name='Gain', default=1.0)

	def init(self, context):
		self.inputs.new('NodeSocketColor', 'Light Color')
		self.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
		
		self.outputs.new('NodeSocketShader', 'Emission')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'gain')
		
@LuxRenderAddon.addon_register_class
class luxrender_material_output_node(luxrender_node):
	'''A custom node'''
	bl_idname = 'luxrender_material_output_node'
	bl_label = 'Material Output'
	bl_icon = 'MATERIAL'
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Surface')
		self.inputs.new('NodeSocketShader', 'Interior Volume')
		self.inputs.new('NodeSocketShader', 'Exterior Volume')
		self.inputs.new('NodeSocketShader', 'Emission')
	
	def export(self, scene, lux_context, material, mode='indirect'):
		
		print('Exporting node tree, mode: %s' % mode)
		
		surface_socket = self.inputs[0] # perhaps by name?
		if not surface_socket.is_linked:
			return set()
		
		surface_node = surface_socket.links[0].from_node
		
		tree_name = material.luxrender_material.nodetree
		
		make_material = None
		if mode == 'indirect':
			# named material exporting
			def make_material_indirect(mat_type, mat_name, mat_params):
				nonlocal lux_context
				nonlocal surface_node
				nonlocal material
				
				if mat_name != surface_node.name:
					material_name = '%s::%s' % (tree_name, mat_name)
				else:
					# this is the root material, don't alter name
					material_name = material.name
				
				print('Exporting material "%s", type: "%s", name: "%s"' % (material_name, mat_type, mat_name))
				mat_params.add_string('type', mat_type)
				ExportedMaterials.makeNamedMaterial(lux_context, material_name, mat_params)
				ExportedMaterials.export_new_named(lux_context)
				
				return material_name
				
			make_material = make_material_indirect
		elif mode == 'direct':
			# direct material exporting
			def make_material_direct(mat_type, mat_name, mat_params):
				nonlocal lux_context
				lux_context.material(mat_type, mat_params)
			make_material = make_material_direct
		
		
		# texture exporting, only one way
		def make_texture(tex_variant, tex_type, tex_name, tex_params):
			nonlocal lux_context
			texture_name = '%s::%s' % (tree_name, tex_name)
			with TextureCounter(texture_name):
				
				print('Exporting texture, variant: "%s", type: "%s", name: "%s"' % (tex_variant, tex_type, tex_name))
				
				ExportedTextures.texture(lux_context, texture_name, tex_variant, tex_type, tex_params)
				ExportedTextures.export_new(lux_context)
				
				return texture_name
		
		# start exporting that material...
		with MaterialCounter(material.name):
			if not (mode=='indirect' and material.name in ExportedMaterials.exported_material_names):
				if check_node_export_material(surface_node):
					surface_node.export_material(make_material=make_material, make_texture=make_texture)
		
		return set()

# Custom socket types, lookup parameters here:
# http://www.blender.org/documentation/blender_python_api_2_66a_release/bpy.props.html?highlight=bpy.props.floatproperty#bpy.props.FloatProperty

#Store our custom socket colors here as vars, so we don't have to remember what they are on every custom socket
float_socket_color = (0.63, 0.63, 0.63, 1.0) #Same as native NodeSocketFloat
color_socket_color = (0.9, 0.9, 0.0, 1.0) #Same as native NodeSocketColor
fresnel_socket_color = (0.33, 0.6, 0.85, 1.0)

@LuxRenderAddon.addon_register_class
class luxrender_fresnel_socket(bpy.types.NodeSocket):
	# Description string
	'''Fresnel texture I/O socket'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'luxrender_fresnel_socket'
	# Label for nice name display
	bl_label = 'IOR socket'
		
	def changed_preset(self, context):
		## connect preset -> property
		self.default_value = self.fresnel_presetvalue
	
	fresnel_presetvalue = bpy.props.FloatProperty(name='IOR-Preset', description='IOR', update=changed_preset)
	fresnel_presetstring = bpy.props.StringProperty(name='IOR_Preset Name', description='IOR')
	fresnel = bpy.props.FloatProperty(name='IOR', description='Optical dataset', default=1.52, precision=6)
	default_value = fresnel
	
	# Optional function for drawing the socket input value
	def draw(self, context, layout, node):
		box = layout.box()
		if self.fresnel == self.fresnel_presetvalue:
			menu_text = self.fresnel_presetstring
		else:
			menu_text = '-- Choose preset --'
		box.menu('LUXRENDER_MT_ior_presets', text=menu_text)
		box.prop(self, 'fresnel', text=self.name)
	
	# Socket color
	def draw_color(self, context, node):
		return fresnel_socket_color
	
	#Export routine for this socket
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			fresnel_params = ParamSet() \
				.add_texture('fresnel', tex_name)
		else:
			fresnel_params = ParamSet() \
				.add_float('fresnel', self.fresnel)
		
		return fresnel_params


##### custom color sockets ##### 

@LuxRenderAddon.addon_register_class
class luxrender_TC_Ka_socket(bpy.types.NodeSocket):
	'''Absorbtion Color socket'''
	bl_idname = 'luxrender_TC_Ka_socket'
	bl_label = 'Absorbtion Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Absorbtion Color', description='Absorbtion Color', default=get_default(TC_Ka), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		print('get_paramset diffuse color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ka_params = ParamSet() \
				.add_texture('Ka', tex_name)
		else:
			ka_params = ParamSet() \
				.add_color('Ka', self.color)
		
		return ka_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Kd_socket(bpy.types.NodeSocket):
	'''Diffuse Color socket'''
	bl_idname = 'luxrender_TC_Kd_socket'
	bl_label = 'Diffuse Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Diffuse Color', description='Diffuse Color', default=get_default(TC_Kd), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		print('get_paramset diffuse color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			kd_params = ParamSet() \
				.add_texture('Kd', tex_name)
		else:
			kd_params = ParamSet() \
				.add_color('Kd', self.color)
		
		return kd_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Kr_socket(bpy.types.NodeSocket):
	'''Reflection color socket'''
	bl_idname = 'luxrender_TC_Kr_socket'
	bl_label = 'Reflection Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Reflection Color', description='Reflection Color', default=get_default(TC_Kr), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			kr_params = ParamSet() \
				.add_texture('Kr', tex_name)
		else:
			kr_params = ParamSet() \
				.add_color('Kr', self.color)
		
		return kr_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Ks_socket(bpy.types.NodeSocket):
	'''Specular color socket'''
	bl_idname = 'luxrender_TC_Ks_socket'
	bl_label = 'Specular Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Specular Color', description='Specular Color', default=get_default(TC_Ks), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ks_params = ParamSet() \
				.add_texture('Ks', tex_name)
		else:
			ks_params = ParamSet() \
				.add_color('Ks', self.color)
		
		return ks_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Ks1_socket(bpy.types.NodeSocket):
	'''Specular color socket'''
	bl_idname = 'luxrender_TC_Ks1_socket'
	bl_label = 'Specular Color 1 socket'
	
	color = bpy.props.FloatVectorProperty(name='Specular Color 1', description='Specular Color 1', default=get_default(TC_Ks1), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ks1_params = ParamSet() \
				.add_texture('Ks1', tex_name)
		else:
			ks1_params = ParamSet() \
				.add_color('Ks1', self.color)
		
		return ks1_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Ks2_socket(bpy.types.NodeSocket):
	'''Specular color socket'''
	bl_idname = 'luxrender_TC_Ks2_socket'
	bl_label = 'Specular Color 2 socket'
	
	color = bpy.props.FloatVectorProperty(name='Specular Color 2', description='Specular Color 2', default=get_default(TC_Ks2), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ks2_params = ParamSet() \
				.add_texture('Ks2', tex_name)
		else:
			ks2_params = ParamSet() \
				.add_color('Ks2', self.color)
		
		return ks2_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Ks3_socket(bpy.types.NodeSocket):
	'''Specular color socket'''
	bl_idname = 'luxrender_TC_Ks3_socket'
	bl_label = 'Specular Color 3 socket'
	
	color = bpy.props.FloatVectorProperty(name='Specular Color 3', description='Specular Color 3', default=get_default(TC_Ks3), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ks3_params = ParamSet() \
				.add_texture('Ks3', tex_name)
		else:
			ks3_params = ParamSet() \
				.add_color('Ks3', self.color)
		
		return ks3_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_Kt_socket(bpy.types.NodeSocket):
	'''Transmission Color socket'''
	bl_idname = 'luxrender_TC_Kt_socket'
	bl_label = 'Transmission Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Transmission Color', description='Transmission Color', default=get_default(TC_Kt), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			kt_params = ParamSet() \
				.add_texture('Kt', tex_name)
		else:
			kt_params = ParamSet() \
				.add_color('Kt', self.color)
		
		return kt_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_warp_Kd_socket(bpy.types.NodeSocket):
	'''Warp Diffuse Color socket'''
	bl_idname = 'luxrender_TC_warp_Kd_socket'
	bl_label = 'Warp Diffuse socket'
	
	color = bpy.props.FloatVectorProperty(name='Warp Diffuse Color', description='Warp Diffuse Color', default=get_default(TC_warp_Kd), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			warp_kd_params = ParamSet() \
				.add_texture('warp_Kd', tex_name)
		else:
			warp_kd_params = ParamSet() \
				.add_color('warp_Kd', self.color)
		
		return warp_kd_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_warp_Ks_socket(bpy.types.NodeSocket):
	'''Warp Diffuse Color socket'''
	bl_idname = 'luxrender_TC_warp_Ks_socket'
	bl_label = 'Warp Specular socket'
	
	color = bpy.props.FloatVectorProperty(name='Warp Specular Color', description='Warp Specular Color', default=get_default(TC_warp_Ks), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			warp_ks_params = ParamSet() \
				.add_texture('warp_Ks', tex_name)
		else:
			warp_ks_params = ParamSet() \
				.add_color('warp_Ks', self.color)
		
		return warp_ks_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_weft_Kd_socket(bpy.types.NodeSocket):
	'''Weft Diffuse Color socket'''
	bl_idname = 'luxrender_TC_weft_Kd_socket'
	bl_label = 'Weft Diffuse socket'
	
	color = bpy.props.FloatVectorProperty(name='Weft Diffuse Color', description='Weft Diffuse Color', default=get_default(TC_weft_Kd), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color

	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			weft_kd_params = ParamSet() \
				.add_texture('weft_Kd', tex_name)
		else:
			weft_kd_params = ParamSet() \
				.add_color('weft_Kd', self.color)
		
		return weft_kd_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_weft_Ks_socket(bpy.types.NodeSocket):
	'''Weft Specular Color socket'''
	bl_idname = 'luxrender_TC_weft_Ks_socket'
	bl_label = 'Weft Specular socket'
	
	color = bpy.props.FloatVectorProperty(name='Weft Specular Color', description='Weft Specular Color', default=get_default(TC_weft_Ks), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			weft_ks_params = ParamSet() \
				.add_texture('weft_Ks', tex_name)
		else:
			weft_ks_params = ParamSet() \
				.add_color('weft_Ks', self.color)
		
		return weft_ks_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_backface_Ka_socket(bpy.types.NodeSocket):
	'''Backface Absorption Color socket'''
	bl_idname = 'luxrender_TC_backface_Ka_socket'
	bl_label = 'Backface Absorption socket'
	
	color = bpy.props.FloatVectorProperty(name='Backface Absorption Color', description='Backface Absorption Color', default=get_default(TC_backface_Ka), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			backface_ka_params = ParamSet() \
				.add_texture('backface_Ka', tex_name)
		else:
			backface_ka_params = ParamSet() \
				.add_color('backface_Ka', self.color)
		
		return backface_ka_params

@LuxRenderAddon.addon_register_class
class luxrender_TC_backface_Ks_socket(bpy.types.NodeSocket):
	'''Backface Specular Color socket'''
	bl_idname = 'luxrender_TC_backface_Ks_socket'
	bl_label = 'Backface Specular socket'
	
	color = bpy.props.FloatVectorProperty(name='Backface Specular Color', description='Backface Specular Color', default=get_default(TC_backface_Ks), subtype='COLOR', min=0.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color

	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			backface_ks_params = ParamSet() \
				.add_texture('backface_Ks', tex_name)
		else:
			backface_ks_params = ParamSet() \
				.add_color('backface_Ks', self.color)
		
		return backface_ks_params

@LuxRenderAddon.addon_register_class
class luxrender_AC_color_socket(bpy.types.NodeSocket):
	'''Volume absorption Color socket'''
	bl_idname = 'luxrender_AC_color_socket'
	bl_label = 'Absorption Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Scattering Color', description='Scattering Color', default=(1.0, 1.0, 1.0), subtype='COLOR', min=-1.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			ac_params = ParamSet() \
				.add_texture('sigma_a', tex_name)
		else:
			ac_params = ParamSet() \
				.add_color('sigma_a', self.color)
		
		return ac_params

@LuxRenderAddon.addon_register_class
class luxrender_SC_color_socket(bpy.types.NodeSocket):
	'''Scattering Color socket'''
	bl_idname = 'luxrender_SC_color_socket'
	bl_label = 'Scattering Color socket'
	
	color = bpy.props.FloatVectorProperty(name='Scattering Color', description='Scattering Color', default=(0.0, 0.0, 0.0), subtype='COLOR', min=-1.0, max=1.0)
	default_value = color
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.alignment = 'LEFT'
		row.prop(self, 'color', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			sc_params = ParamSet() \
				.add_texture('sigma_s', tex_name)
		else:
			sc_params = ParamSet() \
				.add_color('sigma_s', self.color)
		
		return sc_params

##### custom float sockets ##### 

@LuxRenderAddon.addon_register_class
class luxrender_TF_amount_socket(bpy.types.NodeSocket):
	# Description string
	'''Bump socket'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'luxrender_TF_amount_socket'
	# Label for nice name display
	bl_label = 'Amount socket'
	
	amount = bpy.props.FloatProperty(name=get_props(TF_amount, 'name'), description=get_props(TF_amount, 'description'), default=get_props(TF_amount, 'default'), subtype=get_props(TF_amount, 'subtype'), unit=get_props(TF_amount, 'unit'), min=get_props(TF_amount, 'min'), max=get_props(TF_amount, 'max'), soft_min=get_props(TF_amount, 'soft_min'), soft_max=get_props(TF_amount, 'soft_max'), precision=get_props(TF_amount, 'precision'))
	default_value = amount
	
	# Optional function for drawing the socket input value
	def draw(self, context, layout, node):
		layout.prop(self, 'amount', text=self.name)
	
	# Socket color
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset amount')
		tex_node = get_linked_node(self)
		if not tex_node is None:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			amount_params = ParamSet() \
				.add_texture('amount', tex_name)
		else:
			print('value %f' % self.amount)
			amount_params = ParamSet() \
				.add_float('amount', self.amount)
		
		return amount_params


@LuxRenderAddon.addon_register_class
class luxrender_TF_bump_socket(bpy.types.NodeSocket):
	'''Bump socket'''
	bl_idname = 'luxrender_TF_bump_socket'
	bl_label = 'Bump socket'
	
	bump = bpy.props.FloatProperty(name=get_props(TF_bumpmap, 'name'), description=get_props(TF_bumpmap, 'description'), default=get_props(TF_bumpmap, 'default'), subtype=get_props(TF_bumpmap, 'subtype'), unit=get_props(TF_bumpmap, 'unit'), min=get_props(TF_bumpmap, 'min'), max=get_props(TF_bumpmap, 'max'), soft_min=get_props(TF_bumpmap, 'soft_min'), soft_max=get_props(TF_bumpmap, 'soft_max'), precision=get_props(TF_bumpmap, 'precision'))
	default_value = bump
	
	def draw(self, context, layout, node):
		layout.label(text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color

	def get_paramset(self, make_texture):
		bumpmap_params = ParamSet()
		
		tex_node = get_linked_node(self)
		
		if tex_node and check_node_export_texture(tex_node):
			# only export linked bumpmap sockets
			tex_name = tex_node.export_texture(make_texture)
			
			bumpmap_params.add_texture('bumpmap', tex_name)
		
		return bumpmap_params
		
@LuxRenderAddon.addon_register_class
class luxrender_TF_cauchyb_socket(bpy.types.NodeSocket):
	'''Cauchy B socket'''
	bl_idname = 'luxrender_TF_cauchyb_socket'
	bl_label = 'Cauchy B socket'
	
	cauchyb = bpy.props.FloatProperty(name=get_props(TF_cauchyb, 'name'), description=get_props(TF_cauchyb, 'description'), default=get_props(TF_cauchyb, 'default'), subtype=get_props(TF_cauchyb, 'subtype'), min=get_props(TF_cauchyb, 'min'), max=get_props(TF_cauchyb, 'max'), soft_min=get_props(TF_cauchyb, 'soft_min'), soft_max=get_props(TF_cauchyb, 'soft_max'), precision=get_props(TF_cauchyb, 'precision'))
	default_value = cauchyb
	
	def draw(self, context, layout, node):
		layout.prop(self, 'cauchyb', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			cauchyb_params = ParamSet() \
				.add_texture('cauchyb', tex_name)
		else:
			cauchyb_params = ParamSet() \
				.add_float('cauchyb', self.cauchyb)
		
		return cauchyb_params
		
@LuxRenderAddon.addon_register_class
class luxrender_TF_film_ior_socket(bpy.types.NodeSocket):
	'''Thin film IOR socket'''
	bl_idname = 'luxrender_TF_film_ior_socket'
	bl_label = 'Thin Film IOR socket'

	def changed_preset(self, context):
		## connect preset -> property
		self.default_value = self.filmindex_presetvalue
	
	filmindex_presetvalue = bpy.props.FloatProperty(name='IOR-Preset', description='IOR', update=changed_preset)
	filmindex_presetstring = bpy.props.StringProperty(name='IOR_Preset Name', description='IOR')
	filmindex = bpy.props.FloatProperty(name=get_props(TF_filmindex, 'name'), description=get_props(TF_filmindex, 'description'), default=get_props(TF_filmindex, 'default'), subtype=get_props(TF_filmindex, 'subtype'), min=get_props(TF_filmindex, 'min'), max=get_props(TF_filmindex, 'max'), soft_min=get_props(TF_filmindex, 'soft_min'), soft_max=get_props(TF_filmindex, 'soft_max'), precision=get_props(TF_filmindex, 'precision'))
	default_value = filmindex
	
	def draw(self, context, layout, node):
		box = layout.box()
		if self.filmindex == self.filmindex_presetvalue:
			menu_text = self.filmindex_presetstring
		else:
			menu_text = '-- Choose preset --'
		box.menu('LUXRENDER_MT_ior_presets', text=menu_text)
		box.prop(self, 'filmindex', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			filmindex_params = ParamSet() \
				.add_texture('filmindex', tex_name)
		else:
			filmindex_params = ParamSet() \
				.add_float('filmindex', self.filmindex)
		
		return filmindex_params
		
@LuxRenderAddon.addon_register_class
class luxrender_TF_film_thick_socket(bpy.types.NodeSocket):
	'''Thin film IOR socket'''
	bl_idname = 'luxrender_TF_film_thick_socket'
	bl_label = 'Thin Film thickness socket'
	
	film = bpy.props.FloatProperty(name=get_props(TF_film, 'name'), description=get_props(TF_film, 'description'), default=get_props(TF_film, 'default'), subtype=get_props(TF_film, 'subtype'), min=get_props(TF_film, 'min'), max=get_props(TF_film, 'max'), soft_min=get_props(TF_film, 'soft_min'), soft_max=get_props(TF_film, 'soft_max'), precision=get_props(TF_film, 'precision'))
	default_value =  film
	
	def draw(self, context, layout, node):
		layout.prop(self, 'film', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			film_params = ParamSet() \
				.add_texture('film', tex_name)
		else:
			film_params = ParamSet() \
				.add_float('film', self.film)
		
		return film_params
		
@LuxRenderAddon.addon_register_class
class luxrender_TF_ior_socket(bpy.types.NodeSocket):
	'''IOR socket'''
	bl_idname = 'luxrender_TF_ior_socket'
	bl_label = 'IOR socket'
	
	def changed_preset(self, context):
		## connect preset -> property
		self.default_value = self.index_presetvalue

	index_presetvalue = bpy.props.FloatProperty(name='IOR-Preset', description='IOR', update=changed_preset)
	index_presetstring = bpy.props.StringProperty(name='IOR_Preset Name', description='IOR')
	index = bpy.props.FloatProperty(name=get_props(TF_index, 'name'), description=get_props(TF_index, 'description'), default=get_props(TF_index, 'default'), subtype=get_props(TF_index, 'subtype'), min=get_props(TF_index, 'min'), max=get_props(TF_index, 'max'), soft_min=get_props(TF_index, 'soft_min'), soft_max=get_props(TF_index, 'soft_max'), precision=get_props(TF_index, 'precision'))
	default_value = index
	
	def draw(self, context, layout, node):
		box = layout.box()
		if self.index == self.index_presetvalue:
			menu_text = self.index_presetstring
		else:
			menu_text = '-- Choose preset --'
		box.menu('LUXRENDER_MT_ior_presets', text=menu_text)
		box.prop(self, 'index', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			index_params = ParamSet() \
				.add_texture('index', tex_name)
		else:
			index_params = ParamSet() \
				.add_float('index', self.index)
		
		return index_params

@LuxRenderAddon.addon_register_class
class luxrender_TF_uroughness_socket(bpy.types.NodeSocket):
	'''U-Roughness socket'''
	bl_idname = 'luxrender_TF_uroughness_socket'
	bl_label = 'U-Roughness socket'
	
	uroughness = bpy.props.FloatProperty(name=get_props(TF_uroughness, 'name'), description=get_props(TF_uroughness, 'description'), default=get_props(TF_uroughness, 'default'), subtype=get_props(TF_uroughness, 'subtype'), min=get_props(TF_uroughness, 'min'), max=get_props(TF_uroughness, 'max'), soft_min=get_props(TF_uroughness, 'soft_min'), soft_max=get_props(TF_uroughness, 'soft_max'), precision=get_props(TF_uroughness, 'precision'))
	default_value = uroughness
	
	def draw(self, context, layout, node):
		if node.use_anisotropy: name = 'U-Roughness'
		else: name = 'Roughness'
		layout.prop(self, 'uroughness', text=name)
		
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset uroughness')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			roughness_params = ParamSet() \
				.add_texture('uroughness', tex_name)
		else:
			roughness_params = ParamSet() \
				.add_float('uroughness', self.uroughness)
		
		return roughness_params

@LuxRenderAddon.addon_register_class
class luxrender_TF_vroughness_socket(bpy.types.NodeSocket):
	'''V-Roughness socket'''
	bl_idname = 'luxrender_TF_vroughness_socket'
	bl_label = 'V-Roughness socket'
	
	sync_vroughness = bpy.props.BoolProperty(name='Sync V', default=False)
	vroughness = bpy.props.FloatProperty(name=get_props(TF_vroughness, 'name'), description=get_props(TF_vroughness, 'description'), default=get_props(TF_vroughness, 'default'), subtype=get_props(TF_vroughness, 'subtype'), min=get_props(TF_vroughness, 'min'), max=get_props(TF_vroughness, 'max'), soft_min=get_props(TF_vroughness, 'soft_min'), soft_max=get_props(TF_vroughness, 'soft_max'), precision=get_props(TF_uroughness, 'precision'))
	default_value = vroughness
	
	def draw(self, context, layout, node):
		layout.prop(self, 'vroughness', text=self.name)
		layout.active = node.use_anisotropy
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset vroughness')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			roughness_params = ParamSet() \
				.add_texture('vroughness', tex_name)
		else:
			roughness_params = ParamSet() \
				.add_float('vroughness', self.vroughness)
	
		
		return roughness_params

@LuxRenderAddon.addon_register_class
class luxrender_TF_sigma_socket(bpy.types.NodeSocket):
	'''Sigma socket'''
	bl_idname = 'luxrender_TF_sigma_socket'
	bl_label = 'Sigma socket'
	
	sigma = bpy.props.FloatProperty(name=get_props(TF_sigma, 'name'), description=get_props(TF_sigma, 'description'), default=get_props(TF_sigma, 'default'), subtype=get_props(TF_sigma, 'subtype'), min=get_props(TF_sigma, 'min'), max=get_props(TF_sigma, 'max'), soft_min=get_props(TF_sigma, 'soft_min'), soft_max=get_props(TF_sigma, 'soft_max'), precision=get_props(TF_sigma, 'precision'))
	default_value = sigma
	
	def draw(self, context, layout, node):
		layout.prop(self, 'sigma', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			sigma_params = ParamSet() \
				.add_texture('sigma', tex_name)
		else:
			sigma_params = ParamSet() \
				.add_float('sigma', self.sigma)
		
		return sigma_params
		
@LuxRenderAddon.addon_register_class
class luxrender_SC_asymmetry_socket(bpy.types.NodeSocket):
	'''Scattering asymmetry socket'''
	bl_idname = 'luxrender_SC_asymmetry_socket'
	bl_label = 'Scattering Asymmetry socket'
	
	sc_asym = bpy.props.FloatVectorProperty(name='Asymmetry', description='Scattering asymmetry RGB. -1 means backscatter, 0 is isotropic, 1 is forwards scattering', default=(0.0, 0.0, 0.0), min=-1.0, max=1.0, precision=4)
	default_value = sc_asym
	
	def draw(self, context, layout, node):
		row = layout.row()
		row.prop(self, 'sc_asym', text='')
		row.label(text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
		
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
				
			tex_name = tex_node.export_texture(make_texture)
			
			sc_asym_params = ParamSet() \
				.add_texture('g', tex_name)
		else:
			sc_asym_params = ParamSet() \
				.add_float('g', self.g)
		
		return sc_asym_params

@LuxRenderAddon.addon_register_class
class luxrender_TF_d_socket(bpy.types.NodeSocket):
	'''Absorption depth socket'''
	bl_idname = 'luxrender_TF_d_socket'
	bl_label = 'Absorption depth socket'
	
	d = bpy.props.FloatProperty(name=get_props(TF_d, 'name'), description=get_props(TF_d, 'description'), default=get_props(TF_d, 'default'), subtype=get_props(TF_d, 'subtype'), min=get_props(TF_d, 'min'), max=get_props(TF_d, 'max'), soft_min=get_props(TF_d, 'soft_min'), soft_max=get_props(TF_d, 'soft_max'), precision=get_props(TF_d, 'precision'))
	default_value = d
	
	def draw(self, context, layout, node):
		layout.prop(self, 'd', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		tex_node = get_linked_node(self)
		if tex_node:
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			d_params = ParamSet() \
				.add_texture('d', tex_name)
		else:
			d_params = ParamSet() \
				.add_float('d', self.d)
		
		return d_params
