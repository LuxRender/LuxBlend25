# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
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


"""

This file needs re-writing, according to the following outline plan.
Current implementation has become bloated with overloads in order to
try and match blender's internal behaviour, but proceeding like this
is doomed to failure. Moreover, the current code doesn't fully implement
all of Blender's object features, and to do so will create much more
hideous mess.
I'm also planning to drop the experimental PLY mesh export type, as
it is technically not possible at the minute and is complicating the
code unnecessarily.

DH 26/1/11


def buildNativeMesh:
 purpose:
  Split up a blender MESH into parts according to vertex material assignment,
  and construct a mesh_name and ParamSet for each part which will become a
  LuxRender Shape statement.
  The current implementation of this method in exportNativeMesh is more or less
  already correct.
 input: mesh
 process:
  split mesh by material
  construct (mesh_name, mesh_mat, mesh_type, mesh_params) object for each part
  update mesh_params with luxrender_mesh.get_paramset()
  append object to list
 return: list of mesh part objects

def exportMeshDefinition:
 purpose:
  If the mesh is valid and instancing is allowed for this object, export
  an objectBegin..objectEnd block containing the Shape definition.
  This is a simplified version of the existing exportMesh method.
 input: mesh part object from buildNativeMesh
 process:
  if mesh_name in exported meshes list: return	# skip duplicates
  if len(mesh_params) < 1: return				# skip empty meshes
  if not allow_instancing(): return				# don't do anything if we cannot instance
  objectBegin mesh_name
  shape(mesh_type, mesh_params)
  objectEnd
  update exported meshes list with mesh_name
 return: None

def exportMeshInstance:
 purpose:
  Export an instance of a Mesh (full Shape or objectInstance statement)
  wrapped in an attibuteBegin..attributeEnd block, along with the object's
  transform, emission and materials info.
 input: mesh part object from buildNativeMesh, Object
 attributeBegin mesh_name
 transform(*matrix)
 export emission data
 export int/ext statement from mesh_mat
 detect if Object is animated
 if not allow_instancing() or emitter (or mesh_name not in exported meshes list?):
  shape(mesh_type, mesh_params)
 elif animated:
  export transform + motionInstance
 else:
  objectInstance(mesh_name)
 attributeEnd
 return: None

def iterateScene:
 purpose:
  Scan the input scene for objects that LuxRender can handle, and output
  them to the lux_context provided.
  It might also be wise to construct a map of {object types:handler functions}
  so that the iteration loops don't get clogged with implementation details
  and it is clear to see how each object type is handled.
  We probably also need some kind of tracking object (like ExportedMeshes in
  materials.py) to construct per-export lists of known mesh definitions (or
  parts thereof) and objects already exported in order to avoid duplicate
  work or output.
 input: lux_context, scene
 process:
  set up object handler callbacks:
   callbacks = {
    'duplis': {
     'GROUP': handler_Duplis_GROUP,
     'VERTS': handler_Duplis_VERTS,
     # etc
    },
    'particles': {
     'TYPE1': handler_Particles_TYPE1,
     # etc
    }
    'objects': {
     'MESH': handler_MESH,
     'EMPTY': handler_EMPTY,
     # etc
    }
   }
   valid_duplis_types = callbacks['duplis'].keys()
   valid_particles_types = callbacks['particles'].keys()
   valid_objects_types = callbacks['objects'].keys()
  for object in scene:
   if object_type in valid_objects_types:
    if is dupli without particles and dupli_type in valid_duplis_types:
     callbacks['duplis'][dupli_type](lux_context, scene, object)
    if has particle systems and particles_type in valid_particles_types:
     callbacks['particles'][particles_type](lux_context, scene, object)
    
    if object is a proxy for external PLYShape:
     export a PLYShape + instance with this object's transform
    
    if original object should still be exported, according to dupli, particles and override rules:
     callbacks['objects'][object_type](lux_context, scene, object)
 return: None


# Example callback:

handler_Duplis_GROUP:
 purpose:
  Handle DupliGroups
 input: lux_context, scene, object
 process:
  construct dupli list for this object
  export mesh definitions for the group being duplicated
  export instances of each mesh definition at each dupli location
 return: None


"""








import bpy, mathutils

from extensions_framework import util as efutil

from luxrender.outputs import LuxLog
from luxrender.outputs.file_api import Files
from luxrender.export import ParamSet, LuxManager
from luxrender.export import matrix_to_list
from luxrender.export.materials import get_instance_materials, add_texture_parameter

OBJECT_ANALYSIS = False

class InvalidGeometryException(Exception):
	pass

def exportNativeMesh(mesh_name, mesh, lux_context):
	
	if OBJECT_ANALYSIS: print(' -> NativeMesh:')
	
	mesh_definitions = []
	
	# Cache vert positions because me.vertices access is very slow
	#print('-> Cache vert pos and normals')
	verts_co_no = [tuple(v.co)+tuple(v.normal) for v in mesh.vertices]
	
	# collate faces and face verts by mat index
	faces_verts_mats = {}
	ffaces_mats = {}
	for f in mesh.faces:
		mi = f.material_index
		if mi not in faces_verts_mats.keys(): faces_verts_mats[mi] = []
		faces_verts_mats[mi].append( f.vertices )
		if mi not in ffaces_mats.keys(): ffaces_mats[mi] = []
		ffaces_mats[mi].append( f )
	
	for i in range(len(mesh.materials)):
		
		if mesh.materials[i] is None: continue
		if i not in faces_verts_mats.keys(): continue
		if i not in ffaces_mats.keys(): continue
		
		if OBJECT_ANALYSIS: print('  -> Material: %s' % mesh.materials[i])
		
		mesh_name = ('%s_%s' % (mesh_name, mesh.materials[i].name)).replace(' ','_')
		
		if OBJECT_ANALYSIS: print('  -> derived mesh name: %s' % mesh_name)
		
		# face indices
		index = 0
		indices = []
		ntris = 0
		#print('-> Collect face indices')
		for face in ffaces_mats[i]:
			indices.append(index)
			indices.append(index+1)
			indices.append(index+2)
			ntris += 3
			if (len(face.vertices)==4):
				indices.append(index)
				indices.append(index+2)
				indices.append(index+3)
				ntris += 3
			index += len(face.vertices)
		
		if ntris == 0:
			raise InvalidGeometryException()
		
		# vertex positions
		points = []
		#print('-> Collect vert positions')
		nvertices = 0
		for face in ffaces_mats[i]:
			for vertex in face.vertices:
				v = verts_co_no[vertex][:3]
				nvertices += 1
				for co in v:
					points.append(co)
		
		if nvertices == 0:
			raise InvalidGeometryException()
		
		# vertex normals
		#print('-> Collect mert normals')
		normals = []
		for face in ffaces_mats[i]:
			normal = face.normal
			for vertex in face.vertices:
				if face.use_smooth:
					normal = verts_co_no[vertex][3:]
				for no in normal:
					normals.append(no)
		
		# uv coordinates
		#print('-> Collect UV layers')
		
		if len(mesh.uv_textures) > 0:
			if mesh.uv_textures.active and mesh.uv_textures.active.data:
				uv_layer = mesh.uv_textures.active.data
		else:
			uv_layer = None
		
		if uv_layer:
			uvs = []
			for fi, uv in enumerate(uv_layer):
				if fi in range(len(faces_verts_mats[i])) and len(faces_verts_mats[i][fi]) == 4:
					face_uvs = uv.uv1, uv.uv2, uv.uv3, uv.uv4
				else:
					face_uvs = uv.uv1, uv.uv2, uv.uv3
				for uv in face_uvs:
					for single_uv in uv:
						uvs.append(single_uv)
		
		#print(' %s num points: %i' % (ob.name, len(points)))
		#print(' %s num normals: %i' % (ob.name, len(normals)))
		#print(' %s num idxs: %i' % (ob.name, len(indices)))
		
		# build shape ParamSet
		shape_params = ParamSet()
		
		if lux_context.API_TYPE == 'PURE':
			# ntris isn't really the number of tris!!
			shape_params.add_integer('ntris', ntris)
			shape_params.add_integer('nvertices', nvertices)
		
		#print('-> Add indices to paramset')
		shape_params.add_integer('triindices', indices)
		#print('-> Add verts to paramset')
		shape_params.add_point('P', points)
		#print('-> Add normals to paramset')
		shape_params.add_normal('N', normals)
		
		if uv_layer:
			#print(' %s num uvs: %i' % (ob.name, len(uvs)))
			#print('-> Add UVs to paramset')
			shape_params.add_float('uv', uvs)
		
		#print(' %s ntris: %i' % (ob.name, ntris))
		#print(' %s nvertices: %i' % (ob.name, nvertices))
		
		mesh_definitions.append( (mesh.materials[i], mesh_name, shape_params) )
	
	return mesh_definitions

def exportPlyMesh(mesh):
	ply_filename = efutil.export_path + '_' + bpy.path.clean_name(mesh.name) + '.ply'
	
	# TODO: find out how to set the context object
	# bpy.context.object = ob
	bpy.ops.export.ply(
		filepath = ply_filename,
		use_modifiers = True,
		use_normals = True,
		use_uv_coords = True,
		use_colors = False
	)
	
	ply_params = ParamSet()
	ply_params.add_string('filename', efutil.path_relative_to_export(ply_filename))
	ply_params.add_bool('smooth', mesh.use_auto_smooth)
	
	return mesh.name, ply_params

#-------------------------------------------------
# export_mesh(lux_context, object, object_begin_end=True, scale=None, log=True, transformed=False)
# create mesh from object and export it to file
#-------------------------------------------------
def exportMesh(lux_context, ob, object_begin_end=True, scale=None, log=True, transformed=False):
	scene = LuxManager.CurrentScene
	
	#print('-> Create render mesh')
	mesh = ob.create_mesh(scene, True, 'RENDER')
	if mesh is None:
		return
	
	try:
		mesh_definitions = []
		if scene.luxrender_engine.mesh_type == 'native':
			shape_type = ob.data.luxrender_mesh.get_shape_type()
			for mesh_mat, mesh_name, mesh_paramset in exportNativeMesh(ob.data.name, mesh, lux_context):
				mesh_paramset.update( ob.data.luxrender_mesh.get_paramset() )
				mesh_definitions.append( (mesh_mat, mesh_name, shape_type, mesh_paramset) )
			
		elif scene.luxrender_engine.mesh_type == 'ply':
			mesh_name, shape_params = exportPlyMesh(mesh)
			mesh_definitions.append( (None, mesh_name, 'plymesh', shape_params) )
		
	except InvalidGeometryException:
		pass
	
	mesh_names_mats = []
	for me_mat, me_name, me_shape_type, me_shape_params in mesh_definitions:
		
		if len(me_shape_params) == 0: continue
		
		if log or OBJECT_ANALYSIS: LuxLog('Mesh Exported: %s' % me_name)
		
		# Shape is the only thing to go into the ObjectBegin..ObjectEnd definition
		# Everything else is set on a per-instance basis
		if object_begin_end: lux_context.objectBegin(me_name)
		
		if scale is not None: lux_context.scale(*scale)
		
		if transformed: lux_context.transform( matrix_to_list(ob.matrix_world, apply_worldscale=True) )
		
		if lux_context.API_TYPE == 'FILE':
			lux_context.namedMaterial(me_mat.name)
		elif lux_context.API_TYPE == 'PURE':
			me_mat.luxrender_material.export(lux_context, me_mat, mode='direct')
		
		lux_context.shape(me_shape_type, me_shape_params)
		
		if object_begin_end: lux_context.objectEnd()
		mesh_names_mats.append( (me_name, me_mat, None) )
	
	#print('-> Remove render mesh')
	bpy.data.meshes.remove(mesh)
	
	return mesh_names_mats

def allow_instancing(dupli):
	# Some situations require full geometry export
	if LuxManager.CurrentScene.luxrender_engine.renderer == 'hybrid':
		return False
	
	# Only allow instancing for duplis and particles in non-hybrid mode
	return dupli

def get_material_volume_defs(m):
	return m.luxrender_material.Interior_volume, m.luxrender_material.Exterior_volume

def exportInstance(lux_context, ob, matrix, dupli=False, append_objects=None):
	scene = LuxManager.CurrentScene
	lux_context.attributeBegin(comment=ob.name, file=Files.GEOM)
	
	# object translation/rotation/scale 
	lux_context.transform( matrix_to_list(matrix, apply_worldscale=True) )
	
	# Check for emission and volume data
	object_is_emitter = hasattr(ob, 'luxrender_emission') and ob.luxrender_emission.use_emission
	if object_is_emitter:
		lux_context.lightGroup(ob.luxrender_emission.lightgroup, [])
		arealightsource_params = ParamSet() \
				.add_float('gain', ob.luxrender_emission.gain) \
				.add_float('power', ob.luxrender_emission.power) \
				.add_float('efficacy', ob.luxrender_emission.efficacy)
		arealightsource_params.update( add_texture_parameter(lux_context, 'L', 'color', ob.luxrender_emission) )
		lux_context.areaLightSource('area', arealightsource_params)
	
	exported_interior = exported_exterior = False
	for m in get_instance_materials(ob):
		# just export the first volume interior/exterior
		if hasattr(m, 'luxrender_material'):
			int_v, ext_v = get_material_volume_defs(m)
			if int_v != '' or ext_v != '':
				# Always use a matched pair of int_v/ext_v so that materials don't get mismatched
				if int_v != '':
					lux_context.interior(int_v)
					exported_interior = True
				if ext_v != '':
					lux_context.exterior(ext_v)
					exported_exterior = True
				break
	
	if not exported_interior and LuxManager.CurrentScene.luxrender_world.default_interior_volume != '':
		lux_context.interior(LuxManager.CurrentScene.luxrender_world.default_interior_volume)
	if not exported_exterior and LuxManager.CurrentScene.luxrender_world.default_exterior_volume != '':
		lux_context.exterior(LuxManager.CurrentScene.luxrender_world.default_exterior_volume)
	
	# object motion blur
	is_object_animated = False
	if scene.camera.data.luxrender_camera.usemblur and scene.camera.data.luxrender_camera.objectmblur:
		scene.frame_set(scene.frame_current + 1)
		m1 = matrix.copy()
		scene.frame_set(scene.frame_current - 1)
		scene.update()
		if m1 != matrix:
			is_object_animated = True
	
	# If the object emits, don't export instance or motioninstance
	if (not allow_instancing(dupli)) or object_is_emitter:
		exportMesh(lux_context, ob, object_begin_end=False, log=False)
	# special case for motion blur since the mesh is already exported before the attribute
	elif is_object_animated:
		lux_context.transformBegin(comment=ob.name, file=Files.GEOM)
		lux_context.identity()
		lux_context.transform(matrix_to_list(m1, apply_worldscale=True))
		lux_context.coordinateSystem('%s' % ob.data.name + '_motion')
		lux_context.transformEnd()
		lux_context.motionInstance(ob.data.name, 0.0, 1.0, ob.data.name + '_motion')
	elif not dupli and (append_objects is None or ob.data.name not in [i[0] for i in append_objects]):
		lux_context.objectInstance(ob.data.name)
	
	if append_objects is not None:
		for append_object, append_mat, append_transform in append_objects:
			#if not dupli and append_object != ob.data.name:
			if append_transform != None: lux_context.transform( matrix_to_list(append_transform, apply_worldscale=True) )
			if append_mat != None: lux_context.namedMaterial(append_mat.name)
			lux_context.objectInstance(append_object)
	
	lux_context.attributeEnd()

class MeshExportProgressThread(efutil.TimerThread):
	KICK_PERIOD = 1
	total_objects = 0
	exported_objects = 0
	last_update = 0
	def start(self, number_of_meshes):
		self.total_objects = number_of_meshes
		self.exported_objects = 0
		self.last_update = 0
		super().start()
	def kick(self):
		if self.exported_objects != self.last_update:
			self.last_update = self.exported_objects
			pc = int(100 * self.exported_objects/self.total_objects)
			LuxLog('LuxRender: Parsing meshes %i%%' % pc)
			bpy.ops.ef.msg(
				msg_type='INFO',
				msg_text='LuxRender: Parsing meshes %i%%' % pc
			)

#-------------------------------------------------
# write_lxo(lux_context)
# MAIN export function
#-------------------------------------------------
def write_lxo(lux_context):
	'''
	lux_context		pylux.Context
	
	Iterate over the given scene's objects,
	and export the compatible ones to the context lux_context.
	
	Returns		None
	'''
	
	scene = LuxManager.CurrentScene
	sel = scene.objects
	total_objects = len(sel)

	# browse all scene objects for "mesh-convertible" ones
	# First round: check for duplis
	duplis = []
	meshes_exported = set()
	
	dupli_object_mesh_names = {}
	
	for ob in sel:
		if OBJECT_ANALYSIS: print('Parsing objects pass 1: %s' % ob.name)
		# EMPTY is allowed because it is used as GROUP containers
		if ob.type in ('LAMP', 'CAMERA', 'META', 'ARMATURE', 'LATTICE'):
			if OBJECT_ANALYSIS: print(' -> disallowed type: %s' % ob.type)
			continue
		
		# Export only objects which are enabled for render (in the outliner) and visible on a render layer
		if not ob.is_visible(scene) or ob.hide_render:
			if OBJECT_ANALYSIS: print(' -> not visible: %s / %s' % (ob.is_visible(scene), ob.hide_render))
			continue
		
		if ob.parent and ob.parent.is_duplicator:
			if OBJECT_ANALYSIS: print(' -> parent is duplicator')
			continue
		
		number_psystems = len(ob.particle_systems)
		
		if ob.is_duplicator and number_psystems < 1:
			if OBJECT_ANALYSIS: print(' -> is duplicator without particle systems')
			# create dupli objects
			ob.create_dupli_list(scene)
			
			#import pdb
			#pdb.set_trace()
			
			# Scan meshes first
			append_objects = []
			for dupli_ob in ob.dupli_list:
				if dupli_ob.object.type != 'MESH':
					continue
				
				if dupli_ob.object.name not in dupli_object_mesh_names.keys():
					dupli_object_mesh_names[dupli_ob.object.name] = []
				
				if allow_instancing(dupli=True) and (dupli_ob.object.data.name not in meshes_exported):
					mesh_names = exportMesh(lux_context, dupli_ob.object)
					mesh_names_transforms = []
					for mn, mm, mt in mesh_names:
						mesh_names_transforms.append( (mn, mm, dupli_ob.object.matrix_world) )
					if OBJECT_ANALYSIS: print('  %s' % mesh_names_transforms)
					
					dupli_object_mesh_names[dupli_ob.object.name].extend( mesh_names_transforms )
					
					meshes_exported.add(dupli_ob.object.data.name)
				
				if dupli_ob.object.name not in duplis:
					duplis.append(dupli_ob.object.name)
				
				append_objects.extend( dupli_object_mesh_names[dupli_ob.object.name] )
			
			# Export instances second
			if OBJECT_ANALYSIS: print('  exporting instance(s) for %s: %s' % (ob.name, append_objects) )
			exportInstance(lux_context, ob, ob.matrix_world, dupli=True, append_objects=append_objects)
			
			# free object dupli list again. Warning: all dupli objects are INVALID now!
			if OBJECT_ANALYSIS: print(' -> parsed %i dupli objects' % len(ob.dupli_list))
			if ob.dupli_list: 
				ob.free_dupli_list()
		
		if number_psystems > 0:
			if OBJECT_ANALYSIS: print(' -> has %i particle systems' % number_psystems)
			for psys in ob.particle_systems:
				psys_settings = psys.settings
				allowed_particle_states = {'ALIVE'}
				if psys_settings.render_type == 'OBJECT':
					scene.update()
					particle_object = psys_settings.dupli_object
					
					mesh_names = []
					
					# Scan meshes first
					for particle in psys.particles:
						if particle.is_visible and (particle.alive_state in allowed_particle_states):
							if allow_instancing(dupli=True) and (particle_object.data.name not in meshes_exported):
								mesh_names = exportMesh(lux_context, particle_object, scale=[particle.size]*3, log=False)
								meshes_exported.add(particle_object.data.name)
					
					# Export instances second
					for particle in psys.particles:
						if particle.is_visible and (particle.alive_state in allowed_particle_states):
							particle_matrix = mathutils.Matrix.Translation( particle.location )
							particle_matrix *= particle.rotation.to_matrix().to_4x4()
							#particle_matrix *= mathutils.Matrix.Scale(particle.size, 4)
							exportInstance(lux_context, particle_object, particle_matrix, dupli=True, append_objects=mesh_names)
							del particle_matrix
	
	# browse all scene objects for "mesh-convertible" ones
	# skip duplicated objects here
	
	progress_thread = MeshExportProgressThread()
	progress_thread.start(total_objects)
	
	for ob in sel:
		if OBJECT_ANALYSIS: print('Parsing objects pass 2: %s' % ob.name)
		
		if ob.type != 'MESH':
			if OBJECT_ANALYSIS: print(' -> not a MESH')
			continue
		
		# Export only objects which are enabled for render (in the outliner) and visible on a render layer
		if not ob.is_visible(scene) or ob.hide_render:
			if OBJECT_ANALYSIS: print(' -> not visible: %s / %s' % (ob.is_visible(scene), ob.hide_render))
			continue
		
		if ob.parent and ob.parent.is_duplicator:
			if OBJECT_ANALYSIS: print(' -> parent is duplicator')
			continue
		
		# special case for objects with particle system: check if emitter should be rendered
		if len(ob.particle_systems) > 0:
			render_emitter = False
		else:
			render_emitter = True
		
		for psys in ob.particle_systems:
			render_emitter |= psys.settings.use_render_emitter
		
		if OBJECT_ANALYSIS: print(' -> render_emitter: %s' % render_emitter)
			
		# dupli object render rule copied from convertblender.c (blender internal render)
		
		dupli_check = (not ob.is_duplicator or ob.dupli_type == 'DUPLIFRAMES')
		if OBJECT_ANALYSIS: print(' -> dupli_check: %s' % dupli_check)
		ob_not_in_duplis = (ob.name not in duplis)
		if OBJECT_ANALYSIS: print(' -> ob_not_in_duplis: %s' % ob_not_in_duplis)
		if (dupli_check or render_emitter) and ob_not_in_duplis:
			if OBJECT_ANALYSIS: print(' -> checks passed, exporting')
			
			# Find out if referencing external mesh data
			append_objects = []
			if ob.luxrender_object.append_external_mesh:
				lux_context.objectBegin(ob.name)
				ply_params = ParamSet()
				ply_params.add_string('filename', efutil.path_relative_to_export(ob.luxrender_object.external_mesh))
				ply_params.add_bool('smooth', ob.luxrender_object.use_smoothing)
				lux_context.shape('plymesh', ply_params)
				lux_context.objectEnd()
				append_objects.append( (ob.name, ob.active_material, None) )
			
			# Export object instance
			if not ob.data.luxrender_mesh.portal:
				exportInstance(lux_context, ob, ob.matrix_world, dupli=False, append_objects=append_objects)
			
		progress_thread.exported_objects += 1
	
	progress_thread.stop()
	progress_thread.join()
