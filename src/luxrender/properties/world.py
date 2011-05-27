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
import math

import bpy

from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_OR as O, Logic_AND as A

from .. import LuxRenderAddon
from ..export import ParamSet
from ..export.materials import ExportedTextures
from ..outputs.pure_api import LUXRENDER_VERSION
from ..properties.material import texture_append_visibility
from ..properties.texture import (
	ColorTextureParameter, FloatTextureParameter, FresnelTextureParameter
)
from ..util import dict_merge

def WorldVolumeParameter(attr, name):
	return [
		{
			'attr': '%s_volume' % attr,
			'type': 'string',
			'name': '%s_volume' % attr,
			'description': '%s_volume' % attr,
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': attr,
			'src': lambda s,c: s.scene.luxrender_volumes,
			'src_attr': 'volumes',
			'trg': lambda s,c: c.luxrender_world,
			'trg_attr': '%s_volume' % attr,
			'name': name
		},
	]

@LuxRenderAddon.addon_register_class
class luxrender_world(declarative_property_group):
	ef_attach_to = ['Scene']
	
	controls = [
		'default_interior',
		'default_exterior'
	]
	
	properties = [] + \
		WorldVolumeParameter('default_interior', 'Default Interior') + \
		WorldVolumeParameter('default_exterior', 'Default Exterior')

class VolumeDataColorTextureParameter(ColorTextureParameter):
	#texture_collection = 'textures'
	def texture_collection_finder(self):
		def func(s,c):
			return s.world	# Look in the current world object for fresnel textures
		return func
	
	def texture_slot_set_attr(self):
		def func2(s,c):
			return c
		return func2

class VolumeDataFloatTextureParameter(FloatTextureParameter):
	#texture_collection = 'textures'
	def texture_collection_finder(self):
		def func(s,c):
			return s.world	# Look in the current world object for fresnel textures
		return func
	
	def texture_slot_set_attr(self):
		def func2(s,c):
			return c
		return func2

class VolumeDataFresnelTextureParameter(FresnelTextureParameter):
	#texture_collection = 'textures'
	def texture_collection_finder(self):
		def func(s,c):
			return s.world	# Look in the current world object for fresnel textures
		return func
	
	def texture_slot_set_attr(self):
		def func2(s,c):
			return c
		return func2

# Volume related Textures
TFR_IOR			= VolumeDataFresnelTextureParameter('fresnel', 'IOR',			add_float_value = True, min=0.0, max=25.0, default=1.0)

TC_absorption	= VolumeDataColorTextureParameter('absorption', 'Absorption',	default=(1.0,1.0,1.0))
TC_sigma_a		= VolumeDataColorTextureParameter('sigma_a', 'Absorption',		default=(1.0,1.0,1.0))
TC_sigma_s		= VolumeDataColorTextureParameter('sigma_s', 'Scattering',		default=(0.0,0.0,0.0))

def volume_types():
	v_types =  [
		('clear', 'Clear', 'clear')
	]
	
	if LUXRENDER_VERSION >= '0.8':
		v_types.extend([
			('homogeneous', 'Homogeneous', 'homogeneous')
		])
	
	return v_types

@LuxRenderAddon.addon_register_class
class luxrender_volume_data(declarative_property_group):
	'''
	Storage class for LuxRender volume data. The
	luxrender_volumes object will store 1 or more of
	these in its CollectionProperty 'volumes'.
	'''
	
	ef_attach_to = []	# not attached
	
	controls = [
		'type',
	] + \
	[
		'draw_ior_menu',
	] + \
	TFR_IOR.controls + \
	TC_absorption.controls + \
	TC_sigma_a.controls + \
	[
		'depth','absorption_scale'
	] + \
	TC_sigma_s.controls + \
	[
		'scattering_scale',
		'g',
	]
	
	visibility = dict_merge(
		{
			'scattering_scale': { 'type': 'homogeneous', 'sigma_s_usecolortexture': False },
			'g': { 'type': 'homogeneous' },
			'depth': O([ A([{ 'type': 'clear' }, { 'absorption_usecolortexture': False }]), A([{'type': 'homogeneous' }, { 'sigma_a_usecolortexture': False }]) ])
		},
		TFR_IOR.visibility,
		TC_absorption.visibility,
		TC_sigma_a.visibility,
		TC_sigma_s.visibility
	)
	
	visibility = texture_append_visibility(visibility, TC_absorption, { 'type': 'clear' })
	visibility = texture_append_visibility(visibility, TC_sigma_a, { 'type': 'homogeneous' })
	visibility = texture_append_visibility(visibility, TC_sigma_s, { 'type': 'homogeneous' })
	
	properties = [
		{
			'type': 'ef_callback',
			'attr': 'draw_ior_menu',
			'method': 'draw_ior_menu',
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'items': volume_types(),
			'save_in_preset': True
		},
	] + \
	TFR_IOR.properties + \
	TC_absorption.properties + \
	TC_sigma_a.properties + \
	TC_sigma_s.properties + \
	[
		{
			'type': 'float',
			'attr': 'depth',
			'name': 'Abs. at depth',
			'description': 'Object will match absorption color at this depth in metres',
			'default': 1.0,
			'min': 0.00001,
			'soft_min': 0.00001,
			'max': 1000.0,
			'soft_max': 1000.0,
			'precision': 6,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'absorption_scale',
			'name': 'Abs. scale',
			'description': 'Scale the absorption by this value',
			'default': 1.0,
			'min': 0.00001,
			'soft_min': 0.00001,
			'max': 1000.0,
			'soft_max': 1000.0,
			'precision': 6,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'scattering_scale',
			'name': 'Scattering scale',
			'description': 'Scattering colour will be multiplied by this value',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 10000.0,
			'soft_max': 10000.0,
			'precision': 6,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'g',
			'name': 'Asymmetry',
			'description': 'Scattering asymmetry RGB. -1 means backscatter, 0 is isotropic, 1 is forwards scattering.',
			'default': (0.0, 0.0, 0.0),
			'min': -1.0,
			'soft_min': -1.0,
			'max': 1.0,
			'soft_max': 1.0,
			'precision': 4,
			'save_in_preset': True
		},
	]
	
	def api_output(self, lux_context):
		vp = ParamSet()
		
		def absorption_at_depth_scaled(i):
			# This is copied from the old LuxBlend, I don't pretend to understand it, DH
			depthed = (-math.log(max([(float(i)),1e-30]))/(self.depth*self.absorption_scale)) * ((float(i))==1.0 and -1 or 1)
			#print('abs xform: %f -> %f' % (i,depthed))
			return depthed
		
		if self.type == 'clear':
			vp.update( TFR_IOR.get_paramset(self) )
			vp.update( TC_absorption.get_paramset(self, value_transform_function=absorption_at_depth_scaled) )
			
			if self.absorption_usecolortexture and self.absorption_scale!=1.0:
				
				tex_found = False
				for psi in vp:
					if psi.type == 'texture' and psi.name == 'absorption':
						tex_found = True
						absorption_tex = psi.value
				
				if tex_found:
					sv = ExportedTextures.next_scale_value()
					texture_name = 'absorption_scaled_%i' % sv
					ExportedTextures.texture(
						lux_context,
						texture_name,
						'color',
						'scale',
						ParamSet() \
						.add_color(
							'tex1',
							[self.absorption_scale]*3
						) \
						.add_texture(
							'tex2',
							absorption_tex
						)
					)
					ExportedTextures.export_new(lux_context)
					# overwrite the absorption tex name with the scaled tex
					vp.add_texture('absorption', texture_name)
		
		if self.type == 'homogeneous':
			def scattering_scale(i):
				return i * self.scattering_scale
			vp.update( TFR_IOR.get_paramset(self) )
			vp.add_color('g', self.g)
			vp.update( TC_sigma_a.get_paramset(self, value_transform_function=absorption_at_depth_scaled) )
			vp.update( TC_sigma_s.get_paramset(self, value_transform_function=scattering_scale) )
			
			if self.absorption_usecolortexture and self.absorption_scale!=1.0:
				
				tex_found = False
				for psi in vp:
					if psi.type == 'texture' and psi.name == 'sigma_a':
						tex_found = True
						sigma_a_tex = psi.value
				
				if tex_found:
					sv = ExportedTextures.next_scale_value()
					texture_name = 'sigma_a_scaled_%i' % sv
					ExportedTextures.texture(
						lux_context,
						texture_name,
						'color',
						'scale',
						ParamSet() \
						.add_color(
							'tex1',
							[self.absorption_scale]*3
						) \
						.add_texture(
							'tex2',
							sigma_a_tex
						)
					)
					ExportedTextures.export_new(lux_context)
					# overwrite the sigma_a tex name with the scaled tex
					vp.add_texture('sigma_a', texture_name)
		
		return self.type, vp
	
	def load_paramset(self, world, ps):
		psi_accept = {
			'g': 'color'
		}
		psi_accept_keys = psi_accept.keys()
		for psi in ps:
			if psi['name'] in psi_accept_keys and psi['type'].lower() == psi_accept[psi['name']]:
				setattr(self, psi['name'], psi['value'])
			
			if psi['type'].lower() == 'texture':
				# assign the referenced texture to the world
				tex_slot = world.texture_slots.add()
				tex_slot.texture = bpy.data.textures[psi['value']]
		
		TFR_IOR.load_paramset(self, ps)
		TC_absorption.load_paramset(self, ps)
		TC_sigma_a.load_paramset(self, ps)
		TC_sigma_s.load_paramset(self, ps)
		
		# reverse the scattering scale factor
		def sct_col_in_range(val):
			return val>=0.01 and val<=0.99
		def find_scale(Sr,Sg,Sb):
			scale_val = 100000.0
			# simultaneously scale all abs values to a sensible range
			while not (sct_col_in_range(Sr*scale_val) and sct_col_in_range(Sg*scale_val) and sct_col_in_range(Sb*scale_val)):
				scale_val /= 10
				# bail out at minimum scale if we can't find a perfect solution
				if scale_val < 1e-6: break
			return scale_val
		
		# get the raw value from the paramset, value assigned via TC_sigma_s.load_paramset
		# will already have been clamped to (0,1)
		sct_col = [0.0, 0.0, 0.0]
		for psi in ps:
			if psi['type'] == 'color' and psi['name'] == 'sigma_s':
				sct_col = psi['value']
		scl_val = find_scale(*sct_col)
		self.scattering_scale = 1/scl_val
		self.sigma_s_color = [c*scl_val for c in sct_col]
		
		# reverse the absorption_at_depth process
		def rev_aad_in_range(val):
			abs = math.e**-val
			return abs>=0.01 and abs<=0.99
		
		def find_depth(Ar,Ag,Ab):
			depth_val = 100000.0
			# simultaneously scale all abs values to a sensible range
			while not (rev_aad_in_range(Ar*depth_val) and rev_aad_in_range(Ag*depth_val) and rev_aad_in_range(Ab*depth_val)):
				depth_val /= 10
				# bail out at minimum depth if we can't find a perfect solution
				if depth_val < 1e-6: break
			return depth_val
		
		if self.type == 'clear':
			abs_col = [1.0, 1.0, 1.0]
			# get the raw value from the paramset, value assigned via TC_absorption.load_paramset
			# will already have been clamped to (0,1)
			for psi in ps:
				if psi['type'] == 'color' and psi['name'] == 'absorption':
					abs_col = psi['value']
			self.depth = find_depth(*abs_col)
			
			self.absorption_color = [math.e**-(c*self.depth) for c in abs_col]
			
		if self.type == 'homogeneous':
			abs_col = [1.0, 1.0, 1.0]
			# get the raw value from the paramset, value assigned via TC_sigma_a.load_paramset
			# will already have been clamped to (0,1)
			for psi in ps:
				if psi['type'] == 'color' and psi['name'] == 'sigma_a':
					abs_col = psi['value']
			self.depth = find_depth(*abs_col)
			
			self.sigma_a_color = [math.e**-(c*self.depth) for c in abs_col]

@LuxRenderAddon.addon_register_class
class luxrender_volumes(declarative_property_group):
	'''
	Storage class for LuxRender Material volumes.
	'''
	
	ef_attach_to = ['Scene']
	
	controls = [
		'volumes_select',
		['op_vol_add', 'op_vol_rem']
	]
	
	visibility = {}
	
	properties = [
		{
			'type': 'collection',
			'ptype': luxrender_volume_data,
			'name': 'volumes',
			'attr': 'volumes',
			'items': []
		},
		{
			'type': 'int',
			'name': 'volumes_index',
			'attr': 'volumes_index',
		},
		{
			'type': 'template_list',
			'name': 'volumes_select',
			'attr': 'volumes_select',
			'trg': lambda sc,c: c.luxrender_volumes,
			'trg_attr': 'volumes_index',
			'src': lambda sc,c: c.luxrender_volumes,
			'src_attr': 'volumes',
		},
		{
			'type': 'operator',
			'attr': 'op_vol_add',
			'operator': 'luxrender.volume_add',
			'text': 'Add',
			'icon': 'ZOOMIN',
		},
		{
			'type': 'operator',
			'attr': 'op_vol_rem',
			'operator': 'luxrender.volume_remove',
			'text': 'Remove',
			'icon': 'ZOOMOUT',
		},
	]

@LuxRenderAddon.addon_register_class
class luxrender_lightgroup_data(declarative_property_group):
	'''
	Storage class for LuxRender light groups. The
	luxrender_lightgroups object will store 1 or more of
	these in its CollectionProperty 'lightgroups'.
	'''
	
	ef_attach_to = []	# not attached
	
	controls = [
		# enabled is drawn manually in the UI class
		'gain'
	]
	properties = [
		{
			'type': 'bool',
			'attr': 'enabled',
			'name': 'Enabled',
			'description': 'Enable this light group',
			'default': True
		},
		{
			'type': 'float',
			'attr': 'gain',
			'name': 'Gain',
			'description': 'Overall gain for this light group',
			'min': 0.0,
			'soft_min': 0.0,
			'default': 1.0
		}
	]

@LuxRenderAddon.addon_register_class
class luxrender_lightgroups(declarative_property_group):
	'''
	Storage class for LuxRender Light Groups.
	'''
	
	ef_attach_to = ['Scene']
	
	controls = [
		'op_lg_add',
		'ignore',
	]
	
	visibility = {}
	
	properties = [
		{
			'type': 'collection',
			'ptype': luxrender_lightgroup_data,
			'name': 'lightgroups',
			'attr': 'lightgroups',
			'items': []
		},
		{
			'type': 'int',
			'name': 'lightgroups_index',
			'attr': 'lightgroups_index',
		},
		{
			'type': 'operator',
			'attr': 'op_lg_add',
			'operator': 'luxrender.lightgroup_add',
			'text': 'Add',
			'icon': 'ZOOMIN',
		},
		{
			'type': 'bool',
			'attr': 'ignore',
			'name': 'Merge light groups',
			'description': 'Combine all light groups into one. Enable this for final renders, or to decrease RAM usage.',
			'default': False
		},
	]
	
	def is_enabled(self, name):
		if name != '' and name in self.lightgroups:
			return self.lightgroups[name].enabled
		return True