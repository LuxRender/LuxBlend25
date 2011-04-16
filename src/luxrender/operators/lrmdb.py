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
import bpy, blf

from .. import LuxRenderAddon
from ..outputs import LuxLog, LuxManager
from ..export import materials as export_materials

from .lrmdb_lib import lrmdb_client

class LrmdbActionButton(object):
	action_counter = 0
	@staticmethod
	def action_id():
		LrmdbActionButton.action_counter += 1
		return LrmdbActionButton.action_counter
	
	def __init__(self, label, callback=None, callback_args=tuple()):
		self.aid = LrmdbActionButton.action_id()
		self.label = label
		self.callback = callback
		self.callback_args = callback_args
	
	def execute(self, context):
		self.callback( context, *self.callback_args )

@LuxRenderAddon.addon_register_class
class LUXRENDER_OT_lrmdb_login(bpy.types.Operator):
	"""Log in to the LuxRender Materials Database"""
	
	bl_idname = 'luxrender.lrmdb_login'
	bl_label  = 'Log in to LRMDB'
	
	username = bpy.props.StringProperty(name='Username:')
	password = bpy.props.StringProperty(name='Password:')
	
	def execute(self, context):
		if self.properties.username and self.properties.password:
			try:
				s = lrmdb_client.server_instance()
				li = s.user.login(self.properties.username, self.properties.password)
				if not li:
					lrmdb_client.loggedin = False
					lrmdb_client.username = ''
					self.report({'ERROR'}, 'Login failure')
				else:
					lrmdb_client.loggedin = True
					lrmdb_client.username = self.properties.username
				return {'FINISHED'}
			except Exception as err:
				LuxLog('LRMDB ERROR: %s' % err)
				return {'CANCELLED'}
		else:
			self.report({'ERROR'}, 'Must supply both username and password')
			return {'CANCELLED'}
	
	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_props_dialog(self)

@LuxRenderAddon.addon_register_class
class LUXRENDER_OT_lrmdb_logout(bpy.types.Operator):
	"""Log out of the LuxRender Materials Database"""
	
	bl_idname = 'luxrender.lrmdb_logout'
	bl_label  = 'Log out of LRMDB'
	
	def execute(self, context):
		try:
			s = lrmdb_client.server_instance()
			li = s.user.logout()
			if not li:
				self.report({'ERROR'}, 'Logout failure')
			lrmdb_client.reset()
			return {'FINISHED'}
		except Exception as err:
			LuxLog('LRMDB ERROR: %s' % err)
			return {'CANCELLED'}

@LuxRenderAddon.addon_register_class
class LUXRENDER_OT_lrmdb(bpy.types.Operator):
	"""Start the LuxRender Materials Database Interface"""
	
	bl_idname = 'luxrender.lrmdb'
	bl_label  = 'Start LRMDB'
	
	_active = False
	
	actions = []
	
	invoke_action_id = bpy.props.IntProperty(default=0)
	
	def execute(self, context):
		try:
			aid = self.properties.invoke_action_id
			
			if aid == -1:
				# Activate panel
				LUXRENDER_OT_lrmdb._active = True
				self.show_category_list(context)
			if aid == -2:
				# Deactivate panel
				LUXRENDER_OT_lrmdb._active = False
			
			# Otherwise look for action id in current list
			for action in LUXRENDER_OT_lrmdb.actions:
				if action.aid == aid:
					action.execute(context)
			
			return {'FINISHED'}
		except Exception as err:
			self.report({'ERROR'}, '%s' % err)
			LuxLog('LRMDB ERROR: %s' % err)
			return {'CANCELLED'}
	
	def select_material(self, context, mat_id):
		#LuxLog('Chose material %s' % mat_id)
		
		if not context.active_object:
			LuxLog('WARNING: Select an object!')
			return
		if not context.active_object.active_material:
			LuxLog('WARNING: Selected object does not have active material')
			return
		
		try:
			context.area.tag_redraw()
			s = lrmdb_client.server_instance()
			md = s.material.get.data(mat_id)
		except Exception as err:
			LuxLog('LRMDB ERROR: Cannot get data: %s' % err)
			LUXRENDER_OT_lrmdb._active = False
			return
		
		try:
			context.active_object.active_material.luxrender_material.load_lbm2(
				context,
				md,
				context.active_object.active_material,
				context.active_object
			)
			
			for a in context.screen.areas:
				a.tag_redraw()
		except KeyError as err:
			LuxLog('LRMDB ERROR: Bad material data')
	
	def show_category_items(self, context, cat_id, cat_name):
		#LuxLog('Chose category %s' % cat_id)
		try:
			context.area.tag_redraw()
			s = lrmdb_client.server_instance()
			ci = s.category.item(cat_id)
		except Exception as err:
			LuxLog('LRMDB ERROR: Cannot get data: %s' % err)
			LUXRENDER_OT_lrmdb._active = False
			return
		
		#LuxLog(ci)
		
		if len(ci) > 0:
			self.reset_actions()
			
			LUXRENDER_OT_lrmdb.actions.append(
				LrmdbActionButton(
					'Category "%s"' % cat_name
				)
			)
			
			for mat_id, mat_header in ci.items():
				if mat_header['published'] == 1 and mat_header['type'] == 'Material':
					LUXRENDER_OT_lrmdb.actions.append(
						LrmdbActionButton(
							mat_header['name'],
							self.select_material,
							(mat_id,)
						)
					)
			
			self.draw_back_link()
	
	def show_category_list(self, context):
		try:
			context.area.tag_redraw()
			s = lrmdb_client.server_instance()
			ct = s.category.tree()
			lrmdb_client.check_login()
		except Exception as err:
			LuxLog('LRMDB ERROR: Cannot get data: %s' % err)
			LUXRENDER_OT_lrmdb._active = False
			return
		
		def display_category(ctg):
			for cat_id, cat in ctg.items():
				if cat['name'] != 'incoming':
					if cat['items'] > 0:
						LUXRENDER_OT_lrmdb.actions.append(
							LrmdbActionButton(
								cat['name'] + ' (%s)' % cat['items'],
								self.show_category_items,
								(cat_id, cat['name'])
							)
						)
					if 'subcategories' in cat.keys():
						display_category(cat['subcategories'])
		
		if len(ct) > 0:
			self.reset_actions()
			LUXRENDER_OT_lrmdb.actions.append(
				LrmdbActionButton(
					'Categories',
				)
			)
			display_category(ct)
	
	def begin_login(self, context):
		bpy.ops.luxrender.lrmdb_login('INVOKE_DEFAULT')
	
	def end_login(self, context):
		bpy.ops.luxrender.lrmdb_logout()
		self.reset_actions()
		LUXRENDER_OT_lrmdb._active = False
	
	def reset_actions(self):
		LUXRENDER_OT_lrmdb.actions = []
		self.draw_loggedin()
	
	def draw_loggedin(self):
		if lrmdb_client.loggedin:
			LUXRENDER_OT_lrmdb.actions.extend([
				LrmdbActionButton(
					'Logged In as: %s' % lrmdb_client.username,
				),
				LrmdbActionButton(
					'Log out',
					self.end_login
				)
			])
		else:
			LUXRENDER_OT_lrmdb.actions.extend([
				LrmdbActionButton(
					'Log In',
					self.begin_login
				),
			])
	
	def draw_back_link(self):
		LUXRENDER_OT_lrmdb.actions.append(
			LrmdbActionButton(
				'< Back to categories',
				self.show_category_list
			)
		)
	
	@classmethod
	def poll(cls, context):
		return context.scene.render.engine == LuxRenderAddon.BL_IDNAME

@LuxRenderAddon.addon_register_class
class LUXRENDER_OT_upload_material(bpy.types.Operator):
	bl_idname = 'luxrender.lrmdb_upload'
	bl_label = 'Upload material to LRMDB'
	
	def execute(self, context):
		try:
			blender_mat = context.material
			luxrender_mat = context.material.luxrender_material
			
			LM = LuxManager("material_save", 'LBM2')
			LuxManager.SetActive(LM)
			LM.SetCurrentScene(context.scene)
			
			material_context = LM.lux_context
			
			export_materials.ExportedMaterials.clear()
			export_materials.ExportedTextures.clear()
			
			# This causes lb25 to embed all external data ...
			context.scene.luxrender_engine.is_saving_lbm2 = True
			
			# Include interior/exterior for this material
			for volume in context.scene.luxrender_volumes.volumes:
				if volume.name in [luxrender_mat.Interior_volume, luxrender_mat.Exterior_volume]:
					material_context.makeNamedVolume( volume.name, *volume.api_output(material_context) )
			
			luxrender_mat.export(material_context, blender_mat)
			
			material_context.set_material_name(blender_mat.name)
			material_context.update_material_metadata(
				interior=luxrender_mat.Interior_volume,
				exterior=luxrender_mat.Exterior_volume
			)
			
			result = material_context.upload(lrmdb_client)
			if result:
				self.report({'INFO'},'Upload successful!')
			else:
				self.report({'WARNING'},'Upload failed!')
			
			# .. and must be reset!
			context.scene.luxrender_engine.is_saving_lbm2 = False
			
			LM.reset()
			LuxManager.SetActive(None)
			
			return {'FINISHED'}
			
		except Exception as err:
			self.report({'ERROR'}, 'Cannot save: %s' % err)
			return {'CANCELLED'}
