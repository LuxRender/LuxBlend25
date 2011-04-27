# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Genscher
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
from math import degrees

import bpy

from extensions_framework import util as efutil

from ..outputs import LuxManager
from ..outputs.file_api import Files
from ..export import ParamSet, get_worldscale, matrix_to_list

def attr_light(lux_context, light, name, group, type, params, transform=None, portals=[]):
	'''
	lux_context		pylux.Context
	name			string
	group			string LightGroup name
	type			string
	params			dict
	transform		None or list
	
	This method outputs a lightSource of the given name and
	type to context lux_context. The lightSource will be
	wrapped in a transformBegin...transformEnd block if
	a transform is given, otherwise it will appear in an
	attributeBegin...attributeEnd block.
	
	Returns			None
	'''
	
	if transform is not None:
		lux_context.transformBegin(comment=name, file=Files.MAIN)
		lux_context.transform(transform)
	else:
		lux_context.attributeBegin(comment=name, file=Files.MAIN)
	
	if light.type == 'SPOT' and light.luxrender_lamp.luxrender_lamp_spot.projector:
		lux_context.rotate(180, 0,1,0)
	
	lux_context.lightGroup(group, [])
	
	mirrorTransform = light.type == 'HEMI' and light.luxrender_lamp.luxrender_lamp_hemi.type == 'infinite'
	
	if mirrorTransform:
		# correct worldmap orientation
		lux_context.transformBegin(file=Files.MAIN)
		lux_context.scale(-1, 1, 1) 
	
	if light.luxrender_lamp.Exterior_volume != '':
		lux_context.exterior(light.luxrender_lamp.Exterior_volume)
	elif LuxManager.CurrentScene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(LuxManager.CurrentScene.luxrender_world.default_exterior_volume)
	
	lux_context.lightSource(type, params)

	if mirrorTransform:
		lux_context.transformEnd()
	
	for portal in portals:
		lux_context.portalInstance(portal)
	
	if transform is not None:
		lux_context.transformEnd()
	else:
		lux_context.attributeEnd()

def exportLight(scene, lux_context, ob, matrix, portals = []):
	light = ob.data
	
	lg_gain = 1.0
	light_group = light.luxrender_lamp.lightgroup
	
	# If this lamp's light group is disabled, skip it
	if not scene.luxrender_lightgroups.is_enabled(light_group):
		return False
	
	if light_group in scene.luxrender_lightgroups.lightgroups:
		lg_gain = scene.luxrender_lightgroups.lightgroups[light_group].gain
	
	if scene.luxrender_lightgroups.ignore or light.luxrender_lamp.lightgroup == "" :
		light_group = 'default'
	
	# Params common to all light types
	light_params = ParamSet() \
		.add_float('gain', light.energy*lg_gain) \
		.add_float('importance', light.luxrender_lamp.importance)
	
	ies_data = ParamSet()
	if light.luxrender_lamp.iesname != '':
		if light.library is not None:
			iespath = bpy.path.abspath(light.luxrender_lamp.iesname, light.library.filepath)
		else:
			iespath = light.luxrender_lamp.iesname
		ies_data = ParamSet().add_string('iesname', efutil.path_relative_to_export(iespath))
	
	# Params from light sub-types
	light_params.update( getattr(light.luxrender_lamp, 'luxrender_lamp_%s'%light.type.lower() ).get_paramset(ob) )
	
	# Other lamp params from lamp object
	if light.type == 'SUN':
		invmatrix = matrix.inverted()
		if light.luxrender_lamp.luxrender_lamp_sun.sunsky_type != 'sky': light_params.add_vector('sundir', (invmatrix[0][2], invmatrix[1][2], invmatrix[2][2]))
		attr_light(lux_context, light, ob.name, light_group, light.luxrender_lamp.luxrender_lamp_sun.sunsky_type, light_params, portals=portals)
		return True
	
	if light.type == 'HEMI':
		hemi_type = light.luxrender_lamp.luxrender_lamp_hemi.type
		if hemi_type == 'distant':
			light_params.add_point('from', (0,0,0))
			light_params.add_point('to', (0,0,-1))
		
		attr_light(lux_context, light, ob.name, light_group, hemi_type, light_params, transform=matrix_to_list(matrix, apply_worldscale=True), portals=portals)
		return True
	
	if light.type == 'SPOT':
		light_params.update( ies_data )
		coneangle = degrees(light.spot_size) * 0.5
		conedeltaangle = degrees(light.spot_size * 0.5 * light.spot_blend)
		
		if light.luxrender_lamp.luxrender_lamp_spot.projector:
			light_type = 'projection'
			light_params.add_float('fov', coneangle*2)
		else:
			light_type = 'spot'
			light_params.add_point('from', (0,0,0))
			light_params.add_point('to', (0,0,-1))
			light_params.add_float('coneangle', coneangle)
			light_params.add_float('conedeltaangle', conedeltaangle)
		
		attr_light(lux_context, light, ob.name, light_group, light_type, light_params, transform=matrix_to_list(matrix, apply_worldscale=True))
		return True

	if light.type == 'POINT':
		light_params.update( ies_data )
		light_params.add_point('from', (0,0,0)) # (0,0,0) is correct since there is an active Transform
		attr_light(lux_context, light, ob.name, light_group, 'point', light_params, transform=matrix_to_list(matrix, apply_worldscale=True))
		return True
	
	if light.type == 'AREA':
		light_params.update( ies_data )
		# overwrite gain with a gain scaled by ws^2 to account for change in lamp area
		light_params.add_float('gain', light.energy * lg_gain * (get_worldscale(as_scalematrix=False)**2))
		lux_context.attributeBegin(ob.name, file=Files.MAIN)
		lux_context.transform(matrix_to_list(matrix, apply_worldscale=True))
		lux_context.lightGroup(light_group, [])
		
		if light.luxrender_lamp.Exterior_volume != '':
			lux_context.exterior(light.luxrender_lamp.Exterior_volume)
		elif scene.luxrender_world.default_exterior_volume != '':
			lux_context.exterior(scene.luxrender_world.default_exterior_volume)
		
		lux_context.areaLightSource('area', light_params)
		
		areax = light.size
		
		if light.shape == 'SQUARE':
			areay = areax
		elif light.shape == 'RECTANGLE':
			areay = light.size_y
		else:
			areay = areax # not supported yet
		
		points = [-areax/2.0, areay/2.0, 0.0, areax/2.0, areay/2.0, 0.0, areax/2.0, -areay/2.0, 0.0, -areax/2.0, -areay/2.0, 0.0]
		
		shape_params = ParamSet()
		
		if lux_context.API_TYPE == 'PURE':
			# ntris isn't really the number of tris!!
			shape_params.add_integer('ntris', 6)
			shape_params.add_integer('nvertices', 4)
		
		shape_params.add_integer('indices', [0, 1, 2, 0, 2, 3])
		shape_params.add_point('P', points)
		
		lux_context.shape('trianglemesh', shape_params)
		
		for portal in portals:
			lux_context.portalInstance(portal)
		
		lux_context.attributeEnd()
		
		return True

	return False

def lights(lux_context, geometry_scene, visibility_scene, mesh_definitions):
	'''
	lux_context		pylux.Context
	Iterate over the given scene's light sources,
	and export the compatible ones to the context lux_context.
	
	Returns Boolean indicating if any light sources
	were exported.
	'''
	
	have_light = False
	
	# First gather info about portals
	portal_shapes = []
	mesh_def_keys = {}
	for k in mesh_definitions.cache_items.keys():
		# PLY proxies add string keys into mesh_definitions,
		# and the external meshes are never portals, so skip them
		if type(k) is str: continue
		
		if not k[1] in mesh_def_keys.keys():
			mesh_def_keys[k[1]] = []
		mesh_def_keys[k[1]].append(k)
	mesh_def_keys_keys = mesh_def_keys.keys()
	for obdata in mesh_def_keys_keys:
		# match the mesh data against the keys in mesh_definitions
		if obdata.luxrender_mesh.portal:
			for mesh_def_key in mesh_def_keys[obdata]:
				portal_shapes.append(mesh_definitions.get(mesh_def_key)[0])
	
	# Then iterate for lights
	for ob in geometry_scene.objects:
		
		if not ob.is_visible(visibility_scene) or ob.hide_render:
			continue
		
		# skip dupli (child) objects when they are not lamps
		if (ob.parent and ob.parent.is_duplicator) and ob.type != 'LAMP':
			continue
		
		# we have to check for duplis before the "LAMP" check 
		# to support a mesh/object which got lamp as dupli object
		if ob.is_duplicator and ob.dupli_type in ('GROUP', 'VERTS', 'FACES'):
			# create dupli objects
			ob.dupli_list_create(geometry_scene)
			
			for dupli_ob in ob.dupli_list:
				if dupli_ob.object.type != 'LAMP':
					continue
				have_light |= exportLight(visibility_scene, lux_context, dupli_ob.object, dupli_ob.matrix, portal_shapes)
			
			# free object dupli list again. Warning: all dupli objects are INVALID now!
			if ob.dupli_list: 
				ob.dupli_list_clear()
		else:
			if ob.type == 'LAMP':
				have_light |= exportLight(visibility_scene, lux_context, ob, ob.matrix_world, portal_shapes)
	
	return have_light

