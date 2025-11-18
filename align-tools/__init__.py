# SPDX-FileCopyrightText: 2009-2010 gabhead, Lell, Anfeo.
#
# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "Align Tools (Advanced)",
    "author": "gabhead, Lell, Anfeo, updated by ChatGPT",
    "version": (1, 2, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Item > Align Tools",
    "description": "Advanced alignment tools for objects, origins and cursor",
    "category": "Object",
}

import bpy
from bpy.types import (
    Operator,
    Panel,
    AddonPreferences,
)
from bpy.props import (
    EnumProperty,
    BoolProperty,
    FloatVectorProperty,
    StringProperty,
)
from mathutils import Vector


# ------------------------------------------------------------------------
# Simple Align Defs
# ------------------------------------------------------------------------

def LocAll(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.matrix_world.translation = act.matrix_world.translation.copy()
        obj.rotation_euler = act.rotation_euler.copy()


def LocX(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.matrix_world.translation.x = act.matrix_world.translation.x


def LocY(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.matrix_world.translation.y = act.matrix_world.translation.y


def LocZ(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.matrix_world.translation.z = act.matrix_world.translation.z


def RotAll(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.rotation_euler = act.rotation_euler.copy()


def RotX(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.rotation_euler.x = act.rotation_euler.x


def RotY(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.rotation_euler.y = act.rotation_euler.y


def RotZ(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.rotation_euler.z = act.rotation_euler.z


def ScaleAll(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.scale = act.scale.copy()


def ScaleX(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.scale.x = act.scale.x


def ScaleY(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.scale.y = act.scale.y


def ScaleZ(context):
    act = context.active_object
    if act is None:
        return
    for obj in context.selected_objects:
        obj.scale.z = act.scale.z


# ------------------------------------------------------------------------
# Advanced Align Core
# ------------------------------------------------------------------------

def align_function(context,
                   subject, active_too, consistent, self_or_active,
                   loc_x, loc_y, loc_z, ref1, ref2, loc_offset,
                   rot_x, rot_y, rot_z, rot_offset, apply_rot,
                   scale_x, scale_y, scale_z, scale_offset, apply_scale,
                   fit_x, fit_y, fit_z, apply_dim):

    sel_obj = context.selected_objects
    act_obj = context.active_object

    if act_obj is None or not sel_obj:
        return

    # Respeita os toggles "Apply"
    if not apply_rot:
        rot_x = rot_y = rot_z = False
    if not apply_scale:
        scale_x = scale_y = scale_z = False
    if not apply_dim:
        fit_x = fit_y = fit_z = False

    # ---------------- Helpers ---------------- #

    def get_reference_points(obj, space):
        """Retorna [minX, centerX, maxX, minY, centerY, maxY, minZ, centerZ, maxZ]"""
        me = getattr(obj, "data", None)
        co_list = []
        ok = False

        if space == "global":
            obj_mtx = obj.matrix_world
            if obj.type == 'MESH' and me and len(me.vertices) > 0:
                ok = True
                for p in me.vertices:
                    co_list.append(obj_mtx @ p.co)

            elif obj.type in {'CURVE', 'SURFACE', 'FONT'} and me and len(getattr(me, "splines", [])) > 0:
                ok = True
                for s in me.splines:
                    if getattr(s, "bezier_points", None):
                        for p in s.bezier_points:
                            co_list.append(obj_mtx @ p.co)
                    if getattr(s, "points", None):
                        for p in s.points:
                            co_list.append(obj_mtx @ p.co)

        elif space == "local":
            if obj.type == 'MESH' and me and len(me.vertices) > 0:
                ok = True
                for p in me.vertices:
                    co_list.append(p.co)

            elif obj.type in {'CURVE', 'SURFACE', 'FONT'} and me and len(getattr(me, "splines", [])) > 0:
                ok = True
                for s in me.splines:
                    if getattr(s, "bezier_points", None):
                        for p in s.bezier_points:
                            co_list.append(p.co)
                    if getattr(s, "points", None):
                        for p in s.points:
                            co_list.append(p.co)

        if ok and co_list:
            max_x = min_x = co_list[0].x
            max_y = min_y = co_list[0].y
            max_z = min_z = co_list[0].z

            for v in co_list:
                x, y, z = v.x, v.y, v.z
                if x > max_x:
                    max_x = x
                if x < min_x:
                    min_x = x
                if y > max_y:
                    max_y = y
                if y < min_y:
                    min_y = y
                if z > max_z:
                    max_z = z
                if z < min_z:
                    min_z = z
        else:
            a = obj.matrix_world.translation
            min_x = max_x = a.x
            min_y = max_y = a.y
            min_z = max_z = a.z

        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        center_z = (min_z + max_z) * 0.5

        return [
            min_x, center_x, max_x,
            min_y, center_y, max_y,
            min_z, center_z, max_z,
        ]

    def get_sel_ref(ref_co, objects):
        """Min e max da seleção em torno de um ponto interno"""
        max_x = ref_co.x
        min_x = ref_co.x
        max_y = ref_co.y
        min_y = ref_co.y
        max_z = ref_co.z
        min_z = ref_co.z

        for obj in objects:
            ref_points = get_reference_points(obj, "global")
            if ref_co.x < ref_points[0]:
                min_x = ref_points[0]
            if ref_co.x > ref_points[2]:
                max_x = ref_points[2]
            if ref_co.y < ref_points[3]:
                min_y = ref_points[3]
            if ref_co.y > ref_points[5]:
                max_y = ref_points[5]
            if ref_co.z < ref_points[6]:
                min_z = ref_points[6]
            if ref_co.z > ref_points[8]:
                max_z = ref_points[8]

        sel_min = Vector((min_x, min_y, min_z))
        sel_max = Vector((max_x, max_y, max_z))
        return sel_min, sel_max

    def find_ref2_co(target_obj):
        """Coordenada de destino (Min/Center/Pivot/Max/Cursor) do ativo"""
        if ref2 == "4":
            return context.scene.cursor.location.copy()

        ref_points = get_reference_points(target_obj, "global")

        if ref2 == "0":  # Min
            return Vector((ref_points[0], ref_points[3], ref_points[6]))
        elif ref2 == "1":  # Center
            return Vector((ref_points[1], ref_points[4], ref_points[7]))
        elif ref2 == "2":  # Pivot
            return target_obj.matrix_world.translation.copy()
        elif ref2 == "3":  # Max
            return Vector((ref_points[2], ref_points[5], ref_points[8]))
        else:
            return target_obj.matrix_world.translation.copy()

    def point_in_selection(active, objects):
        """Pega um ponto qualquer dentro da seleção (primeiro vértice/point que achar)"""
        ref_ob = None
        ref_co = None

        for o in objects:
            if o == active:
                continue
            ref_ob = o
            obj_mtx = o.matrix_world
            me = getattr(o, "data", None)

            if o.type == 'MESH' and me and len(me.vertices) > 0:
                ref_co = obj_mtx @ me.vertices[0].co
                break
            elif o.type in {'CURVE', 'SURFACE', 'FONT'} and me and len(getattr(me, "splines", [])) > 0:
                for s in me.splines:
                    if getattr(s, "bezier_points", None):
                        ref_co = obj_mtx @ s.bezier_points[0].co
                        break
                    if getattr(s, "points", None):
                        ref_co = obj_mtx @ s.points[0].co
                        break
                if ref_co is not None:
                    break

        if ref_co is None:
            if ref_ob is not None:
                ref_co = ref_ob.matrix_world.translation.copy()
            else:
                ref_co = active.matrix_world.translation.copy()

        return ref_co

    def find_new_rotation(obj):
        if rot_x:
            obj.rotation_euler.x = act_obj.rotation_euler.x + rot_offset[0]
        if rot_y:
            obj.rotation_euler.y = act_obj.rotation_euler.y + rot_offset[1]
        if rot_z:
            obj.rotation_euler.z = act_obj.rotation_euler.z + rot_offset[2]

    def find_new_scale(obj):
        if scale_x:
            obj.scale.x = act_obj.scale.x + scale_offset[0]
        if scale_y:
            obj.scale.y = act_obj.scale.y + scale_offset[1]
        if scale_z:
            obj.scale.z = act_obj.scale.z + scale_offset[2]

    def find_new_dimensions(obj, ref_dim):
        """Ref_dim = dimensão alvo (Vector) do ativo"""
        ref_points = get_reference_points(obj, "local")
        dim = Vector((
            ref_points[2] - ref_points[0],
            ref_points[5] - ref_points[3],
            ref_points[8] - ref_points[6],
        ))

        ratio_x = dim.x / ref_dim.x if ref_dim.x != 0 else 1.0
        ratio_y = dim.y / ref_dim.y if ref_dim.y != 0 else 1.0
        ratio_z = dim.z / ref_dim.z if ref_dim.z != 0 else 1.0

        dx = Vector((0.0, 0.0, 0.0))
        dy = Vector((0.0, 0.0, 0.0))
        dz = Vector((0.0, 0.0, 0.0))

        if fit_x and ratio_x != 0:
            dx = ((1.0 - ratio_x) * 0.5) * dim
        if fit_y and ratio_y != 0:
            dy = ((1.0 - ratio_y) * 0.5) * dim
        if fit_z and ratio_z != 0:
            dz = ((1.0 - ratio_z) * 0.5) * dim

        obj.location += dx + dy + dz

        if fit_x and ratio_x != 0:
            obj.scale.x *= 1.0 / ratio_x
        if fit_y and ratio_y != 0:
            obj.scale.y *= 1.0 / ratio_y
        if fit_z and ratio_z != 0:
            obj.scale.z *= 1.0 / ratio_z

    def find_new_coord(obj, ref2_co):
        """Alinha o objeto ao ref2_co, usando Min/Center/Pivot/Max + offset"""
        ref_points = get_reference_points(obj, "global")
        obj_min = Vector((ref_points[0], ref_points[3], ref_points[6]))
        obj_max = Vector((ref_points[2], ref_points[5], ref_points[8]))
        obj_center = (obj_min + obj_max) * 0.5
        obj_pivot = obj.matrix_world.translation.copy()

        if ref1 == "0":
            source = obj_min + loc_offset
        elif ref1 == "1":
            source = obj_center + loc_offset
        elif ref1 == "2":
            source = obj_pivot + loc_offset
        elif ref1 == "3":
            source = obj_max + loc_offset
        else:
            source = obj_pivot + loc_offset

        translate = ref2_co - source

        if loc_x:
            obj.location.x += translate.x
        if loc_y:
            obj.location.y += translate.y
        if loc_z:
            obj.location.z += translate.z

    # ---------------- Lógica principal ---------------- #

    if subject == "0":  # Objects
        ref2_co = find_ref2_co(act_obj)

        if consistent:
            # Move a seleção como bloco
            ref_co = point_in_selection(act_obj, sel_obj)
            sel_min, sel_max = get_sel_ref(ref_co, sel_obj)
            sel_center = sel_min + (sel_max - sel_min) * 0.5

            if ref1 == "0":
                translate = ref2_co - (sel_min + loc_offset)
            elif ref1 == "1":
                translate = ref2_co - (sel_center + loc_offset)
            elif ref1 == "3":
                translate = ref2_co - (sel_max + loc_offset)
            else:
                translate = ref2_co - (sel_center + loc_offset)

            for obj in sel_obj:
                if obj != act_obj or (active_too and obj == act_obj):
                    if loc_x:
                        obj.location.x += translate.x
                    if loc_y:
                        obj.location.y += translate.y
                    if loc_z:
                        obj.location.z += translate.z

        else:
            # Trata objeto a objeto
            for obj in sel_obj:
                if obj == act_obj:
                    continue

                if rot_x or rot_y or rot_z:
                    find_new_rotation(obj)

                if fit_x or fit_y or fit_z:
                    ref_points = get_reference_points(act_obj, "local")
                    dim = Vector((
                        ref_points[2] - ref_points[0],
                        ref_points[5] - ref_points[3],
                        ref_points[8] - ref_points[6],
                    ))
                    find_new_dimensions(obj, dim)

                if scale_x or scale_y or scale_z:
                    find_new_scale(obj)

                if loc_x or loc_y or loc_z:
                    find_new_coord(obj, ref2_co)

            if active_too:
                if rot_x or rot_y or rot_z:
                    find_new_rotation(act_obj)

                if fit_x or fit_y or fit_z:
                    ref_points = get_reference_points(act_obj, "local")
                    dim = Vector((
                        ref_points[2] - ref_points[0],
                        ref_points[5] - ref_points[3],
                        ref_points[8] - ref_points[6],
                    ))
                    find_new_dimensions(act_obj, dim)

                if scale_x or scale_y or scale_z:
                    find_new_scale(act_obj)

                if loc_x or loc_y or loc_z:
                    find_new_coord(act_obj, ref2_co)

    elif subject == "1":  # "Pivot" – aqui estou interpretando como alinhar a origem (location)
        ref2_co = find_ref2_co(act_obj)

        for obj in sel_obj:
            if obj != act_obj or active_too:
                if loc_x:
                    obj.location.x = ref2_co.x
                if loc_y:
                    obj.location.y = ref2_co.y
                if loc_z:
                    obj.location.z = ref2_co.z

    elif subject == "2":  # Cursor
        cur = context.scene.cursor.location

        def set_cursor_from_vector(target_co):
            if loc_x:
                cur.x = target_co.x + loc_offset[0]
            if loc_y:
                cur.y = target_co.y + loc_offset[1]
            if loc_z:
                cur.z = target_co.z + loc_offset[2]

        if self_or_active in {"0", "1"}:  # Cursor em relação ao ativo
            ref_points = get_reference_points(act_obj, "global")
            ref_min = Vector((ref_points[0], ref_points[3], ref_points[6]))
            ref_max = Vector((ref_points[2], ref_points[5], ref_points[8]))
            ref_center = (ref_min + ref_max) * 0.5
            ref_pivot = act_obj.matrix_world.translation.copy()

            if ref2 == "0":  # Min
                set_cursor_from_vector(ref_min)
            elif ref2 == "1":  # Center
                set_cursor_from_vector(ref_center)
            elif ref2 == "2":  # Pivot
                set_cursor_from_vector(ref_pivot)
            elif ref2 == "3":  # Max
                set_cursor_from_vector(ref_max)

        elif self_or_active == "2":  # Cursor em relação à seleção inteira
            ref_co = point_in_selection(act_obj, sel_obj)
            sel_min, sel_max = get_sel_ref(ref_co, sel_obj)
            sel_center = sel_min + (sel_max - sel_min) * 0.5

            if ref2 == "0":  # Min
                set_cursor_from_vector(sel_min)
            elif ref2 == "1":  # Center
                set_cursor_from_vector(sel_center)
            elif ref2 == "2":  # Pivot (usa o centro da seleção)
                set_cursor_from_vector(sel_center)
            elif ref2 == "3":  # Max
                set_cursor_from_vector(sel_max)


# ------------------------------------------------------------------------
# Preferences
# ------------------------------------------------------------------------

def update_panel(self, context):
    message = ": Updating Panel locations has failed"
    try:
        for panel in panels:
            if "bl_rna" in panel.__dict__:
                bpy.utils.unregister_class(panel)

        for panel in panels:
            panel.bl_category = context.preferences.addons[__name__].preferences.category
            bpy.utils.register_class(panel)

    except Exception as e:
        print("\n[{}]\n{}\n\nError:\n{}".format(__name__, message, e))
        pass


class AlignAddonPreferences(AddonPreferences):
    bl_idname = __name__

    category: StringProperty(
        name="Category",
        description="Choose a name for the category of the panel",
        default="Item",
        update=update_panel,
    )

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.15)
        col = split.column()
        col.label(text="Tab Category:")
        col = split.column()
        col.prop(self, "category", text="")


# ------------------------------------------------------------------------
# Advanced Align Operator
# ------------------------------------------------------------------------

class OBJECT_OT_align_tools(Operator):
    bl_idname = "object.align_tools"
    bl_label = "Align Operator"
    bl_description = "Align Object Tools"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    subject: EnumProperty(
        items=(("0", "Object", "Align Objects"),
               ("1", "Pivot", "Align Objects Pivot"),
               ("2", "Cursor", "Align Cursor To Active")),
        name="Align To",
        description="What will be moved"
    )

    advanced: BoolProperty(
        name="Advanced",
        default=False,
        description="Toggle Advanced Options"
    )

    loc_x: BoolProperty(
        name="Align to X axis",
        default=False,
        description="Enable X axis alignment"
    )
    loc_y: BoolProperty(
        name="Align to Y axis",
        default=False,
        description="Enable Y axis alignment"
    )
    loc_z: BoolProperty(
        name="Align to Z axis",
        default=False,
        description="Enable Z axis alignment"
    )

    self_or_active: EnumProperty(
        items=(("0", "Self", "In relation of itself"),
               ("1", "Active", "In relation of the active object"),
               ("2", "Selection", "In relation of the entire selection")),
        name="Relation",
        default="1",
        description="To what the pivot will be aligned"
    )

    ref1: EnumProperty(
        items=(("0", "Min", "Minimum"),
               ("3", "Max", "Maximum"),
               ("1", "Center", "Center")),
        name="Selection reference",
        description="Reference point"
    )

    ref2: EnumProperty(
        items=(("3", "Max", "Align to the maximum point"),
               ("1", "Center", "Align to the center point"),
               ("2", "Pivot", "Align to the pivot"),
               ("0", "Min", "Align to the minimum point"),
               ("4", "Cursor", "Cursor position")),
        name="Active reference",
        description="Destination point"
    )

    active_too: BoolProperty(
        name="Affect Active Too",
        default=False,
        description="Apply transformation to active object too"
    )

    consistent: BoolProperty(
        name="Consistent",
        default=False,
        description="Align selection as a single block"
    )

    loc_offset: FloatVectorProperty(
        name="Location Offset",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION',
        size=3,
        description="Location offset to apply"
    )

    fit_x: BoolProperty(
        name="Fit Dimension to X axis",
        default=False,
        description=""
    )
    fit_y: BoolProperty(
        name="Fit Dimension to Y axis",
        default=False,
        description=""
    )
    fit_z: BoolProperty(
        name="Fit Dimension to Z axis",
        default=False,
        description=""
    )

    apply_dim: BoolProperty(
        name="Apply Dimension",
        default=False,
        description="Enable Fit Dimensions"
    )

    rot_x: BoolProperty(
        name="Align Rotation to X axis",
        default=False,
        description=""
    )
    rot_y: BoolProperty(
        name="Align Rotation to Y axis",
        default=False,
        description=""
    )
    rot_z: BoolProperty(
        name="Align Rotation to Z axis",
        default=False,
        description=""
    )

    rot_offset: FloatVectorProperty(
        name="Rotation Offset",
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        size=3,
        description="Rotation offset to apply"
    )

    apply_rot: BoolProperty(
        name="Apply Rotation",
        default=False,
        description="Enable Rotation alignment"
    )

    scale_x: BoolProperty(
        name="Align Scale to X axis",
        default=False,
        description=""
    )
    scale_y: BoolProperty(
        name="Align Scale to Y axis",
        default=False,
        description=""
    )
    scale_z: BoolProperty(
        name="Align Scale to Z axis",
        default=False,
        description=""
    )

    scale_offset: FloatVectorProperty(
        name="Scale Offset",
        default=(0.0, 0.0, 0.0),
        subtype='XYZ',
        size=3,
        description="Scale offset to apply"
    )

    apply_scale: BoolProperty(
        name="Apply Scale",
        default=False,
        description="Enable Scale alignment"
    )

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row()
        row.label(text="Active object is: ", icon='OBJECT_DATA')

        box = layout.box()
        row2 = box.row()
        if obj:
            row2.prop(obj, "name", text="")
        else:
            row2.label(text="None")

        col = layout.column()
        col.prop(self, "subject", expand=True)
        col.prop(self, "self_or_active", text="Align")
        col.prop(self, "advanced")

        box2 = layout.box()
        if self.subject == "0":
            box2.prop(self, "consistent")
            box2.prop(self, "active_too")
        else:
            box2.label(text="Ignore for pivot and cursor!")

        if self.subject == "2":
            col.prop(self, "ref2", text="Cursor")
            if self.self_or_active == "2":
                col.prop(self, "ref1", text="Selection reference")
        else:
            col.prop(self, "ref1", text="Selection reference")
            col.prop(self, "ref2", text="Active reference")

        row3 = layout.row()
        row3.label(text='Align Location :')
        row4 = layout.row(align=True)
        row4.prop(self, 'loc_x', text='X', toggle=True)
        row4.prop(self, 'loc_y', text='Y', toggle=True)
        row4.prop(self, 'loc_z', text='Z', toggle=True)

        if self.advanced:
            row5 = layout.row()
            row5.prop(self, 'loc_offset', text='Offset')

        row12 = layout.row()
        row12.label(text='Align Rotation:')
        row13 = layout.row(align=True)
        row13.prop(self, 'rot_x', text='X', toggle=True)
        row13.prop(self, 'rot_y', text='Y', toggle=True)
        row13.prop(self, 'rot_z', text='Z', toggle=True)
        row13.prop(self, 'apply_rot', text='Apply', toggle=True)

        if self.advanced:
            row14 = layout.row()
            row14.prop(self, 'rot_offset', text='Offset')

        row12 = layout.row()
        row12.label(text='Align Scale:')
        row15 = layout.row(align=True)
        row15.prop(self, 'scale_x', text='X', toggle=True)
        row15.prop(self, 'scale_y', text='Y', toggle=True)
        row15.prop(self, 'scale_z', text='Z', toggle=True)
        row15.prop(self, 'apply_scale', text='Apply', toggle=True)

        if self.advanced:
            row15b = layout.row()
            row15b.prop(self, 'scale_offset', text='')

        row10 = layout.row()
        row10.label(text='Fit Dimensions:')
        row11 = layout.row(align=True)
        row11.prop(self, 'fit_x', text='X', toggle=True)
        row11.prop(self, 'fit_y', text='Y', toggle=True)
        row11.prop(self, 'fit_z', text='Z', toggle=True)
        row11.prop(self, 'apply_dim', text='Apply', toggle=True)

    def execute(self, context):
        align_function(
            context,
            self.subject, self.active_too, self.consistent,
            self.self_or_active, self.loc_x, self.loc_y, self.loc_z,
            self.ref1, self.ref2, self.loc_offset,
            self.rot_x, self.rot_y, self.rot_z, self.rot_offset, self.apply_rot,
            self.scale_x, self.scale_y, self.scale_z, self.scale_offset, self.apply_scale,
            self.fit_x, self.fit_y, self.fit_z, self.apply_dim
        )
        return {'FINISHED'}


# ------------------------------------------------------------------------
# Simple Align Operators
# ------------------------------------------------------------------------

class OBJECT_OT_AlignOperator(Operator):
    bl_idname = "object.align"
    bl_label = "Align Selected To Active"
    bl_description = "Align Selected To Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        LocAll(context)
        RotAll(context)
        return {'FINISHED'}


class OBJECT_OT_AlignLocationOperator(Operator):
    bl_idname = "object.align_location_all"
    bl_label = "Align Selected Location To Active"
    bl_description = "Align Selected Location To Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        LocAll(context)
        return {'FINISHED'}


class OBJECT_OT_AlignLocationXOperator(Operator):
    bl_idname = "object.align_location_x"
    bl_label = "Align Selected Location To Active X axis"
    bl_description = "Align Selected Location To Active X axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        LocX(context)
        return {'FINISHED'}


class OBJECT_OT_AlignLocationYOperator(Operator):
    bl_idname = "object.align_location_y"
    bl_label = "Align Selected Location To Active Y axis"
    bl_description = "Align Selected Location To Active Y axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        LocY(context)
        return {'FINISHED'}


class OBJECT_OT_AlignLocationZOperator(Operator):
    bl_idname = "object.align_location_z"
    bl_label = "Align Selected Location To Active Z axis"
    bl_description = "Align Selected Location To Active Z axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        LocZ(context)
        return {'FINISHED'}


class OBJECT_OT_AlignRotationOperator(Operator):
    bl_idname = "object.align_rotation"
    bl_label = "Align Selected Rotation To Active"
    bl_description = "Align Selected Rotation To Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        RotAll(context)
        return {'FINISHED'}


class OBJECT_OT_AlignRotationXOperator(Operator):
    bl_idname = "object.align_rotation_x"
    bl_label = "Align Selected Rotation To Active X axis"
    bl_description = "Align Selected Rotation To Active X axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        RotX(context)
        return {'FINISHED'}


class OBJECT_OT_AlignRotationYOperator(Operator):
    bl_idname = "object.align_rotation_y"
    bl_label = "Align Selected Rotation To Active Y axis"
    bl_description = "Align Selected Rotation To Active Y axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        RotY(context)
        return {'FINISHED'}


class OBJECT_OT_AlignRotationZOperator(Operator):
    bl_idname = "object.align_rotation_z"
    bl_label = "Align Selected Rotation To Active Z axis"
    bl_description = "Align Selected Rotation To Active Z axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        RotZ(context)
        return {'FINISHED'}


class OBJECT_OT_AlignObjectsScaleOperator(Operator):
    bl_idname = "object.align_objects_scale"
    bl_label = "Align Selected Objects Scale To Active"
    bl_description = "Align Selected Objects Scale To Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ScaleAll(context)
        return {'FINISHED'}


class OBJECT_OT_AlignObjectsScaleXOPerator(Operator):
    bl_idname = "object.align_objects_scale_x"
    bl_label = "Align Selected Objects Scale To Active X axis"
    bl_description = "Align Selected Objects Scale To Active X axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ScaleX(context)
        return {'FINISHED'}


class OBJECT_OT_AlignObjectsScaleYOPerator(Operator):
    bl_idname = "object.align_objects_scale_y"
    bl_label = "Align Selected Objects Scale To Active Y axis"
    bl_description = "Align Selected Objects Scale To Active Y axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ScaleY(context)
        return {'FINISHED'}


class OBJECT_OT_AlignObjectsScaleZOPerator(Operator):
    bl_idname = "object.align_objects_scale_z"
    bl_label = "Align Selected Objects Scale To Active Z axis"
    bl_description = "Align Selected Objects Scale To Active Z axis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ScaleZ(context)
        return {'FINISHED'}


# ------------------------------------------------------------------------
# Panel
# ------------------------------------------------------------------------

class VIEW3D_PT_AlignUi(Panel):
    bl_label = "Align Tools"
    bl_idname = "VIEW3D_PT_AlignUi"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row()
        row.label(text="Align Tools:", icon='OBJECT_DATA')

        if obj:
            row = layout.row()
            row.label(text="Active object is:", icon='OBJECT_DATA')
            row = layout.row()
            split = row.split(factor=0.15)
            col = split.column()
            col.label(text="")
            col = split.column()
            col.prop(obj, "name", text="")

        col = layout.column()
        col.label(text="Simple Align:")
        row = layout.row()
        row.operator("object.align", text="Loc & Rot")
        row = layout.row()
        row.operator("object.align_location_all", text="Location XYZ")
        row = layout.row()
        row.operator("object.align_rotation", text="Rotation XYZ")
        row = layout.row()
        row.operator("object.align_objects_scale", text="Scale XYZ")

        col = layout.column(align=True)
        col.label(text="Advanced:")
        col.operator("object.align_tools", text="Advanced Align")
        col.label(text="Selected to active:")


# ------------------------------------------------------------------------
# Register
# ------------------------------------------------------------------------

classes = (
    AlignAddonPreferences,
    OBJECT_OT_align_tools,
    OBJECT_OT_AlignOperator,
    OBJECT_OT_AlignLocationOperator,
    OBJECT_OT_AlignLocationXOperator,
    OBJECT_OT_AlignLocationYOperator,
    OBJECT_OT_AlignLocationZOperator,
    OBJECT_OT_AlignRotationOperator,
    OBJECT_OT_AlignRotationXOperator,
    OBJECT_OT_AlignRotationYOperator,
    OBJECT_OT_AlignRotationZOperator,
    OBJECT_OT_AlignObjectsScaleOperator,
    OBJECT_OT_AlignObjectsScaleXOPerator,
    OBJECT_OT_AlignObjectsScaleYOPerator,
    OBJECT_OT_AlignObjectsScaleZOPerator,
    VIEW3D_PT_AlignUi,
)

panels = (
    VIEW3D_PT_AlignUi,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
