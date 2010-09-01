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
import math#

import bpy

from ef.ef import declarative_property_group

from luxrender.properties import has_property
from luxrender.properties.texture import FresnelTextureParameter, FloatTextureParameter, ColorTextureParameter
from luxrender.export import ParamSet
from luxrender.export.materials import add_texture_parameter

def MaterialParameter(attr, name, property_group):
	return [
		{
			'attr': '%s_material' % attr,
			'type': 'string',
			'name': '%s_material' % attr,
			'description': '%s_material' % attr,
		},
		{
			'type': 'prop_search',
			'attr': attr,
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: getattr(c, property_group),
			'trg_attr': '%s_material' % attr,
			'name': name
		},
	]

def VolumeParameter(attr, name, property_group):
	return [
		{
			'attr': '%s_volume' % attr,
			'type': 'string',
			'name': '%s_volume' % attr,
			'description': '%s_volume' % attr,
		},
		{
			'type': 'prop_search',
			'attr': attr,
			'src': lambda s,c: s.scene.luxrender_volumes,
			'src_attr': 'volumes',
			'trg': lambda s,c: getattr(c, property_group),
			'trg_attr': '%s_volume' % attr,
			'name': name
		},
	]

class VolumeDataColorTextureParameter(ColorTextureParameter):
	texture_collection = 'textures'
	def texture_collection_finder(self):
		def func(s,c):
			return s.main
		return func
	
	def texture_slot_set_attr(self):
		def func2(s,c):
			return c
		return func2

class VolumeDataFresnelTextureParameter(FresnelTextureParameter):
	texture_collection = 'textures'
	def texture_collection_finder(self):
		def func(s,c):
			return s.main
		return func
	
	def texture_slot_set_attr(self):
		def func2(s,c):
			return c
		return func2

# Fresnel Textures
TFR_IOR			= VolumeDataFresnelTextureParameter('fresnel', 'IOR', add_float_value = False)

# Float Textures
TF_amount		= FloatTextureParameter('amount', 'Mix Amount',				add_float_value=True, min=0.0, default=0.5, max=1.0 )
TF_bumpmap		= FloatTextureParameter('bumpmap', 'Bump Map',				add_float_value=True, precision=6, multiply_float=True, ignore_zero=True )
TF_cauchyb		= FloatTextureParameter('cauchyb', 'Cauchy B',				add_float_value=True, default=0.0, min=0.0, max=1.0 ) # default 0.0 for OFF
TF_d			= FloatTextureParameter('d', 'Absorption Depth',			add_float_value=True, default=0.15, min=0.0, max=15.0 )
TF_film			= FloatTextureParameter('film', 'Thin Film Thickness (nm)',	add_float_value=True, min=0.0, default=0.0, max=1500.0 ) # default 0.0 for OFF
TF_filmindex	= FloatTextureParameter('filmindex', 'Film IOR',			add_float_value=True, default=1.5, min=1.0, max=6.0 )
TF_index		= FloatTextureParameter('index', 'IOR',						add_float_value=True, min=0.0, max=25.0, default=1.0)
TF_M1			= FloatTextureParameter('M1', 'M1',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_M2			= FloatTextureParameter('M2', 'M2',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_M3			= FloatTextureParameter('M3', 'M3',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_R1			= FloatTextureParameter('R1', 'R1',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_R2			= FloatTextureParameter('R2', 'R2',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_R3			= FloatTextureParameter('R3', 'R3',							add_float_value=True, default=1.0, min=0.0, max=0.0 )
TF_sigma		= FloatTextureParameter('sigma', 'Sigma',					add_float_value=True, min=0.0, max=100.0 )
TF_uroughness	= FloatTextureParameter('uroughness', 'uroughness',			add_float_value=True, min=0.00001, max=1.0, default=0.0002 )
TF_vroughness	= FloatTextureParameter('vroughness', 'vroughness',			add_float_value=True, min=0.00001, max=1.0, default=0.0002 )

# Color Textures
TC_Ka			= ColorTextureParameter('Ka', 'Absorption color',	default=(0.2,0.2,0.2) )
TC_Kd			= ColorTextureParameter('Kd', 'Diffuse color',		default=(0.64,0.64,0.64) )
TC_Kr			= ColorTextureParameter('Kr', 'Reflection color',	default=(1.0,1.0,1.0) )
TC_Ks			= ColorTextureParameter('Ks', 'Specular color',		default=(0.25,0.25,0.25) )
TC_Ks1			= ColorTextureParameter('Ks1', 'Specular color 1',	default=(1.0,1.0,1.0) )
TC_Ks2			= ColorTextureParameter('Ks2', 'Specular color 2',	default=(1.0,1.0,1.0) )
TC_Ks3			= ColorTextureParameter('Ks3', 'Specular color 3',	default=(1.0,1.0,1.0) )
TC_Kt			= ColorTextureParameter('Kt', 'Transmission color',	default=(1.0,1.0,1.0) )
TC_L			= ColorTextureParameter('L', 'Emission color',		default=(1.0,1.0,1.0) )

TC_absorption	= VolumeDataColorTextureParameter('absorption', 'Absorption')

def material_visibility():
	# non-texture properties
	vis = {
		'architectural':	{ 'material': has_property('', 'architectural') },
		'dispersion':		{ 'material': has_property('', 'dispersion') },
		'name':				{ 'material': has_property('', 'name') },
		'namedmaterial1':	{ 'material': has_property('', 'namedmaterial1') },
		'namedmaterial2':	{ 'material': has_property('', 'namedmaterial2') },
	}
	
	# Float Texture parameters
	vis.update( TF_amount.get_visibility() )
	vis.update( TF_bumpmap.get_visibility() )
	vis.update( TF_cauchyb.get_visibility() )
	vis.update( TF_d.get_visibility() )
	vis.update( TF_film.get_visibility() )
	vis.update( TF_filmindex.get_visibility() )
	vis.update( TF_index.get_visibility() )
	vis.update( TF_M1.get_visibility() )
	vis.update( TF_M2.get_visibility() )
	vis.update( TF_M3.get_visibility() )
	vis.update( TF_R1.get_visibility() )
	vis.update( TF_R2.get_visibility() )
	vis.update( TF_R3.get_visibility() )
	vis.update( TF_sigma.get_visibility() )
	vis.update( TF_uroughness.get_visibility() )
	vis.update( TF_vroughness.get_visibility() )
	
	# Color Texture parameters
	vis.update( TC_Ka.get_visibility() )
	vis.update( TC_Kd.get_visibility() )
	vis.update( TC_Kr.get_visibility() )
	vis.update( TC_Ks.get_visibility() )
	vis.update( TC_Ks1.get_visibility() )
	vis.update( TC_Ks2.get_visibility() )
	vis.update( TC_Ks3.get_visibility() )
	vis.update( TC_Kt.get_visibility() )
	
	# Add compositing options for distributedpath
	vis.update({
		'compositing_label':				{ 'integrator_type': 'distributedpath' },
		'compo_visible_material':			{ 'integrator_type': 'distributedpath' },
		'compo_visible_emission':			{ 'integrator_type': 'distributedpath' },
		'compo_visible_indirect_material':	{ 'integrator_type': 'distributedpath' },
		'compo_visible_indirect_emission':	{ 'integrator_type': 'distributedpath' },
		'compo_override_alpha':				{ 'integrator_type': 'distributedpath' },
		'compo_override_alpha_value':		{ 'integrator_type': 'distributedpath', 'compo_override_alpha': True },
		
		'Interior':							{ 'material': 'glass2' },
		'Exterior':							{ 'material': 'glass2' },
	})
	
	return vis

class luxrender_material(declarative_property_group):
	'''
	Storage class for LuxRender Material settings.
	This class will be instantiated within a Blender Material
	object.
	'''
	
	controls = [
		'type',
	]
	
	visibility = {}
	
	properties = [
		# Material Type Select
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'description': 'LuxRender material type',
			'default': 'matte',
			'items': [
				('carpaint', 'Car Paint', 'carpaint'),
				('glass', 'Glass', 'glass'),
				('glass2', 'Glass2', 'glass2'),
				('roughglass','Rough Glass','roughglass'),
				('glossy','Glossy','glossy'),
				('glossy_lossy','Glossy (Lossy)','glossy_lossy'),
				('matte','Matte','matte'),
				('mattetranslucent','Matte Translucent','mattetranslucent'),
				('metal','Metal','metal'),
				('shinymetal','Shiny Metal','shinymetal'),
				('mirror','Mirror','mirror'),
				('mix','Mix','mix'),
				('null','Null','null'),
			],
		},
	]

def carpaint_visibility():
	vis = {}
	
	vis.update( TF_bumpmap.get_visibility() )
	vis.update( TF_d.get_visibility() )
	vis.update( TC_Ka.get_visibility() )
	vis.update( TC_Kd.get_visibility() )
	vis.update( TC_Ks1.get_visibility() )
	vis.update( TC_Ks2.get_visibility() )
	vis.update( TC_Ks3.get_visibility() )
	vis.update( TF_M1.get_visibility() )
	vis.update( TF_M2.get_visibility() )
	vis.update( TF_M3.get_visibility() )
	vis.update( TF_R1.get_visibility() )
	vis.update( TF_R2.get_visibility() )
	vis.update( TF_R3.get_visibility() )
	
	vis2 = vis.copy()
	# only show Ka/Kd/Ks1/Ks2/Ks3/M1/M2/M3/R1/R2/R3 if name=='-'
	for k in vis.keys():
		for srch in ['Ka','Kd','Ks1','Ks2','Ks3']:
			vis2['%s_color'%srch] = { 'name': '-' }
			vis2['%s_usecolortexture'%srch] = { 'name': '-' }
			if k.startswith(srch):
				vis2[k]['name'] = '-'
		for srch in ['M1','M2','M3','R1','R2','R3']:
			vis2['%s_floatvalue'%srch] = { 'name': '-' }
			vis2['%s_usefloattexture'%srch] = { 'name': '-' }
			if k.startswith(srch):
				vis2[k]['name'] = '-'
	
	return vis2

class carpaint(declarative_property_group):
	
	controls = [
		'name'
	] + \
	TF_bumpmap.get_controls() + \
	TF_d.get_controls() + \
	TC_Ka.get_controls() + \
	TC_Kd.get_controls() + \
	TC_Ks1.get_controls() + \
	TC_Ks2.get_controls() + \
	TC_Ks3.get_controls() + \
	TF_M1.get_controls() + \
	TF_M2.get_controls() + \
	TF_M3.get_controls() + \
	TF_R1.get_controls() + \
	TF_R2.get_controls() + \
	TF_R3.get_controls()
	
	visibility = carpaint_visibility()
	
	properties = [
		{
			'type': 'enum',
			'attr': 'name',
			'name': 'Preset',
			'items': [
				('-', 'Manual settings', '-'),
				('white', 'white', 'white'),
			]
		},
	] + \
	TF_bumpmap.get_properties() + \
	TF_d.get_properties() + \
	TC_Ka.get_properties() + \
	TC_Kd.get_properties() + \
	TC_Ks1.get_properties() + \
	TC_Ks2.get_properties() + \
	TC_Ks3.get_properties() + \
	TF_M1.get_properties() + \
	TF_M2.get_properties() + \
	TF_M3.get_properties() + \
	TF_R1.get_properties() + \
	TF_R2.get_properties() + \
	TF_R3.get_properties()

class glass(declarative_property_group):
	
	controls = [
		'architectural',
	] + \
	TF_bumpmap.get_controls() + \
	TF_cauchyb.get_controls() + \
	TF_film.get_controls() + \
	TF_filmindex.get_controls() + \
	TF_index.get_controls() + \
	TC_Kr.get_controls() + \
	TC_Kt.get_controls()
	
	visibility = {
	}
	
	properties = [
		{
			'type': 'bool',
			'attr': 'architectural',
			'name': 'Architectural',
			'default': False
		},
	] + \
	TF_bumpmap.get_properties() + \
	TF_cauchyb.get_properties() + \
	TF_film.get_properties() + \
	TF_filmindex.get_properties() + \
	TF_index.get_properties() + \
	TC_Kr.get_properties() + \
	TC_Kt.get_properties()

class glass2(declarative_property_group):
	
	controls = [
		'architectural',
		'dispersion',
	] + \
	TF_bumpmap.get_controls()
	
	visibility = {
	}
	
	properties = [
		{
			'type': 'bool',
			'attr': 'architectural',
			'name': 'Architectural',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'dispersion',
			'name': 'Dispersion',
			'default': False
		},
	] + \
	TF_bumpmap.get_properties()

class roughglass(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TF_cauchyb.get_controls() + \
	TF_index.get_controls() + \
	TC_Kr.get_controls() + \
	TC_Kt.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TF_cauchyb.get_properties() + \
	TF_index.get_properties() + \
	TC_Kr.get_properties() + \
	TC_Kt.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties()

class glossy(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TF_d.get_controls() + \
	TF_index.get_controls() + \
	TC_Ka.get_controls() + \
	TC_Kd.get_controls() + \
	TC_Ks.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TF_d.get_properties() + \
	TF_index.get_properties() + \
	TC_Ka.get_properties() + \
	TC_Kd.get_properties() + \
	TC_Ks.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties()

class glossy_lossy(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TF_d.get_controls() + \
	TF_index.get_controls() + \
	TC_Ka.get_controls() + \
	TC_Kd.get_controls() + \
	TC_Ks.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TF_d.get_properties() + \
	TF_index.get_properties() + \
	TC_Ka.get_properties() + \
	TC_Kd.get_properties() + \
	TC_Ks.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties()

class matte(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TC_Kd.get_controls() + \
	TF_sigma.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TC_Kd.get_properties() + \
	TF_sigma.get_properties()

class mattetranslucent(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TC_Kr.get_controls() + \
	TC_Kt.get_controls() + \
	TF_sigma.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TC_Kr.get_properties() + \
	TC_Kt.get_properties() + \
	TF_sigma.get_properties()

class metal(declarative_property_group):
	
	controls = [
		'name',
		'filename',
	] + \
	TF_bumpmap.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls()
	
	visibility = {
		'filename':	{ 'name': 'nk' }
	}
	
	properties = [
		{
			'type': 'enum',
			'attr': 'name',
			'name': 'Preset',
			'items': [
				('nk', 'Use nk File', 'nk'),
				('amorphous carbon', 'amorphous carbon', 'amorphous carbon'),
				('copper', 'copper', 'copper'),
				('gold', 'gold', 'gold'),
				('silver', 'silver', 'silver'),
			]
		},
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'filename',
			'name': 'NK file',
		},
	] + \
	TF_bumpmap.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties()

class shinymetal(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TF_film.get_controls() + \
	TF_filmindex.get_controls() + \
	TC_Kr.get_controls() + \
	TC_Ks.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TF_film.get_properties() + \
	TF_filmindex.get_properties() + \
	TC_Kr.get_properties() + \
	TC_Ks.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties()

class mirror(declarative_property_group):
	
	controls = [
	] + \
	TF_bumpmap.get_controls() + \
	TF_film.get_controls() + \
	TF_filmindex.get_controls() + \
	TC_Kr.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_bumpmap.get_properties() + \
	TF_film.get_properties() + \
	TF_filmindex.get_properties() + \
	TC_Kr.get_properties()

class mix(declarative_property_group):
	
	controls = [
		'namedmaterial1',
		'namedmaterial2',
	] + \
	TF_amount.get_controls()
	
	visibility = {
	}
	
	properties = [
	] + \
	TF_amount.get_properties() + \
	MaterialParameter('namedmaterial1', 'Material 1', 'mix') + \
	MaterialParameter('namedmaterial2', 'Material 2', 'mix')

class null(declarative_property_group):
	
	controls = [
	]
	
	visibility = {
	}
	
	properties = [
	]

class old_mat(object):
	
	controls = [
		
		'name',
		
	] + \
	TC_Kd.get_controls() + \
	TF_sigma.get_controls() + \
	TC_Ka.get_controls() + \
	TC_Ks.get_controls() + \
	TF_d.get_controls() + \
	TF_uroughness.get_controls() + \
	TF_vroughness.get_controls() + \
	[
		# 'Glassy' options
		'architectural',
	] + \
	TF_index.get_controls() + \
	[
		'dispersion',
	] + \
	TF_cauchyb.get_controls() + \
	TC_Kr.get_controls() + \
	TC_Kt.get_controls() + \
	TF_film.get_controls() + \
	TF_filmindex.get_controls() + \
	TC_Ks1.get_controls() + \
	TC_Ks2.get_controls() + \
	TC_Ks3.get_controls() + \
	TF_M1.get_controls() + \
	TF_M2.get_controls() + \
	TF_M3.get_controls() + \
	TF_R1.get_controls() + \
	TF_R2.get_controls() + \
	TF_R3.get_controls() + \
	TF_bumpmap.get_controls() + \
	TF_amount.get_controls() + \
	[
		# Mix Material
		'namedmaterial1',
		'namedmaterial2',
		
		# Compositing options for distributedpath
		'compositing_label',
		['compo_visible_material',
		'compo_visible_emission'],
		['compo_visible_indirect_material',
		'compo_visible_indirect_emission'],
		'compo_override_alpha',
		'compo_override_alpha_value',
		
		# Glass 2 Volumes
		'Interior',
		'Exterior'
	]
	
	visibility = material_visibility()
	
	properties = [
		
	] + \
	TF_amount.get_properties() + \
	[
		{
			'type': 'bool',
			'attr': 'architectural',
			'name': 'Architectural',
			'default': False
		},
	] + \
	TF_bumpmap.get_properties() + \
	TF_cauchyb.get_properties() + \
	TF_d.get_properties() + \
	[
		{
			'type': 'bool',
			'attr': 'dispersion',
			'name': 'Dispersion',
			'default': False
		},
	] + \
	TF_film.get_properties() + \
	TF_filmindex.get_properties() + \
	TF_index.get_properties() + \
	TC_Ka.get_properties() + \
	TC_Kd.get_properties() + \
	TC_Kr.get_properties() + \
	TC_Ks.get_properties() + \
	TC_Ks1.get_properties() + \
	TC_Ks2.get_properties() + \
	TC_Ks3.get_properties() + \
	TC_Kt.get_properties() + \
	TF_M1.get_properties() + \
	TF_M2.get_properties() + \
	TF_M3.get_properties() + \
	[
		{
			'type': 'string',
			'attr': 'name',
			'name': 'Name'
		},
	] + \
	MaterialParameter('namedmaterial1', 'Material 1', 'luxrender_material') + \
	MaterialParameter('namedmaterial2', 'Material 2', 'luxrender_material') + \
	TF_R1.get_properties()+ \
	TF_R2.get_properties() + \
	TF_R3.get_properties() + \
	TF_sigma.get_properties() + \
	TF_uroughness.get_properties() + \
	TF_vroughness.get_properties() + \
	[
		# hidden parameter to hold current integrator type - updated on draw()
		{
			'type': 'string',
			'attr': 'integrator_type',
		},
		{
			'type': 'text',
			'attr': 'compositing_label',
			'name': 'Compositing options',
		},
		{
			'type': 'bool',
			'attr': 'compo_visible_material',
			'name': 'Visible Material',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'compo_visible_emission',
			'name': 'Visible Emission',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'compo_visible_indirect_material',
			'name': 'Visible Indirect Material',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'compo_visible_indirect_emission',
			'name': 'Visible Indirect Emission',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'compo_override_alpha',
			'name': 'Override Alpha',
			'default': False
		},
		{
			'type': 'float',
			'attr': 'compo_override_alpha_value',
			'name': 'Override Alpha Value',
			'default': 0.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1.0,
			'soft_max': 1.0,
		},
	] + \
	VolumeParameter('Interior', 'Interior', 'luxrender_material') + \
	VolumeParameter('Exterior', 'Exterior', 'luxrender_material')

class luxrender_emission(declarative_property_group):
	'''
	Storage class for LuxRender Material emission settings.
	This class will be instantiated within a Blender Material
	object.
	'''
	
	controls = [
		'use_emission',
		'lightgroup',
	] + \
	TC_L.get_controls() + \
	[
		'gain',
		'power',
		'efficacy',
	]
	
	visibility = {
		'lightgroup': 			{ 'use_emission': True },
		'L_colorlabel': 		{ 'use_emission': True },
		'L_color': 				{ 'use_emission': True },
		'L_usecolorrgc':		{ 'use_emission': True },
		'L_usecolortexture':	{ 'use_emission': True },
		'L_colortexture':		{ 'use_emission': True, 'L_usecolortexture': True },
		'gain': 				{ 'use_emission': True },
		'power': 				{ 'use_emission': True },
		'efficacy': 			{ 'use_emission': True },
	}
	
	properties = [
		{
			'type': 'bool',
			'attr': 'use_emission',
			'name': 'Use Emission',
			'default': False
		},
		{
			'type': 'string',
			'attr': 'lightgroup',
			'name': 'Light Group',
			'default': 'default',
		},
		{
			'type': 'float',
			'attr': 'gain',
			'name': 'Gain',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1e8,
			'soft_max': 1e8
		},
		{
			'type': 'float',
			'attr': 'power',
			'name': 'Power',
			'default': 100.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1e5,
			'soft_max': 1e5
		},
		{
			'type': 'float',
			'attr': 'efficacy',
			'name': 'Efficacy',
			'default': 17.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1e4,
			'soft_max': 1e4
		},
	] + \
	TC_L.get_properties()

class luxrender_volume_data(declarative_property_group):
	'''
	Storage class for LuxRender volume data. The
	luxrender_volumes object will store 1 or more of
	these in its CollectionProperty 'volumes'.
	'''
	
	controls = [
		'type',
	] + \
	TFR_IOR.get_controls() + \
	TC_absorption.get_controls() + \
	[
		'depth'
	]
	
	visibility = {
		'ior_floattexture':			{ 'ior_usefloattexture': True },
		'absorption_colortexture':	{ 'absorption_usecolortexture': True }
	}
	
	properties = [
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'items': [
				('clear', 'clear', 'clear')
			]
		},
	] + \
	TFR_IOR.get_properties() + \
	TC_absorption.get_properties() + \
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
			'precision': 6
		},
	]
	
	def api_output(self, lux_context):
		vp = ParamSet()
		
		scale = 1
		def absorption_transform(i):
			# This is copied from the old LuxBlend, I don't pretend to understand it, DH
			depthed = (-math.log(max([(float(i)),1e-30]))/(self.depth*scale)) * ((float(i))==1.0 and -1 or 1)
			#print('abs xform: %f -> %f' % (i,depthed))
			return depthed
		
		vp.update( add_texture_parameter(lux_context, 'fresnel', 'fresnel', self) )
		vp.update( add_texture_parameter(lux_context, 'absorption', 'color', self, value_transform=absorption_transform) )
		
		return self.type, vp

class luxrender_volumes(declarative_property_group):
	'''
	Storage class for LuxRender Material volumes.
	This class will be instantiated within a Blender scene
	object.
	'''
	
	controls = [
		'volumes_label',
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
			'items': [
				
			]
		},
		{
			'type': 'text',
			'attr': 'volumes_label',
			'name': 'Volumes',
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
			'icon': 'PLUS',
		},
		{
			'type': 'operator',
			'attr': 'op_vol_rem',
			'operator': 'luxrender.volume_remove',
			'text': 'Remove',
			'icon': 'X',
		},
	]


