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
import os

import bpy

from extensions_framework import util as efutil
from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_OR as O, Logic_AND as A

from .. import LuxRenderAddon
from ..export import get_worldscale, get_output_filename
from ..export import ParamSet, LuxManager
from ..export import fix_matrix_order
from ..outputs.pure_api import LUXRENDER_VERSION

def CameraVolumeParameter(attr, name):
	return [
		{
			'attr': '%s_volume' % attr,
			'type': 'string',
			'name': '%s_volume' % attr,
			'description': '%s volume; leave blank to use World default' % attr,
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': attr,
			'src': lambda s,c: s.scene.luxrender_volumes,
			'src_attr': 'volumes',
			'trg': lambda s,c: c.luxrender_camera,
			'trg_attr': '%s_volume' % attr,
			'name': name
		},
	]

@LuxRenderAddon.addon_register_class
class luxrender_camera(declarative_property_group):
	'''
	Storage class for LuxRender Camera settings.
	'''
	
	ef_attach_to = ['Camera']
	
	controls = [		
		'Exterior',
		'fstop',
		'sensitivity',
		'exposure_mode',
		'exposure_start', 'exposure_end_norm', 'exposure_end_abs',
		['exposure_degrees_start', 'exposure_degrees_end'],
		'usemblur',
		'motion_blur_samples',
		'shutterdistribution', 
		['cammblur', 'objectmblur'],
		[0.3, 'use_dof','autofocus',  'use_clipping'],
		'blades',
		['distribution', 'power'],
	]
	
	visibility = {
		'autofocus':				{ 'use_dof': True },
		'blades':					{ 'use_dof': True },
		'distribution':				{ 'use_dof': True },
		'power':					{ 'use_dof': True },
		'exposure_start':			{ 'exposure_mode': O(['normalised','absolute']) },
		'exposure_end_norm':		{ 'exposure_mode': 'normalised' },
		'exposure_end_abs':			{ 'exposure_mode': 'absolute' },
		'exposure_degrees_start':	{ 'exposure_mode': 'degrees' },
		'exposure_degrees_end':		{ 'exposure_mode': 'degrees' },
		'shutterdistribution':		{ 'usemblur': True },
		'motion_blur_samples':		{ 'usemblur': True },
		'cammblur':					{ 'usemblur': True },
		'objectmblur':				{ 'usemblur': True },
	}
	
	properties = CameraVolumeParameter('Exterior', 'Exterior') + [
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
			'description': 'Use depth of field',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'autofocus',
			'name': 'Auto focus',
			'description': 'Auto-focus for depth of field, DOF target object will be ignored',
			'default': True,
		},
		{
			'type': 'int',
			'attr': 'blades',
			'name': 'Blades',
			'description': 'Number of aperture blades. Use 2 or lower for circular aperture',
			'min': 0,
			'default': 0,
		},
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Distribution',
			'description': 'This value controls the lens sampling distribution. Non-uniform distributions allow for ring effects',
			'default': 'uniform',
			'items': [
				('uniform', 'Uniform', 'Uniform'),
				('exponential', 'Exponential', 'Exponential'),
				('inverse exponential', 'Inverse Exponential', 'Inverse Exponential'),
				('gaussian', 'Gaussian', 'Gaussian'),
				('inverse gaussian', 'Inverse Gaussian', 'Inverse Gaussian'),
				]
		},
		{
			'type': 'int',
			'attr': 'power',
			'name': 'Power',
			'description': 'Exponent for lens samping distribution. Higher values give more pronounced ring-effects',
			'min': 0,
			'default': 0,
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
			'soft_max': 128.0,
			'step': 100
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
			'soft_max': 6400.0,
			'step': 1000
		},
		{
			'type': 'enum',
			'attr': 'exposure_mode',
			'name': 'Exposure timing',
			'items': [
				('normalised', 'Normalised', 'normalised'),
				('absolute', 'Absolute', 'absolute'),
				('degrees', 'Degrees', 'degrees'),
			],
			'default': 'normalised'
		},
		{
			'type': 'int',
			'attr': 'motion_blur_samples',
			'name': 'Shutter Steps',
			'description': 'Shutter Steps',
			'default': 1,
			'min': 1,
			'soft_min': 1,
			'max': 100,
			'soft_max': 100
		},
		{
			'type': 'float',
			'attr': 'exposure_start',
			'name': 'Open',
			'description': 'Shutter open time',
			'precision': 6,
			'default': 0.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1.0,
			'soft_max': 1.0
		},
		{
			'type': 'float',
			'attr': 'exposure_end_norm',
			'name': 'Close',
			'description': 'Shutter close time',
			'precision': 6,
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 1.0,
			'soft_max': 1.0
		},
		{
			'type': 'float',
			'attr': 'exposure_end_abs',
			'name': 'Close',
			'description': 'Shutter close time',
			'precision': 6,
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 120.0,
			'soft_max': 120.0
		},
		{
			'type': 'float',
			'attr': 'exposure_degrees_start',
			'name': 'Open angle',
			'description': 'Shutter open angle',
			'precision': 1,
			'default': 0.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 360.0,
			'soft_max': 360.0
		},
		{
			'type': 'float',
			'attr': 'exposure_degrees_end',
			'name': 'Close angle',
			'description': 'Shutter close angle',
			'precision': 1,
			'default': 360.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 360.0,
			'soft_max': 360.0
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
	
	def lookAt(self, camera):
		'''
		Derive a list describing 3 points for a LuxRender LookAt statement
		
		Returns		tuple(9) (floats)
		'''
		matrix = camera.matrix_world.copy()
		ws = get_worldscale()
		matrix *= ws
		ws = get_worldscale(as_scalematrix=False)
		matrix = fix_matrix_order(matrix) # matrix indexing hack
		matrix[0][3] *= ws
		matrix[1][3] *= ws
		matrix[2][3] *= ws
		# transpose to extract columns
		# TODO - update to matrix.col when available
		matrix = matrix.transposed() 
		pos = matrix[3]
		forwards = -matrix[2]
		target = (pos + forwards)
		up = matrix[1]
		return pos[:3] + target[:3] + up[:3]
	
	def screenwindow(self, xr, yr, scene, cam):
		'''
		xr			float
		yr			float
		cam		   bpy.types.camera
		
		Calculate LuxRender camera's screenwindow parameter
		
		Returns list[4]
		'''
		
		shiftX = cam.shift_x
		shiftY = cam.shift_y
		
		if cam.type == 'ORTHO':
			scale = cam.ortho_scale / 2.0
		else:
			scale = 1.0
		
		aspect = xr/yr
		invaspect = 1.0/aspect
		
		if aspect > 1.0:
			sw = [
				((2*shiftX)-1) * scale,
				((2*shiftX)+1) * scale,
				((2*shiftY)-invaspect) * scale,
				((2*shiftY)+invaspect) * scale
			]
		else:
			sw = [
				((2*shiftX)-aspect) * scale,
				((2*shiftX)+aspect) * scale,
				((2*shiftY)-1) * scale,
				((2*shiftY)+1) * scale
				]
		
		if scene.render.use_border:
			(x1,x2,y1,y2) = [
				scene.render.border_min_x, scene.render.border_max_x,
				scene.render.border_min_y, scene.render.border_max_y
			]
			sw = [
				sw[0]*(1-x1)+sw[1]*x1,
				sw[0]*(1-x2)+sw[1]*x2,
				sw[2]*(1-y1)+sw[3]*y1,
				sw[2]*(1-y2)+sw[3]*y2
			]
		
		return sw
	
	def exposure_time(self):
		"""
		Calculate the camera exposure time in seconds
		"""
		fps = LuxManager.CurrentScene.render.fps
		
		time = 1.0
		if self.exposure_mode == 'normalised':
			time = (self.exposure_end_norm - self.exposure_start) / fps
		if self.exposure_mode == 'absolute':
			time = (self.exposure_end_abs - self.exposure_start)
		if self.exposure_mode == 'degrees':
			time = (self.exposure_degrees_end - self.exposure_degrees_start) / (fps * 360.0)
		
		return time
	
	def api_output(self, scene, is_cam_animated):
		'''
		scene			bpy.types.scene
		
		Format this class's members into a LuxRender ParamSet
		
		Returns tuple
		'''
		
		cam = scene.camera.data
		xr, yr = self.luxrender_film.resolution(scene)
		
		params = ParamSet()
		
		if cam.type == 'PERSP' and self.type == 'perspective':
			params.add_float('fov', math.degrees(scene.camera.data.angle))
		
		params.add_float('screenwindow', self.screenwindow(xr, yr, scene, cam))
		params.add_bool('autofocus', False)
		
		fps = scene.render.fps
		if self.exposure_mode == 'normalised':
			params.add_float('shutteropen', self.exposure_start / fps)
			params.add_float('shutterclose', self.exposure_end_norm / fps)
		if self.exposure_mode == 'absolute':
			params.add_float('shutteropen', self.exposure_start)
			params.add_float('shutterclose', self.exposure_end_abs)
		if self.exposure_mode == 'degrees':
			params.add_float('shutteropen', self.exposure_degrees_start / (fps*360.0))
			params.add_float('shutterclose', self.exposure_degrees_end / (fps*360.0))
		
		if self.use_dof:
			# Do not world-scale this, it is already in meters !
			params.add_float('lensradius', (cam.lens / 1000.0) / ( 2.0 * self.fstop ))
		
			#Write apperture params
			params.add_integer('blades', self.blades)
			params.add_integer('power', self.power)
			params.add_string('distribution', self.distribution)
		
		ws = get_worldscale(as_scalematrix=False)
		
		if self.autofocus:
			params.add_bool('autofocus', True)
		else:
			if cam.dof_object is not None:
				params.add_float('focaldistance', ws*((scene.camera.location - cam.dof_object.location).length))
			elif cam.dof_distance > 0:
				params.add_float('focaldistance', ws*cam.dof_distance)
			
		if self.use_clipping:
			params.add_float('hither', ws*cam.clip_start)
			params.add_float('yon', ws*cam.clip_end)
		
		if self.usemblur:
			# update the camera settings with motion blur settings
			params.add_string('shutterdistribution', self.shutterdistribution)
		
			if self.cammblur and is_cam_animated:
				params.add_string('endtransform', 'CameraEndTransform')
		
		cam_type = 'orthographic' if cam.type == 'ORTHO' else 'environment' if cam.type == 'PANO' else 'perspective'
		return cam_type, params

@LuxRenderAddon.addon_register_class
class luxrender_film(declarative_property_group):
	
	ef_attach_to = ['luxrender_camera']
	
	controls = [
		'lbl_internal',
		'internal_updateinterval',
		'integratedimaging',
		
		'lbl_external',
		'writeinterval',
		'flmwriteinterval',
		'displayinterval',
		
		'lbl_outputs',
		['write_png', 'write_png_16bit'],
		'write_tga',
		['write_exr', 'write_exr_applyimaging', 'write_exr_halftype'],
		'write_exr_compressiontype',
		'write_zbuf',
		'zbuf_normalization',
		['output_alpha', 'premultiply_alpha'],
		['write_flm', 'restart_flm', 'write_flm_direct'],
		
		'ldr_clamp_method',
		'outlierrejection_k',
		'tilecount'
	]
	
	visibility = {
		'restart_flm': { 'write_flm': True },
		'premultiply_alpha': { 'output_alpha': True },
		'write_flm_direct': { 'write_flm': True },
		'write_png_16bit': { 'write_png': True },
		'write_exr_applyimaging': { 'write_exr': True },
		'write_exr_halftype': { 'write_exr': True },
		'write_exr_compressiontype': { 'write_exr': True },
		'write_zbuf': O([{'write_exr': True }, { 'write_tga': True }]),
		'zbuf_normalization': A([{'write_zbuf': True}, O([{'write_exr': True }, { 'write_tga': True }])]),
	}
	
	properties = [
		{
			'type': 'text',
			'attr': 'lbl_internal',
			'name': 'Internal rendering'
		},
		{
			'type': 'int',
			'attr': 'internal_updateinterval',
			'name': 'Update interval',
			'description': 'Period for updating render image (seconds)',
			'default': 10,
			'min': 2,
			'soft_min': 2,
			'save_in_preset': True
		},
		{
			'type': 'text',
			'attr': 'lbl_external',
			'name': 'External rendering'
		},
		{
			'type': 'int',
			'attr': 'writeinterval',
			'name': 'Write interval',
			'description': 'Period for writing images to disk (seconds)',
			'default': 180,
			'min': 2,
			'soft_min': 2,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'flmwriteinterval',
			'name': 'Flm write interval',
			'description': 'Period for writing flm files to disk (seconds)',
			'default': 900,
			'min': 2,
			'soft_min': 2,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'displayinterval',
			'name': 'Refresh interval',
			'description': 'Period for updating rendering on screen (seconds)',
			'default': 10,
			'min': 2,
			'soft_min': 2,
			'save_in_preset': True
		},
		{
			'type': 'text',
			'attr': 'lbl_outputs',
			'name': 'Output formats'
		},
		{
			'type': 'bool',
			'attr': 'integratedimaging',
			'name': 'Integrated imaging workflow',
			'description': 'Transfer rendered image directly to Blender without saving to disk (adds Alpha and Z-buffer support)',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'write_png',
			'name': 'PNG',
			'description': 'Enable PNG output',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'write_png_16bit',
			'name': 'Use 16bit PNG',
			'description': 'Use 16bit per channel PNG instead of 8bit',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'write_exr',
			'name': 'OpenEXR',
			'description': 'Enable OpenEXR ouput',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'write_exr_halftype',
			'name': 'Use 16bit EXR',
			'description': 'Use "half" (16bit float) OpenEXR format instead of 32bit float',
			'default': True
		},
		{
			'type': 'enum',
			'attr': 'write_exr_compressiontype',
			'name': 'EXR Compression',
			'description': 'Compression format for OpenEXR output',
			'items': [
				('RLE (lossless)', 'RLE (lossless)', 'RLE (lossless)'),
				('PIZ (lossless)', 'PIZ (lossless)', 'PIZ (lossless)'),
				('ZIP (lossless)', 'ZIP (lossless)', 'ZIP (lossless)'),
				('Pxr24 (lossy)', 'Pxr24 (lossy)', 'Pxr24 (lossy)'),
				('None', 'None', 'None'),
			],
			'default': 'PIZ (lossless)'
		},
		{
			'type': 'bool',
			'attr': 'write_tga',
			'name': 'TARGA',
			'description': 'Enable TARGA ouput',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'write_flm',
			'name': 'Write FLM',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'restart_flm',
			'name': 'Restart FLM',
			'description': 'Restart render from the beginning even if an FLM is available',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'write_flm_direct',
			'name': 'Write FLM Directly',
			'description': 'Write FLM directly to disk instead of trying to build it in RAM first. Slower, but uses less memory',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'output_alpha',
			'name': 'Enable alpha channel',
			'description': 'Enable alpha channel. This applies to all image formats',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'premultiply_alpha',
			'name': 'Premultiply Alpha',
			'description': 'Premultiply alpha channel (happens during film stage, not image output)',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'write_exr_applyimaging',
			'name': 'Tonemap EXR',
			'description': 'Apply imaging pipeline to OpenEXR output. Gamma correction will be skipped regardless',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'write_zbuf',
			'name': 'Enable Z-Buffer',
			'description': 'Include Z-buffer in OpenEXR and TARGA output',
			'default': False
		},
		{
			'type': 'enum',
			'attr': 'zbuf_normalization',
			'name': 'Z-Buffer Normalization',
			'description': 'Where to get normalization info for Z-buffer',
			'items': [
				('Camera Start/End clip', 'Camera start/end clip', 'Use Camera clipping range'),
				('Min/Max', 'Min/max', 'Min/max'),
				('None', 'None', 'None'),
			],
			'default': 'None'
		},
		{
			'type': 'int',
			'attr': 'outlierrejection_k',
			'name': 'Firefly rejection',
			'description': 'Firefly (outlier) rejection k parameter. 0=disabled',
			'default': 0,
			'min': 0,
			'soft_min': 0,
		},
		{
			'type': 'int',
			'attr': 'tilecount',
			'name': 'Tiles',
			'description': 'Number of film buffer tiles to use. 0=auto-detect',
			'default': 0,
			'min': 0,
			'soft_min': 0,
		},
		{
			'type': 'enum',
			'attr': 'ldr_clamp_method',
			'name': 'LDR Clamp method',
			'description': 'Method used to clamp bright areas into LDR range',
			'items': [
				('lum', 'Luminosity', 'Preserve luminosity'),
				('hue', 'Hue', 'Preserve hue'),
				('cut', 'Cut', 'Clip channels individually')
			],
			'default': 'cut'
		},
	]
	
	def resolution(self, scene):
		'''
		Calculate the output render resolution
		
		Returns		tuple(2) (floats)
		'''
		
		xr = scene.render.resolution_x * scene.render.resolution_percentage / 100.0
		yr = scene.render.resolution_y * scene.render.resolution_percentage / 100.0
		
		xr = round(xr)
		yr = round(yr)
		
		return xr, yr
	
	def get_gamma(self):
		if self.luxrender_colorspace.preset:
			return getattr(colorspace_presets, self.luxrender_colorspace.preset_name).gamma
		else:
			return self.luxrender_colorspace.gamma
	
	def api_output(self):
		'''
		Calculate type and parameters for LuxRender Film statement
		
		Returns		tuple(2) (string, list) 
		'''
		scene = LuxManager.CurrentScene
		
		xr, yr = self.resolution(scene)
		
		params = ParamSet()
		
		if scene.render.use_border:
			(x1,x2,y1,y2) = [
				scene.render.border_min_x, scene.render.border_max_x,
				scene.render.border_min_y, scene.render.border_max_y
			]
			# Set resolution
			params.add_integer('xresolution', round(xr*x2, 0)-round(xr*x1, 0))
			params.add_integer('yresolution', round(yr*y2, 0)-round(yr*y1, 0))
		else:
			# Set resolution
			params.add_integer('xresolution', xr)
			params.add_integer('yresolution', yr)
		
#		if scene.render.use_border:
#			cropwindow = [
#				scene.render.border_min_x, scene.render.border_max_x,
#				scene.render.border_min_y, scene.render.border_max_y
#			]
#			params.add_float('cropwindow', cropwindow)
		
		# ColourSpace
		if self.luxrender_colorspace.preset:
			cs_object = getattr(colorspace_presets, self.luxrender_colorspace.preset_name)
		else:
			cs_object = self.luxrender_colorspace
			
		params.add_float('gamma', self.get_gamma())
		params.add_float('colorspace_white',	[cs_object.cs_whiteX,	cs_object.cs_whiteY])
		params.add_float('colorspace_red',		[cs_object.cs_redX,		cs_object.cs_redY])
		params.add_float('colorspace_green',	[cs_object.cs_greenX,	cs_object.cs_greenY])
		params.add_float('colorspace_blue',		[cs_object.cs_blueX,	cs_object.cs_blueY])
		
		# Camera Response Function
		if LUXRENDER_VERSION >= '0.8' and self.luxrender_colorspace.use_crf == 'file':
			if scene.camera.library is not None:
				local_crf_filepath = bpy.path.abspath(self.luxrender_colorspace.crf_file, scene.camera.library.filepath)
			else:
				local_crf_filepath = self.luxrender_colorspace.crf_file
			local_crf_filepath = efutil.filesystem_path( local_crf_filepath )
			if scene.luxrender_engine.allow_file_embed():
				from ..util import bencode_file2string
				params.add_string('cameraresponse', os.path.basename(local_crf_filepath))
				encoded_data = bencode_file2string(local_crf_filepath)
				params.add_string('cameraresponse_data', encoded_data.splitlines() )
			else:
				params.add_string('cameraresponse', local_crf_filepath)
		if LUXRENDER_VERSION >= '0.8' and self.luxrender_colorspace.use_crf == 'preset':
			params.add_string('cameraresponse', self.luxrender_colorspace.crf_preset)
		
		# Output types
		params.add_string('filename', get_output_filename(scene))
		params.add_bool('write_resume_flm', self.write_flm)
		params.add_bool('restart_resume_flm', self.restart_flm)
		params.add_bool('write_flm_direct', self.write_flm_direct)
		
		if self.output_alpha:
			output_channels = 'RGBA'
			params.add_bool('premultiplyalpha', self.premultiply_alpha)
		else:
			output_channels = 'RGB'
								
		if scene.luxrender_engine.export_type == 'INT' and self.integratedimaging:
			# Set up params to enable z buffer and set gamma=1.0
			# Also, this requires tonemapped EXR output
			params.add_string('write_exr_channels', 'RGBA')
			params.add_bool('write_exr_halftype', False)
			params.add_bool('write_exr_applyimaging', True)
			params.add_bool('premultiplyalpha', True) #Apparently, this should always be true with EXR
			params.add_bool('write_exr_ZBuf', True)
			params.add_string('write_exr_zbuf_normalizationtype', 'Camera Start/End clip')
			if scene.render.use_color_management:
				params.add_float('gamma', 1.0) # Linear workflow !
			# else leave as pre-corrected gamma
		else:
			# Otherwise let the user decide on tonemapped EXR and other EXR settings
			params.add_bool('write_exr_halftype', self.write_exr_halftype)
			params.add_bool('write_exr_applyimaging', self.write_exr_applyimaging)
			params.add_bool('write_exr_ZBuf', self.write_zbuf)
			params.add_string('write_exr_compressiontype', self.write_exr_compressiontype)
			params.add_string('write_exr_zbuf_normalizationtype', self.zbuf_normalization)
			params.add_bool('write_exr', self.write_exr)
			if self.write_exr: params.add_string('write_exr_channels', output_channels)
		
		params.add_bool('write_png', self.write_png)
		if self.write_png:
			params.add_string('write_png_channels', output_channels)
			params.add_bool('write_png_16bit', self.write_png_16bit)
		params.add_bool('write_tga', self.write_tga)
		if self.write_tga:
			params.add_string('write_tga_channels', output_channels)
			params.add_string('write_tga_Zbuf', self.write_zbuf)
			params.add_string('write_tga_zbuf_normalizationtype', self.zbuf_normalization)
		
		params.add_string('ldr_clamp_method', self.ldr_clamp_method)
		
		if scene.luxrender_engine.export_type == 'EXT':
			params.add_integer('displayinterval', self.displayinterval)
			params.add_integer('writeinterval', self.writeinterval)
			params.add_integer('flmwriteinterval', self.flmwriteinterval)
		else:
			params.add_integer('writeinterval', self.internal_updateinterval)
		
		# Halt conditions
		if scene.luxrender_halt.haltspp > 0:
			params.add_integer('haltspp', scene.luxrender_halt.haltspp)
		
		if scene.luxrender_halt.halttime > 0:
			params.add_integer('halttime', scene.luxrender_halt.halttime)
		
		if self.outlierrejection_k > 0 and scene.luxrender_rendermode.renderer != 'sppm':
			params.add_integer('outlierrejection_k', self.outlierrejection_k)
			
		params.add_integer('tilecount', self.tilecount)
		
		# update the film settings with tonemapper settings
		params.update( self.luxrender_tonemapping.get_paramset() )
		
		return ('fleximage', params)

# Valid CRF preset names (case sensitive):
# See lux/core/cameraresponse.cpp to keep this up to date

crf_preset_names = [s.strip() for s in
"""Advantix_100CD
Advantix_200CD
Advantix_400CD
Agfachrome_ctpecisa_200CD
Agfachrome_ctprecisa_100CD
Agfachrome_rsx2_050CD
Agfachrome_rsx2_100CD
Agfachrome_rsx2_200CD
Agfacolor_futura_100CD
Agfacolor_futura_200CD
Agfacolor_futura_400CD
Agfacolor_futuraII_100CD
Agfacolor_futuraII_200CD
Agfacolor_futuraII_400CD
Agfacolor_hdc_100_plusCD
Agfacolor_hdc_200_plusCD
Agfacolor_hdc_400_plusCD
Agfacolor_optimaII_100CD
Agfacolor_optimaII_200CD
Agfacolor_ultra_050_CD
Agfacolor_vista_100CD
Agfacolor_vista_200CD
Agfacolor_vista_400CD
Agfacolor_vista_800CD
Ektachrome_100_plusCD
Ektachrome_100CD
Ektachrome_320TCD
Ektachrome_400XCD
Ektachrome_64CD
Ektachrome_64TCD
Ektachrome_E100SCD
F125CD
F250CD
F400CD
FCICD
Gold_100CD
Gold_200CD
Kodachrome_200CD
Kodachrome_25CD
Kodachrome_64CD
Max_Zoom_800CD
Portra_100TCD
Portra_160NCCD
Portra_160VCCD
Portra_400NCCD
Portra_400VCCD
Portra_800CD""".splitlines()]

@LuxRenderAddon.addon_register_class
class CAMERA_OT_set_luxrender_crf(bpy.types.Operator):
	bl_idname = 'camera.set_luxrender_crf'
	bl_label = 'Set LuxRender Film Response Function'
	
	preset_name = bpy.props.StringProperty()
	
	@classmethod
	def poll(cls, context):
		return	context.camera and \
			context.camera.luxrender_camera.luxrender_film.luxrender_colorspace
	
	def execute(self, context):
		context.camera.luxrender_camera.luxrender_film.luxrender_colorspace.crf_preset = self.properties.preset_name
		return {'FINISHED'}

@LuxRenderAddon.addon_register_class
class CAMERA_MT_luxrender_crf(bpy.types.Menu):
	bl_label = 'CRF Preset'
	
	# Flat-list menu system
	def draw(self, context):
		lt = self.layout.row()
		for i, crf_name in enumerate(sorted(crf_preset_names)):
			# Create a new column every 20 items
			if (i%20 == 0):
				cl = lt.column()
			op = cl.operator('CAMERA_OT_set_luxrender_crf', text=crf_name)
			op.preset_name = crf_name

@LuxRenderAddon.addon_register_class
class luxrender_colorspace(declarative_property_group):
	'''
	Storage class for LuxRender Colour-Space settings.
	'''
	
	ef_attach_to = ['luxrender_film']
	
	controls = [
		'cs_label',
		[0.1, 'preset', 'preset_name'],
		['cs_whiteX', 'cs_whiteY'],
		['cs_redX', 'cs_redY'],
		['cs_greenX', 'cs_greenY'],
		['cs_blueX', 'cs_blueY'],
		
		'gamma_label',
		'gamma',
	]
	
	if LUXRENDER_VERSION >= '0.8':
		controls.extend([
			'crf_label',
			'use_crf',
			'crf_preset_menu',
			'crf_file'
		])
	
	visibility = {
		'preset_name':		{ 'preset': True },
		'cs_whiteX':		{ 'preset': False },
		'cs_whiteY':		{ 'preset': False },
		'cs_redX':			{ 'preset': False },
		'cs_redY':			{ 'preset': False },
		'cs_greenX':		{ 'preset': False },
		'cs_greenY':		{ 'preset': False },
		'cs_blueX':			{ 'preset': False },
		'cs_blueY':			{ 'preset': False },
		
		'crf_preset_menu':	{ 'use_crf': 'preset' },
		'crf_file':			{ 'use_crf': 'file' },
		
		'gamma_label':		{ 'preset': False },
		'gamma':			{ 'preset': False },
	}
	
	properties = [
		{
			'attr': 'cs_label',
			'type': 'text',
			'name': 'Color Space'
		},
		{
			'attr': 'gamma_label',
			'type': 'text',
			'name': 'Gamma'
		},
		{
			'attr': 'gamma',
			'type': 'float',
			'name': 'Gamma',
			'default': 2.2,
			'min': 0.1,
			'soft_min': 0.1,
			'max': 20.0,
			'soft_max': 20.0
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
		
		# Camera Response Functions
		{
			'attr': 'crf_label',
			'type': 'text',
			'name': 'Film Response Function',
		},
		{
			'attr': 'use_crf',
			'type': 'enum',
			'name': 'Use Film Response',
			'default': 'none',
			'items': [
				('none', 'None', 'Don\'t use a Film Response'),
				('file', 'File', 'Load a Film Response from file'),
				('preset', 'Preset', 'Use a built-in Film Response Preset'),
			],
			'expand': True
		},
		{
			'type': 'ef_callback',
			'attr': 'crf_preset_menu',
			'method': 'draw_crf_preset_menu',
		},
		{
			'attr': 'crf_file',
			'type': 'string',
			'subtype': 'FILE_PATH',
			'name': 'Film Reponse File',
			'default': '',
		},
		{
			'attr': 'crf_preset',
			'type': 'string',
			'name': 'Film Reponse Preset',
			'default': 'Film Response Preset',
		},
	]

class colorspace_presets(object):
	class sRGB(object):
		gamma		= 2.2		# This is still approximate
		cs_whiteX	= 0.314275
		cs_whiteY	= 0.329411
		cs_redX		= 0.63
		cs_redY		= 0.34
		cs_greenX	= 0.31
		cs_greenY	= 0.595
		cs_blueX	= 0.155
		cs_blueY	= 0.07
	class romm_rgb(object):
		gamma		= 1.8
		cs_whiteX	= 0.346
		cs_whiteY	= 0.359
		cs_redX		= 0.7347
		cs_redY		= 0.2653
		cs_greenX	= 0.1596
		cs_greenY	= 0.8404
		cs_blueX	= 0.0366
		cs_blueY	= 0.0001
	class adobe_rgb_98(object):
		gamma		= 2.2
		cs_whiteX	= 0.313
		cs_whiteY	= 0.329
		cs_redX		= 0.64
		cs_redY		= 0.34
		cs_greenX	= 0.21
		cs_greenY	= 0.71
		cs_blueX	= 0.15
		cs_blueY	= 0.06
	class apple_rgb(object):
		gamma		= 1.8		# TODO: verify
		cs_whiteX	= 0.313
		cs_whiteY	= 0.329
		cs_redX		= 0.625
		cs_redY		= 0.34
		cs_greenX	= 0.28
		cs_greenY	= 0.595
		cs_blueX	= 0.155
		cs_blueY	= 0.07
	class ntsc_1953(object):
		gamma		= 2.2		# TODO: verify
		cs_whiteX	= 0.31
		cs_whiteY	= 0.316
		cs_redX		= 0.67
		cs_redY		= 0.33
		cs_greenX	= 0.21
		cs_greenY	= 0.71
		cs_blueX	= 0.14
		cs_blueY	= 0.08
	class ntsc_1979(object):
		gamma		= 2.2		# TODO: verify
		cs_whiteX	= 0.313
		cs_whiteY	= 0.329
		cs_redX		= 0.63
		cs_redY		= 0.34
		cs_greenX	= 0.31
		cs_greenY	= 0.595
		cs_blueX	= 0.155
		cs_blueY	= 0.07
	class pal_secam(object):
		gamma		= 2.8
		cs_whiteX	= 0.313
		cs_whiteY	= 0.329
		cs_redX		= 0.64
		cs_redY		= 0.33
		cs_greenX	= 0.29
		cs_greenY	= 0.6
		cs_blueX	= 0.15
		cs_blueY	= 0.06
	class cie_e(object):
		gamma		= 2.2
		cs_whiteX	= 0.333
		cs_whiteY	= 0.333
		cs_redX		= 0.7347
		cs_redY		= 0.2653
		cs_greenX	= 0.2738
		cs_greenY	= 0.7174
		cs_blueX	= 0.1666
		cs_blueY	= 0.0089

@LuxRenderAddon.addon_register_class
class luxrender_tonemapping(declarative_property_group):
	'''
	Storage class for LuxRender ToneMapping settings.
	'''
	
	ef_attach_to = ['luxrender_film']
	
	controls = [
		'tm_label',
		'type',
		
		# Reinhard
		['reinhard_prescale', 'reinhard_postscale', 'reinhard_burn'],
		
		# Contrast
		'ywa',
	]
	
	visibility = {
		# Reinhard
		'reinhard_prescale':	{ 'type': 'reinhard' },
		'reinhard_postscale':	{ 'type': 'reinhard' },
		'reinhard_burn':		{ 'type': 'reinhard' },
		
		# Linear
		# all params are taken from camera/colorspace settings
		
		# Contrast
		'ywa':					{ 'type': 'contrast' },
	}
	
	properties = [
		{
			'attr': 'tm_label',
			'type': 'text',
			'name': 'Tonemapping'
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Tonemapper',
			'description': 'Choose tonemapping type',
			'default': 'autolinear',
			'items': [
				('reinhard', 'Reinhard', 'reinhard'),
				('linear', 'Linear (manual)', 'linear'),
				('autolinear', 'Linear (auto-exposure)', 'autolinear'),
				('contrast', 'Contrast', 'contrast'),
				('maxwhite', 'Maxwhite', 'maxwhite')
			]
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
	
	def get_paramset(self):
		cam = LuxManager.CurrentScene.camera.data
		
		params = ParamSet()
		
		params.add_string('tonemapkernel', self.type)
		
		if self.type == 'reinhard':
			params.add_float('reinhard_prescale', self.reinhard_prescale)
			params.add_float('reinhard_postscale', self.reinhard_postscale)
			params.add_float('reinhard_burn', self.reinhard_burn)
			
		if self.type == 'linear':
			params.add_float('linear_sensitivity', cam.luxrender_camera.sensitivity)
			params.add_float('linear_exposure', cam.luxrender_camera.exposure_time())
			params.add_float('linear_fstop', cam.luxrender_camera.fstop)
			params.add_float('linear_gamma', cam.luxrender_camera.luxrender_film.get_gamma())
			
		if self.type == 'contrast':
			params.add_float('contrast_ywa', self.ywa)
		
		return params
