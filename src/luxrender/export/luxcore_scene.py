# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# David Bucciarelli
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
import math

from .. import pyluxcore
from ..outputs import LuxManager, LuxLog
from ..outputs.luxcore_api import ToValidLuxCoreName
from ..export import get_worldscale
from ..export.materials import get_texture_from_scene

class BlenderSceneConverter(object):
	def __init__(self, blScene):
		LuxManager.SetCurrentScene(blScene)

		self.blScene = blScene
		self.lcScene = pyluxcore.Scene()
		self.scnProps = pyluxcore.Properties()
		self.cfgProps = pyluxcore.Properties()
		
		self.materialsCache = set()
		self.texturesCache = set()
	
	def ConvertObjectGeometry(self, obj):
		try:
			mesh_definitions = []

			if obj.hide_render:
				return mesh_definitions

			mesh = obj.to_mesh(self.blScene, True, 'RENDER')
			if mesh is None:
				LuxLog('Cannot create render/export object: %s' % obj.name)
				return mesh_definitions

			mesh.transform(obj.matrix_world)
			mesh.update(calc_tessface = True)

			# Collate faces by mat index
			ffaces_mats = {}
			mesh_faces = mesh.tessfaces
			for f in mesh_faces:
				mi = f.material_index
				if mi not in ffaces_mats.keys():
					ffaces_mats[mi] = []
				ffaces_mats[mi].append(f)
			material_indices = ffaces_mats.keys()

			number_of_mats = len(mesh.materials)
			if number_of_mats > 0:
				iterator_range = range(number_of_mats)
			else:
				iterator_range = [0]

			for i in iterator_range:
				try:
					if i not in material_indices:
						continue

					mesh_name = '%s-%s_m%03d' % (obj.data.name, self.blScene.name, i)

					uv_textures = mesh.tessface_uv_textures
					if len(uv_textures) > 0:
						if uv_textures.active and uv_textures.active.data:
							uv_layer = uv_textures.active.data
					else:
						uv_layer = None

					# Export data
					points = []
					normals = []
					uvs = []
					face_vert_indices = []		# List of face vert indices

					# Caches
					vert_vno_indices = {}		# Mapping of vert index to exported vert index for verts with vert normals
					vert_use_vno = set()		# Set of vert indices that use vert normals

					vert_index = 0				# Exported vert index
					for face in ffaces_mats[i]:
						fvi = []
						for j, vertex in enumerate(face.vertices):
							v = mesh.vertices[vertex]

							if face.use_smooth:
								if uv_layer:
									vert_data = (v.co[:], v.normal[:], uv_layer[face.index].uv[j][:])
								else:
									vert_data = (v.co[:], v.normal[:], tuple())

								if vert_data not in vert_use_vno:
									vert_use_vno.add(vert_data)

									points.append(vert_data[0])
									normals.append(vert_data[1])
									uvs.append(vert_data[2])

									vert_vno_indices[vert_data] = vert_index
									fvi.append(vert_index)

									vert_index += 1
								else:
									fvi.append(vert_vno_indices[vert_data])

							else:
								# all face-vert-co-no are unique, we cannot
								# cache them
								points.append(v.co[:])
								normals.append(face.normal[:])
								if uv_layer:
									uvs.append(uv_layer[face.index].uv[j][:])

								fvi.append(vert_index)

								vert_index += 1

						# For Lux, we need to triangulate quad faces
						face_vert_indices.append(tuple(fvi[0:3]))
						if len(fvi) == 4:
							face_vert_indices.append((fvi[0], fvi[2], fvi[3]))

					del vert_vno_indices
					del vert_use_vno

					# Define a new mesh
					lcObjName = ToValidLuxCoreName(mesh_name)
					self.lcScene.DefineMesh('Mesh-' + lcObjName, points, face_vert_indices, normals, uvs if uv_layer else None, None, None)				
					mesh_definitions.append((lcObjName, i))

				except Exception as err:
					LuxLog('Mesh export failed, skipping this mesh:\n%s' % err)

			del ffaces_mats
			bpy.data.meshes.remove(mesh)

			return mesh_definitions;

		except Exception as err:
			LuxLog('Object export failed, skipping this object:\n%s' % err)
			return []

	def ConvertMapping(self, prefix, texture):
		luxMapping = getattr(texture.luxrender_texture, 'luxrender_tex_mapping')
		
		if luxMapping.type == 'uv':
			self.scnProps.Set(pyluxcore.Property(prefix + '.mapping.type', ['uvmapping2d']))
			self.scnProps.Set(pyluxcore.Property(prefix + '.mapping.uvscale', [luxMapping.uscale, luxMapping.vscale * - 1.0]))
			if luxMapping.center_map ==  False:
				self.scnProps.Set(pyluxcore.Property(prefix + '.mapping.uvdelta', [luxMapping.udelta, luxMapping.vdelta + 1.0]))
			else:
				self.scnProps.Set(pyluxcore.Property(prefix + '.mapping.uvdelta', [
					luxMapping.udelta + 0.5 * (1.0 - luxMapping.uscale), luxMapping.vdelta * - 1.0 + 1.0 - (0.5 * (1.0 - luxMapping.vscale))]))
		else:
			raise Exception('Unsupported mapping for texture: ' + texture.name)

	def ConvertTexture(self, texture):
		texType = texture.luxrender_texture.type

		if texType != 'BLENDER':
			texName = ToValidLuxCoreName(texture.name)
			luxTex = getattr(texture.luxrender_texture, 'luxrender_tex_' + texType)

			prefix = 'scene.textures.' + texName
			####################################################################
			# Imagemap
			####################################################################
			if texType == 'imagemap':
				self.scnProps.Set(pyluxcore.Property(prefix + '.type', ['imagemap']))
				self.scnProps.Set(pyluxcore.Property(prefix + '.file', [luxTex.filename]))
				self.scnProps.Set(pyluxcore.Property(prefix + '.gamma', [float(luxTex.gamma)]))
				self.scnProps.Set(pyluxcore.Property(prefix + '.gain', [float(luxTex.gain)]))
				self.ConvertMapping(prefix, texture)
			else:
				raise Exception('Unknown type ' + texType + 'for texture: ' + texture.name)
			
			self.texturesCache.add(texName)
			return texName
		
		raise Exception('Unknown texture type: ' + texture.name)

	def ConvertMaterialChannel(self, luxMaterial, materialChannel, variant):
		if getattr(luxMaterial, materialChannel + '_use' + variant + 'texture'):
			texName = getattr(luxMaterial, '%s_%stexturename' % (materialChannel, variant))
			validTexName = ToValidLuxCoreName(texName)
			# Check if it is an already defined texture
			if validTexName in self.texturesCache:
				return validTexName
			LuxLog('Texture: ' + texName)
			
			texture = get_texture_from_scene(self.blScene, texName)
			
			if texture != False:
				return self.ConvertTexture(texture) 
		else:
			if variant == 'float':
				return str(getattr(luxMaterial, materialChannel + '_floatvalue'))
			elif variant == 'color':
				return ' '.join(str(i) for i in getattr(luxMaterial, materialChannel + '_color'))
			elif variant == 'fresnel':
				return str(getattr(property_group, materialChannel + '_fresnelvalue'))

		raise Exception('Unknown texture in channel' + materialChannel + ' for material ' + material.luxrender_material.type)

	def ConvertMaterial(self, material):
		try:
			if material is None:
				return 'LUXBLEND_LUXCORE_CLAY_MATERIAL'

			matIsTransparent = False
			if material.type in ['glass', 'glass2', 'null']:
				matIsTransparent == True

			if self.blScene.luxrender_testing.clay_render and matIsTransparent == False:
				return 'LUXBLEND_LUXCORE_CLAY_MATERIAL'

			matName = ToValidLuxCoreName(material.name)
			# Check if it is an already defined material
			if matName in self.materialsCache:
				return matName
			LuxLog('Material: ' + material.name)

			matType = material.luxrender_material.type
			luxMat = getattr(material.luxrender_material, 'luxrender_mat_' + matType)
			
			prefix = 'scene.materials.' + matName
			####################################################################
			# Matte
			####################################################################
			if matType == 'matte':
				self.scnProps.Set(pyluxcore.Property(prefix + '.type', ['matte']))
				self.scnProps.Set(pyluxcore.Property(prefix + '.kd', self.ConvertMaterialChannel(luxMat, 'Kd', 'color')))
			else:
				return 'LUXBLEND_LUXCORE_CLAY_MATERIAL'

			# LuxCore specific material settings
			if material.luxcore_material.id != -1:
				self.scnProps.Set(pyluxcore.Property(prefix + '.id', [material.luxcore_material.id]))
			if material.luxcore_material.emission_id != -1:
				self.scnProps.Set(pyluxcore.Property(prefix + '.emission.id', [material.luxcore_material.light_id]))
				
			self.scnProps.Set(pyluxcore.Property(prefix + '.samples', [material.luxcore_material.samples]))
			self.scnProps.Set(pyluxcore.Property(prefix + '.emission.samples', [material.luxcore_material.emission_samples]))
			self.scnProps.Set(pyluxcore.Property(prefix + '.bumpsamplingdistance', [material.luxcore_material.bumpsamplingdistance]))
			
			self.scnProps.Set(pyluxcore.Property(prefix + '.visibility.indirect.diffuse.enable', [material.luxcore_material.visibility_indirect_diffuse_enable]))
			self.scnProps.Set(pyluxcore.Property(prefix + '.visibility.indirect.glossy.enable', [material.luxcore_material.visibility_indirect_glossy_enable]))
			self.scnProps.Set(pyluxcore.Property(prefix + '.visibility.indirect.specular.enable', [material.luxcore_material.visibility_indirect_specular_enable]))
			
			self.materialsCache.add(matName)
			return matName
		except Exception as err:
			LuxLog('Material export failed, skipping material: %s\n%s' % (material.name, err))
			import traceback
			traceback.print_exc()
			return 'LUXBLEND_LUXCORE_CLAY_MATERIAL'

	def ConvertObject(self, obj):
		########################################################################
		# Convert the object geometry
		########################################################################

		meshDefinitions = []
		meshDefinitions.extend(self.ConvertObjectGeometry(obj))

		for meshDefinition in meshDefinitions:
			objName = meshDefinition[0]
			objMatIndex = meshDefinition[1]
			
			####################################################################
			# Convert the material
			####################################################################
			
			try:
				objMat = obj.material_slots[objMatIndex].material
			except IndexError:
				objMat = None
				LuxLog('WARNING: material slot %d on object "%s" is unassigned!' % (objMatIndex + 1, obj.name))
			
			objMatName = self.ConvertMaterial(objMat)

			####################################################################
			# Create the mesh
			####################################################################
			
			self.scnProps.Set(pyluxcore.Property('scene.objects.' + objName + '.material', [objMatName]))
			self.scnProps.Set(pyluxcore.Property('scene.objects.' + objName + '.ply', ['Mesh-' + objName]))
	
	def ConvertCamera(self, imageWidth = None, imageHeight = None):
		blCamera = self.blScene.camera
		blCameraData = blCamera.data
		luxCamera = blCameraData.luxrender_camera

		if (not imageWidth is None) and (not imageHeight is None):
			xr = imageWidth
			yr = imageHeight
		else:
			xr, yr = luxCamera.luxrender_film.resolution(self.blScene)

		lookat = luxCamera.lookAt(blCamera)
		orig = list(lookat[0:3])
		target = list(lookat[3:6])
		up = list(lookat[6:9])
		self.scnProps.Set(pyluxcore.Property('scene.camera.lookat.orig', orig))
		self.scnProps.Set(pyluxcore.Property('scene.camera.lookat.target', target))
		self.scnProps.Set(pyluxcore.Property('scene.camera.lookat.up', up))

		if blCameraData.type == 'PERSP' and luxCamera.type == 'perspective':
			self.scnProps.Set(pyluxcore.Property('scene.camera.lookat.fieldofview', [math.degrees(blCameraData.angle)]))
		
		self.scnProps.Set(pyluxcore.Property("scene.camera.screenwindow", luxCamera.screenwindow(xr, yr, self.blScene, blCameraData)));
		
		if luxCamera.use_dof:
			# Do not world-scale this, it is already in meters !
			self.scnProps.Set(pyluxcore.Property("scene.camera.lensradius", (blCameraData.lens / 1000.0) / (2.0 * luxCamera.fstop)));
		
		ws = get_worldscale(as_scalematrix = False)
		
		if luxCamera.use_dof:
			if blCameraData.dof_object is not None:
				self.scnProps.Set(pyluxcore.Property("scene.camera.focaldistance", ws * ((scene.camera.location - blCameraData.dof_object.location).length)));
			elif blCameraData.dof_distance > 0:
				self.scnProps.Set(pyluxcore.Property("scene.camera.focaldistance"), ws * blCameraData.dof_distance);
			
		if luxCamera.use_clipping:
			self.scnProps.Set(pyluxcore.Property("scene.camera.cliphither", ws * blCameraData.clip_start));
			self.scnProps.Set(pyluxcore.Property("scene.camera.clipyon", ws * blCameraData.clip_end));

	def ConvertEngineSettings(self):
		engine = self.blScene.luxcore_enginesettings.renderengine_type
		if len(engine) == 0:
			engine = 'PATHCPU'
		self.cfgProps.Set(pyluxcore.Property('renderengine.type', [engine]))
		
		if engine == 'BIASPATHCPU' or engine == 'BIASPATHOCL':
			self.cfgProps.Set(pyluxcore.Property('tile.size', [self.blScene.luxcore_enginesettings.tile_size]))
			self.cfgProps.Set(pyluxcore.Property('tile.multipass.enable', [self.blScene.luxcore_enginesettings.tile_multipass_enable]))
			self.cfgProps.Set(pyluxcore.Property('tile.multipass.convergencetest.threshold', [self.blScene.luxcore_enginesettings.tile_multipass_convergencetest_threshold]))
			self.cfgProps.Set(pyluxcore.Property('tile.multipass.convergencetest.threshold.reduction', [self.blScene.luxcore_enginesettings.tile_multipass_convergencetest_threshold_reduction]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.sampling.aa.size', [self.blScene.luxcore_enginesettings.biaspath_sampling_aa_size]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.sampling.diffuse.size', [self.blScene.luxcore_enginesettings.biaspath_sampling_diffuse_size]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.sampling.glossy.size', [self.blScene.luxcore_enginesettings.biaspath_sampling_glossy_size]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.sampling.specular.size', [self.blScene.luxcore_enginesettings.biaspath_sampling_specular_size]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.pathdepth.total', [self.blScene.luxcore_enginesettings.biaspath_pathdepth_total]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.pathdepth.diffuse', [self.blScene.luxcore_enginesettings.biaspath_pathdepth_diffuse]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.pathdepth.glossy', [self.blScene.luxcore_enginesettings.biaspath_pathdepth_glossy]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.pathdepth.specular', [self.blScene.luxcore_enginesettings.biaspath_pathdepth_specular]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.clamping.radiance.maxvalue', [self.blScene.luxcore_enginesettings.biaspath_clamping_radiance_maxvalue]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.clamping.pdf.value', [self.blScene.luxcore_enginesettings.biaspath_clamping_pdf_value]))
			self.cfgProps.Set(pyluxcore.Property('biaspath.lights.samplingstrategy.type', [self.blScene.luxcore_enginesettings.biaspath_lights_samplingstrategy_type]))
		
		# CPU settings
		self.cfgProps.Set(pyluxcore.Property('native.threads.count', [self.blScene.luxcore_enginesettings.native_threads_count]))
		
		# OpenCL settings
		if len(self.blScene.luxcore_enginesettings.luxcore_opencl_devices) > 0:
			dev_string = ''
			for dev_index in range(len(self.blScene.luxcore_enginesettings.luxcore_opencl_devices)):
				dev = self.blScene.luxcore_enginesettings.luxcore_opencl_devices[dev_index]
				dev_string += '1' if dev.opencl_device_enabled else '0'

			self.cfgProps.Set(pyluxcore.Property('opencl.devices.select', [dev_string]))
		
		# Accelerator settings
		self.cfgProps.Set(pyluxcore.Property('accelerator.instances.enable', [False]))

	def Convert(self, imageWidth = None, imageHeight = None):
		########################################################################
		# Convert camera definition
		########################################################################

		self.ConvertCamera(imageWidth = imageWidth, imageHeight = imageHeight)

		########################################################################
		# Add a sky definition
		########################################################################

		self.scnProps.Set(pyluxcore.Property('scene.lights.skylight.type', ['sky']))
		self.scnProps.Set(pyluxcore.Property('scene.lights.skylight.gain', [1.0, 1.0, 1.0]))

		########################################################################
		# Add dummy material
		########################################################################

		self.scnProps.Set(pyluxcore.Property('scene.materials.LUXBLEND_LUXCORE_CLAY_MATERIAL.type', ['matte']))
		self.scnProps.Set(pyluxcore.Property('scene.materials.LUXBLEND_LUXCORE_CLAY_MATERIAL.kd', [0.7, 0.7, 0.7]))

		########################################################################
		# Convert all objects
		########################################################################

		for obj in self.blScene.objects:
			LuxLog('Object: %s' % obj.name)
			self.ConvertObject(obj)

		self.lcScene.Parse(self.scnProps)

		########################################################################
		# Create the configuration
		########################################################################

		self.ConvertEngineSettings()

		# Film
		if (not imageWidth is None) and (not imageHeight is None):
			filmWidth = imageWidth
			filmHeight = imageHeight
		else:
			filmWidth, filmHeight = self.blScene.camera.data.luxrender_camera.luxrender_film.resolution(self.blScene)

		self.cfgProps.Set(pyluxcore.Property('film.width', [filmWidth]))
		self.cfgProps.Set(pyluxcore.Property('film.height', [filmHeight]))

		# Image Pipeline
		self.cfgProps.Set(pyluxcore.Property('film.imagepipeline.0.type', ['TONEMAP_AUTOLINEAR']))
		self.cfgProps.Set(pyluxcore.Property('film.imagepipeline.1.type', ['GAMMA_CORRECTION']))
		self.cfgProps.Set(pyluxcore.Property('film.imagepipeline.1.value', [2.2]))

		# Pixel Filter
		self.cfgProps.Set(pyluxcore.Property('film.filter.type', ['MITCHELL_SS']))

		# Sampler
		self.cfgProps.Set(pyluxcore.Property('sampler.type', ['RANDOM']))

		self.lcConfig = pyluxcore.RenderConfig(self.cfgProps, self.lcScene)

		return self.lcConfig