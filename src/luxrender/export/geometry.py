# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Exporter Framework - LuxRender Plug-in
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
import bpy

from luxrender.module.file_api import Files
from luxrender.export import matrix_to_list

def write_lxo(l, scene):
    '''
    l            pylux.Context
    scene        bpy.types.scene
    
    Iterate over the given scene's objects,
    and export the compatible ones to the context l.
    
    Returns None
    '''
    
    sel = scene.objects
    for ob in sel:
        
        if ob.type in ('LAMP', 'CAMERA', 'EMPTY', 'META', 'ARMATURE'):
            continue
        
        # materials are exported in write_lxm()
        # me = ob.data
        # me_materials = me.materials
        
        me = ob.create_mesh(scene, True, 'RENDER')
        
        if not me:
            continue
        
        l.attributeBegin(comment=ob.name, file=Files.GEOM)
        
        # object translation/rotation/scale 
        l.transform( matrix_to_list(ob.matrix) )
        
        # dummy material for now
        l.material('matte', [
            ('color Kd', [0.7, 0.6, 0.7])
        ])
        
        faces_verts = [f.verts for f in me.faces]
        ffaces = [f for f in me.faces]
        faces_normals = [tuple(f.normal) for f in me.faces]
        verts_normals = [tuple(v.normal) for v in me.verts]
        
        # face indices
        index = 0
        indices = []
        for face in ffaces:
            indices.append(index)
            indices.append(index+1)
            indices.append(index+2)
            if (len(face.verts)==4):
                indices.append(index)
                indices.append(index+2)
                indices.append(index+3)
            index += len(face.verts)
            
        # vertex positions
        points = []
        for face in ffaces:
            for vertex in face.verts:
                v = me.verts[vertex]
                for co in v.co:
                    points.append(co)
                    
        # vertex normals
        normals = []
        for face in ffaces:
            normal = face.normal
            for vertex in face.verts:
                if (face.smooth):
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
        ss = [
            ('integer indices', indices),
            ('point P', points),
            ('normal N', normals),
        ]
        if uv_layer:
            #print(' %s num uvs: %i' % (ob.name, len(uvs)))
            ss.append( ('float uv', uvs) )
            
        l.shape('trianglemesh', ss)
        
        l.attributeEnd()
        
        bpy.data.meshes.remove(me)
