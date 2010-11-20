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

from luxrender.export import ParamSet
from luxrender.export.film import resolution
from luxrender.export.geometry import exportNativeMesh
from luxrender.outputs import LuxManager

def preview_scene(scene, lux_context, obj=None, mat=None):
	
	HALTSPP = 256
	
	# Camera
	lux_context.lookAt(0.0,-3.0,0.5, 0.0,-2.0,0.5, 0.0,0.0,1.0)
	camera_params = ParamSet().add_float('fov', 22.5)
	lux_context.camera('perspective', camera_params)
	
	# Film
	xr, yr = resolution(scene)
	
	film_params = ParamSet() \
		.add_integer('xresolution', int(xr)) \
		.add_integer('yresolution', int(yr)) \
		.add_string('filename', 'luxblend25-preview') \
		.add_bool('write_exr', False) \
		.add_bool('write_exr_ZBuf', True) \
		.add_bool('write_exr_applyimaging', True) \
		.add_string('write_exr_channels', 'RGBA') \
		.add_bool('write_exr_halftype', False) \
		.add_float('gamma', 1.0) \
		.add_bool('write_png', False) \
		.add_bool('write_tga', False) \
		.add_bool('write_resume_flm', False) \
		.add_integer('displayinterval', 3) \
		.add_integer('writeinterval', 3600) \
		.add_integer('haltspp', HALTSPP) \
		.add_string('tonemapkernel', 'linear') \
		.add_integer('reject_warmup', 64)
	lux_context.film('fleximage', film_params)
	
	# Pixel Filter
	pixelfilter_params = ParamSet() \
		.add_float('xwidth', 1.5) \
		.add_float('ywidth', 1.5) \
		.add_float('B', 0.333) \
		.add_float('C', 0.333) \
		.add_bool('supersample', True)
	lux_context.pixelFilter('mitchell', pixelfilter_params)
	
	# Sampler
	sampler_params = ParamSet() \
		.add_string('pixelsampler', 'hilbert') \
		.add_integer('pixelsamples', 2)
	lux_context.sampler('lowdiscrepancy', sampler_params)
	
	# Surface Integrator
	surfaceintegrator_params = ParamSet() \
		.add_integer('directsamples', 1) \
		.add_integer('diffusereflectdepth', 2) \
		.add_integer('diffusereflectsamples', 4) \
		.add_integer('diffuserefractdepth', 8) \
		.add_integer('diffuserefractsamples', 1) \
		.add_integer('glossyreflectdepth', 2) \
		.add_integer('glossyreflectsamples', 2) \
		.add_integer('glossyrefractdepth', 8) \
		.add_integer('glossyrefractsamples', 1) \
		.add_integer('specularreflectdepth', 4) \
		.add_integer('specularrefractdepth', 8)
	lux_context.surfaceIntegrator('distributedpath', surfaceintegrator_params)
	
	lux_context.worldBegin()
	
	# Light
	lux_context.attributeBegin()
	lux_context.transform([
#		1.0, 0.0, 0.0, 0.0,
#		0.0, 1.0, 0.0, 0.0,
#		0.0, 0.0, 1.0, 0.0,
#		1.0, -1.0, 4.0, 1.0

		0.5996068120002747, 0.800294816493988, 2.980232594040899e-08, 0.0,
		-0.6059534549713135, 0.45399996638298035, 0.6532259583473206, 0.0,
		0.5227733850479126, -0.3916787803173065, 0.7571629285812378, 0.0,
		4.076245307922363, -3.0540552139282227, 5.903861999511719, 1.0

	])
	light_bb_params = ParamSet().add_float('temperature', 6500.0)
	lux_context.texture('pL', 'color', 'blackbody', light_bb_params)
	light_params = ParamSet() \
		.add_texture('L', 'pL') \
		.add_float('gain', 1.002)
	lux_context.areaLightSource('area', light_params)

	areax = 1
	areay = 1
	points = [-areax/2.0, areay/2.0, 0.0, areax/2.0, areay/2.0, 0.0, areax/2.0, -areay/2.0, 0.0, -areax/2.0, -areay/2.0, 0.0]
	
	shape_params = ParamSet()
	shape_params.add_integer('ntris', 6)
	shape_params.add_integer('nvertices', 4)
	shape_params.add_integer('indices', [0, 1, 2, 0, 2, 3])
	shape_params.add_point('P', points)
	lux_context.shape('trianglemesh', shape_params)
	lux_context.attributeEnd()
	
	# Add a background color (light)
	lux_context.lightSource('infinite', ParamSet().add_float('gain', 0.2))
	
	# back drop
	lux_context.attributeBegin()
	lux_context.transform([
		5.0, 0.0, 0.0, 0.0,
		0.0, 5.0, 0.0, 0.0,
		0.0, 0.0, 5.0, 0.0,
		0.0, 0.0, 0.0, 1.0
	])
	lux_context.scale(4,1,1)
	checks_pattern_params = ParamSet() \
		.add_integer('dimension', 2) \
		.add_string('mapping', 'uv') \
		.add_float('uscale', 36.8) \
		.add_float('vscale', 36.0*4) #.add_string('aamode', 'supersample') \
	lux_context.texture('checks::pattern', 'float', 'checkerboard', checks_pattern_params)
	checks_params = ParamSet() \
		.add_texture('amount', 'checks::pattern') \
		.add_color('tex1', [0.9, 0.9, 0.9]) \
		.add_color('tex2', [0.0, 0.0, 0.0])
	lux_context.texture('checks', 'color', 'mix', checks_params)
	mat_params = ParamSet().add_texture('Kd', 'checks')
	lux_context.material('matte', mat_params)
	bd_shape_params = ParamSet() \
		.add_integer('nlevels', 3) \
		.add_bool('dmnormalsmooth', True) \
		.add_bool('dmsharpboundary', False) \
		.add_integer('ntris', 18) \
		.add_integer('nvertices', 8) \
		.add_integer('indices', [0,1,2,0,2,3,1,0,4,1,4,5,5,4,6,5,6,7]) \
		.add_point('P', [
			 1.0,  1.0, 0.0,
			-1.0,  1.0, 0.0,
			-1.0, -1.0, 0.0,
			 1.0, -1.0, 0.0,
			 1.0,  3.0, 0.0,
			-1.0,  3.0, 0.0,
			 1.0,  3.0, 2.0,
			-1.0,  3.0, 2.0,
		]) \
		.add_normal('N', [
			0.0,  0.000000, 1.000000,
			0.0,  0.000000, 1.000000,
			0.0,  0.000000, 1.000000,
			0.0,  0.000000, 1.000000,
			0.0, -0.707083, 0.707083,
			0.0, -0.707083, 0.707083,
			0.0, -1.000000, 0.000000,
			0.0, -1.000000, 0.000000,
		]) \
		.add_float('uv', [
			0.333334, 0.000000,
			0.333334, 0.333334,
			0.000000, 0.333334,
			0.000000, 0.000000,
			0.666667, 0.000000,
			0.666667, 0.333333,
			1.000000, 0.000000,
			1.000000, 0.333333,
		])
	lux_context.shape('loopsubdiv', bd_shape_params)
	lux_context.attributeEnd()
	
	# Collect volumes from all scenes *sigh*
	preview_scene = LuxManager.CurrentScene
	for scn in bpy.data.scenes:
		LuxManager.SetCurrentScene(scn)
		for volume in scn.luxrender_volumes.volumes:
			lux_context.makeNamedVolume( volume.name, *volume.api_output(lux_context) )
	LuxManager.SetCurrentScene(preview_scene)
	
	if obj is not None and mat is not None:
		# preview object
		lux_context.attributeBegin()
		pv_transform = [
			0.5, 0.0, 0.0, 0.0,
			0.0, 0.5, 0.0, 0.0,
			0.0, 0.0, 0.5, 0.0,
			0.0, 0.0, 0.5, 1.0
		]
		pv_export_shape = True
		
		if mat.preview_render_type == 'FLAT':
			pv_export_shape = False
		if mat.preview_render_type == 'SPHERE':
			pv_transform = [
				0.1, 0.0, 0.0, 0.0,
				0.0, 0.1, 0.0, 0.0,
				0.0, 0.0, 0.1, 0.0,
				0.0, 0.0, 0.5, 1.0
			]
		if mat.preview_render_type == 'CUBE':
			lux_context.scale(0.8, 0.8, 0.8)
			lux_context.rotate(-35, 0,0,1)
		if mat.preview_render_type == 'MONKEY':
			pv_transform = [
				1.0573405027389526, 0.6340668201446533, 0.0, 0.0,
				-0.36082395911216736, 0.601693332195282, 1.013795018196106, 0.0,
				0.5213892459869385, -0.8694445490837097, 0.7015902996063232, 0.0,
				0.0, 0.0, 0.5, 1.0
			]
		if mat.preview_render_type == 'HAIR':
			pv_export_shape = False
		if mat.preview_render_type == 'SPHERE_A':
			pv_export_shape = False
		
		lux_context.concatTransform(pv_transform)
		
		mat.luxrender_material.export(scene, lux_context, mat, mode='direct')
		
		if mat.luxrender_material.type in ['glass2']:
			lux_context.interior(mat.luxrender_material.luxrender_mat_glass2.Interior_volume)
			lux_context.exterior(mat.luxrender_material.luxrender_mat_glass2.Exterior_volume)
		
		if pv_export_shape:
			pv_mesh = obj.create_mesh(scene, True, 'RENDER')
			lux_context.shape( *exportNativeMesh(scene, pv_mesh, lux_context) )
			bpy.data.meshes.remove(pv_mesh)
		else:
			lux_context.shape('sphere', ParamSet().add_float('radius', 1.0))
		lux_context.attributeEnd()
	
	return int(xr), int(yr)
	