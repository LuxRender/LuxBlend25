# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Exporter Framework - LuxRender Plug-in
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Daniel Genrich
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
import random

import bpy

from ..module import LuxLog
from ..module.file_api import Files
from . import matrix_to_list
from . import ParamSet
from .materials import export_object_material

#-------------------------------------------------
# getMeshType(self, scene, mesh, ss)
# returns type of mesh as string to use depending on thresholds
#-------------------------------------------------
def getMeshType(mesh):
	
	params = ParamSet()
	dstr = 'trianglemesh'

	# check if subdivision is used
	if mesh.luxrender_mesh.subdiv == True:
		dstr = 'loopsubdiv'
		params.add_integer('nlevels', mesh.luxrender_mesh.sublevels)
		params.add_bool('dmnormalsmooth', mesh.luxrender_mesh.nsmooth)
		params.add_bool('dmsharpboundary', mesh.luxrender_mesh.sharpbound)
	
	return dstr,params

def exportMesh(ob, me, l, smoothing_enabled):
	
	faces_verts = [f.verts for f in me.faces]
	ffaces = [f for f in me.faces]
	#faces_normals = [tuple(f.normal) for f in me.faces]
	#verts_normals = [tuple(v.normal) for v in me.verts]
	
	# face indices
	index = 0
	indices = []
	ntris = 0
	for face in ffaces:
		indices.append(index)
		indices.append(index+1)
		indices.append(index+2)
		ntris += 3
		if (len(face.verts)==4):
			indices.append(index)
			indices.append(index+2)
			indices.append(index+3)
			ntris += 3
		index += len(face.verts)
		
	# vertex positions
	points = []
	nvertices = 0
	for face in ffaces:
		for vertex in face.verts:
			v = me.verts[vertex]
			nvertices += 1
			for co in v.co:
				points.append(co)
				
	# vertex normals
	normals = []
	for face in ffaces:
		normal = face.normal
		for vertex in face.verts:
			if (smoothing_enabled and face.smooth):
				normal = vertex.normal
			for no in normal:
				normals.append(no)
				
	# uv coordinates
	try:
		uv_layer = me.active_uv_texture.data
	except:
		uv_layer = None
		
	if uv_layer:
		uvs = []
		for fi, uv in enumerate(uv_layer):
			if len(faces_verts[fi]) == 4:
				face_uvs = uv.uv1, uv.uv2, uv.uv3, uv.uv4
			else:
				face_uvs = uv.uv1, uv.uv2, uv.uv3
			for uv in face_uvs:
				for single_uv in uv:
					uvs.append(single_uv)
					
	
	#print(' %s num points: %i' % (ob.name, len(points)))
	#print(' %s num normals: %i' % (ob.name, len(normals)))
	#print(' %s num idxs: %i' % (ob.name, len(indices)))
	
	# export shape		
	shape_type, shape_params = getMeshType(ob.data)
	
	if l.API_TYPE == 'PURE':
		# ntris isn't really the number of tris!!
		shape_params.add_integer('ntris', ntris)
		shape_params.add_integer('nvertices', nvertices)
	
	shape_params.add_integer('indices', indices)
	shape_params.add_point('P', points)
	shape_params.add_normal('N', normals)
	
	if uv_layer:
		#print(' %s num uvs: %i' % (ob.name, len(uvs)))
		shape_params.add_float('uv', uvs)
	
	#print(' %s ntris: %i' % (ob.name, ntris))
	#print(' %s nvertices: %i' % (ob.name, nvertices))
	
	l.shape(shape_type, shape_params)


def write_lxo(render_engine, l, scene, smoothing_enabled=True):
	'''
	l			pylux.Context
	scene		bpy.types.scene
	
	Iterate over the given scene's objects,
	and export the compatible ones to the context l.
	
	Returns		None
	'''
	
	vis_layers = scene.layers
	
	sel = scene.objects
	total_objects = len(sel)
	rpcs = []
	ipc = 0.0
	for ob in sel:
		ipc += 1.0
		
		if ob.type in ('LAMP', 'CAMERA', 'EMPTY', 'META', 'ARMATURE'):
			continue
		
		# Check layers
		visible = False
		for layer_index, o_layer in enumerate(ob.layers):
			visible = visible or (o_layer and vis_layers[layer_index])
		
		if not visible:
			continue
		
		me = ob.create_mesh(scene, True, 'RENDER')
		
		if not me:
			continue

		l.attributeBegin(comment=ob.name, file=Files.GEOM)
		
		# Export either NamedMaterial stmt or the full material
		# definition depending on the output type
		export_object_material(l, ob)
		
		# object translation/rotation/scale 
		l.transform( matrix_to_list(ob.matrix) )

		exportMesh(ob, me, l, smoothing_enabled)

		l.attributeEnd()
		
		bpy.data.meshes.remove(me)
		
		# TODO: this probably isn't very efficient for large scenes
		pc = int(100 * ipc/total_objects)
		if pc not in rpcs:
			rpcs.append(pc)
			render_engine.update_stats('', 'LuxRender: Parsing meshes %i%%' % pc)
	
