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

from properties_data_camera import DataButtonsPanel

# EF API
from ef.ui import described_layout
from ef.ef import ef

import luxrender.properties.camera
from ..module import LuxManager as LM

class camera_panel(DataButtonsPanel, described_layout):
	COMPAT_ENGINES = {'luxrender'}
	
	# prevent creating luxrender_camera property group in Scene
	property_group_non_global = True
	
	@classmethod
	def property_reload(cls):
		for cam in bpy.data.cameras:
			cls.property_create(cam)
	
	@classmethod
	def property_create(cls, cam):
		if not hasattr(cam, cls.property_group.__name__):
			ef.init_properties(cam, [{
				'type': 'pointer',
				'attr': cls.property_group.__name__,
				'ptype': cls.property_group,
				'name': cls.property_group.__name__,
				'description': cls.property_group.__name__
			}], cache=False)
			ef.init_properties(cls.property_group, cls.properties, cache=False)
	
	# Overridden to provide data storage in the camera, not the scene
	def draw(self, context):
		if context.camera is not None:
			self.property_create(context.camera)
			
			# Show only certain controls for Blender's perspective camera type 
			context.camera.luxrender_camera.is_perspective = (context.camera.type == 'PERSP')
			
			for p in self.controls:
				self.draw_column(p, self.layout, context.camera, supercontext=context)

class camera(camera_panel, bpy.types.Panel):
	bl_label = 'LuxRender Camera'
	
	property_group = luxrender.properties.camera.luxrender_camera
	
	controls = [
		['autofocus', 'use_dof', 'use_clipping'],
		'type',
		'fstop',
		'sensitivity',
		'exposure',
		'usemblur',
		'shutterdistribution', 
		['cammblur', 'objectmblur'], 
	]
	
	visibility = {
		'type':						{ 'is_perspective': True }, 
		'shutterdistribution':		{ 'usemblur': True },
		'cammblur':					{ 'usemblur': True },
		'objectmblur':				{ 'usemblur': True },
	}
	
	properties = [
		# hidden property set via draw() method
		{
			'type': 'bool',
			'attr': 'is_perspective',
			'name': 'is_perspective',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'use_clipping',
			'name': 'Clipping',
			'description': 'Use near/far geometry clipping',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'use_dof',
			'name': 'DOF',
			'description': 'Use DOF effect',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'autofocus',
			'name': 'Auto focus',
			'description': 'Use auto focus',
			'default': True,
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Camera type',
			'description': 'Choose camera type',
			'default': 'perspective',
			'items': [
				('perspective', 'Perspective', 'perspective'),
				('environment', 'Environment', 'environment'),
				#('realistic', 'Realistic', 'realistic'),
			]
		},
		{
			'type': 'float',
			'attr': 'fstop',
			'name': 'f/Stop',
			'description': 'f/Stop',
			'default': 2.8,
			'min': 0.4,
			'soft_min': 0.4,
			'max': 128.0,
			'soft_max': 128.0
		},
		{
			'type': 'float',
			'attr': 'sensitivity',
			'name': 'ISO',
			'description': 'Sensitivity (ISO)',
			'default': 320.0,
			'min': 10.0,
			'soft_min': 10.0,
			'max': 6400.0,
			'soft_max': 6400.0
		},
		{
			'type': 'float',
			'attr': 'exposure',
			'name': 'Exposure',
			'description': 'Exposure time (secs)',
			'precision': 6,
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 25.0,
			'soft_max': 25.0
		},
		{
			'type': 'bool',
			'attr': 'usemblur',
			'name': 'Motion Blur',
			'default': False
		},
		{
			'type': 'enum',
			'attr': 'shutterdistribution',
			'name': 'Distribution',
			'default': 'uniform',
			'items': [
				('uniform', 'Uniform', 'uniform'),
				('gaussian', 'Gaussian', 'gaussian'),
			]
		},
		{
			'type': 'bool',
			'attr': 'cammblur',
			'name': 'Camera Motion Blur',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'objectmblur',
			'name': 'Object Motion Blur',
			'default': True
		},	
	]

class colorspace(camera_panel, bpy.types.Panel):
	bl_label = 'LuxRender Colour Space'
	
	property_group = luxrender.properties.camera.luxrender_colorspace
	
	controls = [
		'gamma',
		
		[0.1, 'preset', 'preset_name'],
		['cs_whiteX', 'cs_whiteY'],
		['cs_redX', 'cs_redY'],
		['cs_greenX', 'cs_greenY'],
		['cs_blueX', 'cs_blueY'],
	]
	
	visibility = {
		'preset_name':				{ 'preset': True },
		'cs_whiteX':				{ 'preset': False },
		'cs_whiteY':				{ 'preset': False },
		'cs_redX':					{ 'preset': False },
		'cs_redY':					{ 'preset': False },
		'cs_greenX':				{ 'preset': False },
		'cs_greenY':				{ 'preset': False },
		'cs_blueX':					{ 'preset': False },
		'cs_blueY':					{ 'preset': False },
	}
	
	properties = [
		{
			'attr': 'gamma',
			'type': 'float',
			'name': 'Gamma',
			'default': 2.2
		},
		{
			'attr': 'preset',
			'type': 'bool',
			'name': 'P',
			'default': True,
			'toggle': True
		},
		# TODO - change actual parameter values when user chooses a preset
		{
			'attr': 'preset_name',
			'type': 'enum',
			'name': 'Preset',
			'default': 'sRGB',
			'items': [
				('sRGB', 'sRGB - HDTV (ITU-R BT.709-5)', 'sRGB'),
				('romm_rgb', 'ROMM RGB', 'romm_rgb'),
				('adobe_rgb_98', 'Adobe RGB 98', 'adobe_rgb_98'),
				('apple_rgb', 'Apple RGB', 'apple_rgb'),
				('ntsc_1953', 'NTSC (FCC 1953, ITU-R BT.470-2 System M)', 'ntsc_1953'),
				('ntsc_1979', 'NTSC (1979) (SMPTE C, SMPTE-RP 145)', 'ntsc_1979'),
				('pal_secam', 'PAL/SECAM (EBU 3213, ITU-R BT.470-6)', 'pal_secam'),
				('cie_e', 'CIE (1931) E', 'cie_e'),
			]
		},
		{
			'attr': 'cs_whiteX',
			'type': 'float',
			'name': 'White X',
			'precision': 6,
			'default': 0.314275
		},
		{
			'attr': 'cs_whiteY',
			'type': 'float',
			'name': 'White Y',
			'precision': 6,
			'default': 0.329411
		},
		
		{
			'attr': 'cs_redX',
			'type': 'float',
			'name': 'Red X',
			'precision': 6,
			'default': 0.63
		},
		{
			'attr': 'cs_redY',
			'type': 'float',
			'name': 'Red Y',
			'precision': 6,
			'default': 0.34
		},
		
		{
			'attr': 'cs_greenX',
			'type': 'float',
			'name': 'Green X',
			'precision': 6,
			'default': 0.31
		},
		{
			'attr': 'cs_greenY',
			'type': 'float',
			'name': 'Green Y',
			'precision': 6,
			'default': 0.595
		},
		
		{
			'attr': 'cs_blueX',
			'type': 'float',
			'name': 'Blue X',
			'precision': 6,
			'default': 0.155
		},
		{
			'attr': 'cs_blueY',
			'type': 'float',
			'name': 'Blue Y',
			'precision': 6,
			'default': 0.07
		},
	]

class tonemapping_live_update(object):
	prop_lookup = {
		#'type':				 'LUX_FILM_TM_TONEMAPKERNEL',
		'reinhard_prescale':	'LUX_FILM_TM_REINHARD_PRESCALE',
		'reinhard_postscale':	'LUX_FILM_TM_REINHARD_POSTSCALE',
		'reinhard_burn':		'LUX_FILM_TM_REINHARD_BURN',
	}
	prop_vals = {}
	@staticmethod
	def update(context, scene, property):
		if LM.ActiveManager is not None and LM.ActiveManager.started:
			prop_val = getattr(scene.camera.data.luxrender_tonemapping, property)
			if property not in tonemapping_live_update.prop_vals.keys():
				tonemapping_live_update.prop_vals[property] = prop_val
			
			if tonemapping_live_update.prop_vals[property] != prop_val:
				tonemapping_live_update.prop_vals[property] = prop_val
				c = LM.ActiveManager.lux_context
				c.setParameterValue(
					c.PYLUX.luxComponent.LUX_FILM,
					getattr(c.PYLUX.luxComponentParameters, tonemapping_live_update.prop_lookup[property]),
					prop_val,
					0
				)

class tonemapping(camera_panel, bpy.types.Panel):
	bl_label = 'LuxRender ToneMapping'
	
	property_group = luxrender.properties.camera.luxrender_tonemapping
	
	controls = [
		'type',
		
		# Reinhard
		['reinhard_prescale', 'reinhard_postscale', 'reinhard_burn'],
		
		# Linear
		'linear_gamma',
		
		# Contrast
		'ywa',
	]
	
	visibility = {
		# Reinhard
		'reinhard_prescale':			{ 'type': 'reinhard' },
		'reinhard_postscale':			{ 'type': 'reinhard' },
		'reinhard_burn':				{ 'type': 'reinhard' },
		
		# Linear
		'linear_gamma':					{ 'type': 'linear' },
		
		# Contrast
		'ywa':							{ 'type': 'contrast' },
	}
	
	properties = [
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Tonemapper',
			'description': 'Choose tonemapping type',
			'default': 'reinhard',
			'items': [
				('reinhard', 'Reinhard', 'reinhard'),
				('linear', 'Linear', 'linear'),
				('contrast', 'Contrast', 'contrast'),
				('maxwhite', 'Maxwhite', 'maxwhite')
			],
			#'draw': lambda context, scene: tonemapping_live_update.update(context, scene, 'type')
		},
		
		# Reinhard
		{
			'type': 'float',
			'attr': 'reinhard_prescale',
			'name': 'Pre',
			'description': 'Reinhard Pre-Scale factor',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 25.0,
			'soft_max': 25.0,
			# 'draw': lambda context, scene: tonemapping_live_update.update(context, scene, 'reinhard_prescale') 
		},
		{
			'type': 'float',
			'attr': 'reinhard_postscale',
			'name': 'Post',
			'description': 'Reinhard Post-Scale factor',
			'default': 1.2,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 25.0,
			'soft_max': 25.0,
			# 'draw': lambda context, scene: tonemapping_live_update.update(context, scene, 'reinhard_postscale')
		},
		{
			'type': 'float',
			'attr': 'reinhard_burn',
			'name': 'Burn',
			'description': 'Reinhard Burn factor',
			'default': 6.0,
			'min': 0.01,
			'soft_min': 0.01,
			'max': 25.0,
			'soft_max': 25.0,
			# 'draw': lambda context, scene: tonemapping_live_update.update(context, scene, 'reinhard_burn')
		},
		
		#Linear
		{
			'type': 'float',
			'attr': 'linear_gamma',
			'name': 'Gamma',
			'description': 'Linear gamma',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 5.0,
			'soft_max': 5.0
		},
		
		#Contrast
		{
			'type': 'float',
			'attr': 'ywa',
			'name': 'Ywa',
			'description': 'World adaption luminance',
			'default': 0.1,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 2e5,
			'soft_max': 2e5
		}
	]

