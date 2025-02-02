# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
import math
import bpy_extras
import mathutils
import re
from math import inf
from rna_prop_ui import rna_idprop_ui_create
from mathutils import Matrix, Vector

CUSTOM_SHAPE_LAYER = 13
MCH_BONE_EXTENSION_LAYER = 14
DEF_BONE_LAYER = 15
MCH_BONE_LAYER = 31

def deselect_edit_bones(ob):
    for b in ob.data.edit_bones:
        b.select = False
        b.select_head = False
        b.select_tail = False


def create_constraint_influence_driver(ob, cns, driver_data_path, base_influence=1.0):
    fcurve = cns.driver_add('influence')
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'influence'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path

    if base_influence != 1.0:
        fmod = fcurve.modifiers[0]
        fmod.mode = 'POLYNOMIAL'
        fmod.poly_order = 1
        fmod.coefficients = (0, base_influence)


def create_constraint_generic_driver(ob, cns, driver_data_path, property_name):
    fcurve = cns.driver_add(property_name)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = property_name
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path


def create_rotation_euler_x_driver(ob, bone, driver_data_path):
    fcurve = bone.driver_add('rotation_euler', 0)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path

def create_rotation_euler_y_driver(ob, bone, driver_data_path, flip = False):
    fcurve = bone.driver_add('rotation_euler', 1)
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    if flip:
        drv.expression = "-rotationAngle * 0.01745329252"
    else:
        drv.expression = "rotationAngle * 0.01745329252"

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path

def create_translation_x_driver(ob, bone, driver_data_path):
    fcurve = bone.driver_add('location', 0)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path


def create_bone_group(pose, group_name, color_set, bone_names):
    group = pose.bone_groups.new(name=group_name)
    group.color_set = color_set
    for bone_name in bone_names:
        bone = pose.bones.get(bone_name)
        if bone is not None:
            bone.bone_group = group


def name_range(prefix, nb=1000):
    if nb > 0:
        yield prefix
        for i in range(1, nb):
            yield '%s.%03d' % (prefix, i)


def get_widget(name):
    widget = bpy.data.objects.get(name)
    if widget is None:

        from . import widgets
        # import widgets

        widgets.create()
        widget = bpy.data.objects.get(name)
    return widget


def define_custom_property(target, name, value, description=None, overridable=True):
    rna_idprop_ui_create(target, name, default=value, description=description, overridable=overridable, min=-inf, max=inf)


def dispatch_bones_to_armature_layers(ob):
    re_mch_bone = re.compile(r'^MCH-Wheel(Brake)?\.(Ft|Bk)\.[LR](\.\d+)?$')
    default_visible_layers = [False] * 32

    for b in ob.data.bones:
        layers = [False] * 32
        if b.name.startswith('DEF-'):
            layers[DEF_BONE_LAYER] = True
        elif b.name.startswith('MCH-'):
            layers[MCH_BONE_LAYER] = True
            if b.name in ('MCH-Body', 'MCH-Steering') or re_mch_bone.match(b.name):
                layers[MCH_BONE_EXTENSION_LAYER] = True
        else:
            layer_num = ob.pose.bones[b.name].bone_group_index
            layers[layer_num] = True
            default_visible_layers[layer_num] = True
        b.layers = layers

    ob.data.layers = default_visible_layers

    shape_bone_layers = [False] * 32
    shape_bone_layers[CUSTOM_SHAPE_LAYER] = True
    for b in ob.pose.bones:
        if b.custom_shape:
            if b.custom_shape_transform:
                ob.pose.bones[b.custom_shape_transform.name].custom_shape = b.custom_shape
                ob.data.bones[b.custom_shape_transform.name].layers = shape_bone_layers
            else:
                ob.data.bones[b.name].layers[CUSTOM_SHAPE_LAYER] = True


class NameSuffix(object):

    def __init__(self, position, side, index=0):
        self.position = position
        self.side = side
        self.index = index
        if index == 0:
            self.value = '%s.%s' % (position, side)
        else:
            self.value = '%s.%s.%03d' % (position, side, index)

    def name(self, base_name=None):
        return '%s.%s' % (base_name, self.value) if base_name else self.value

    @property
    def is_front(self):
        return self.position == 'Ft'

    @property
    def is_left(self):
        return self.side == 'L'

    @property
    def is_first(self):
        return self.index == 0

    def __str__(self):
        return self.value


class BoundingBox(object):

    def __init__(self, armature, bone_name):
        objs = [o for o in armature.children if o.parent_bone == bone_name]
        bone = armature.data.bones[bone_name]
        self.__center = bone.head.copy()
        if not objs:
            self.__xyz = [bone.head.x - bone.length / 2, bone.head.x + bone.length / 2, bone.head.y - bone.length, bone.head.y + bone.length, .0, bone.head.z * 2]
        else:
            self.__xyz = [inf, -inf, inf, -inf, inf, -inf]
            self.__compute(mathutils.Matrix(), *objs)

    def __compute(self, pmatrix, *objs):
        for obj in objs:
            omatrix = pmatrix @ obj.matrix_world
            if obj.instance_type == 'COLLECTION':
                self.__compute(omatrix, *obj.instance_collection.all_objects)
            elif obj.bound_box:
                for p in obj.bound_box:
                    world_p = omatrix @ mathutils.Vector(p)
                    self.__xyz[0] = min(world_p.x, self.__xyz[0])
                    self.__xyz[1] = max(world_p.x, self.__xyz[1])
                    self.__xyz[2] = min(world_p.y, self.__xyz[2])
                    self.__xyz[3] = max(world_p.y, self.__xyz[3])
                    self.__xyz[4] = min(world_p.z, self.__xyz[4])
                    self.__xyz[5] = max(world_p.z, self.__xyz[5])
            self.__compute(pmatrix, *obj.children)

    @property
    def center(self):
        return self.__center

    @property
    def box_center(self):
        return mathutils.Vector((self.max_x + self.min_x, self.max_y + self.min_y, self.max_z + self.min_z)) / 2

    @property
    def min_x(self):
        return self.__xyz[0]

    @property
    def max_x(self):
        return self.__xyz[1]

    @property
    def min_y(self):
        return self.__xyz[2]

    @property
    def max_y(self):
        return self.__xyz[3]

    @property
    def min_z(self):
        return self.__xyz[4]

    @property
    def max_z(self):
        return self.__xyz[5]

    @property
    def width(self):
        return abs(self.__xyz[0] - self.__xyz[1])

    @property
    def length(self):
        return abs(self.__xyz[2] - self.__xyz[3])

    @property
    def height(self):
        return abs(self.__xyz[4] - self.__xyz[5])


class WheelBoundingBox(BoundingBox):

    def __init__(self, armature, bone_name, side):
        super().__init__(armature, bone_name)
        self.side = side

    def compute_outer_x(self, delta=0):
        if self.side == 'L':
            return self.max_x + delta
        else:
            return self.min_x - delta


class WheelsDimension(object):

    def __init__(self, armature, position, side_position, default):
        self.default = default
        self.position = position
        self.side_position = side_position
        self.wheels = []
        wheel_bones = (armature.data.edit_bones.get(name) for name in name_range('DEF-Wheel.%s.%s' % (self.position, self.side_position)))
        for wheel_bone in wheel_bones:
            if wheel_bone is None:
                break
            self.wheels.append(WheelBoundingBox(armature, wheel_bone.name, side_position))

    def name_suffixes(self):
        for i in range(len(self.wheels)):
            yield NameSuffix(self.position, self.side_position, i)

    def names(self, base_name=None):
        for name_suffix in name_range('%s.%s' % (self.position, self.side_position), self.nb):
            yield '%s.%s' % (base_name, name_suffix) if base_name else name_suffix

    def name(self, base_name=None):
        suffix = '%s.%s' % (self.position, self.side_position)
        return '%s.%s' % (base_name, suffix) if base_name else suffix

    @property
    def nb(self):
        return len(self.wheels)

    @property
    def min_position(self):
        if self.nb == 0:
            return self.default
        return min(self.wheels, key=lambda w: w.center.y).center

    @property
    def max_position(self):
        if self.nb == 0:
            return self.default
        return max(self.wheels, key=lambda w: w.center.y).center

    @property
    def medium_position(self):
        if self.nb == 0:
            return self.min_position
        return (self.min_position + self.max_position) / 2.0

    def compute_outer_x(self, delta=0):
        if self.side_position == 'L':
            x = max(map(lambda w: w.max_x, self.wheels))
            x += delta
        else:
            x = min(map(lambda w: w.min_x, self.wheels))
            x -= delta
        return x

    @property
    def outer_z(self):
        return max(map(lambda w: w.max_z, self.wheels))

    @property
    def outer_front(self):
        return min(map(lambda w: w.min_y, self.wheels))

    @property
    def outer_back(self):
        return max(map(lambda w: w.max_y, self.wheels))


class CarDimension(object):

    def __init__(self, armature):
        body = armature.data.edit_bones['DEF-Body']
        self.bb_body = BoundingBox(armature, 'DEF-Body')
        self.wheels_front_left = WheelsDimension(armature, 'Ft', 'L', default=body.head)
        self.wheels_front_right = WheelsDimension(armature, 'Ft', 'R', default=body.head)
        self.wheels_back_left = WheelsDimension(armature, 'Bk', 'L', default=body.tail)
        self.wheels_back_right = WheelsDimension(armature, 'Bk', 'R', default=body.tail)

    @property
    def body_center(self):
        return self.bb_body.center

    @property
    def car_center(self):
        center = self.bb_body.box_center.copy()
        center.y = (self.max_y + self.min_y) / 2
        return center

    @property
    def width(self):
        return max([self.bb_body.width] + [abs(w.compute_outer_x() - self.bb_body.center.x) * 2 for w in self.wheels_dimensions])

    @property
    def height(self):
        return max([self.bb_body.max_z] + [w.outer_z for w in self.wheels_dimensions])

    @property
    def length(self):
        return abs(self.max_y - self.min_y)

    @property
    def min_y(self):
        return min([self.bb_body.min_y] + [w.outer_front for w in self.wheels_dimensions])

    @property
    def max_y(self):
        return max([self.bb_body.max_y] + [w.outer_back for w in self.wheels_dimensions])

    @property
    def wheels_front_position(self):
        position = (self.wheels_front_left.min_position + self.wheels_front_right.min_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def wheels_back_position(self):
        position = (self.wheels_back_left.max_position + self.wheels_back_right.max_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def suspension_front_position(self):
        position = (self.wheels_front_left.medium_position + self.wheels_front_right.medium_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def suspension_back_position(self):
        position = (self.wheels_back_left.medium_position + self.wheels_back_right.medium_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def has_wheels(self):
        return self.has_front_wheels or self.has_back_wheels

    @property
    def has_front_wheels(self):
        return self.nb_front_wheels > 0

    @property
    def has_back_wheels(self):
        return self.nb_back_wheels > 0

    @property
    def nb_front_wheels(self):
        return max(self.wheels_front_left.nb, self.wheels_front_right.nb)

    @property
    def nb_back_wheels(self):
        return max(self.wheels_back_left.nb, self.wheels_back_right.nb)

    @property
    def wheels_dimensions(self):
        return filter(lambda w: w.nb, (self.wheels_front_left, self.wheels_front_right, self.wheels_back_left, self.wheels_back_right))


def create_wheel_brake_bone(wheel_brake, parent_bone, wheel_bone):
    wheel_brake.use_deform = False
    wheel_brake.parent = parent_bone
    wheel_brake.head = wheel_bone.head
    wheel_brake.tail = wheel_bone.tail


def generate_constraint_on_wheel_brake_bone(wheel_brake_pose_bone, wheel_pose_bone):
    wheel_brake_pose_bone.lock_location = (True, True, True)
    wheel_brake_pose_bone.lock_rotation = (True, True, True)
    wheel_brake_pose_bone.lock_rotation_w = True
    wheel_brake_pose_bone.lock_scale = (True, False, False)
    wheel_brake_pose_bone.custom_shape = get_widget('WGT-CarRig.WheelBrake')
    wheel_brake_pose_bone.bone.show_wire = True
    wheel_brake_pose_bone.bone_group = wheel_pose_bone.bone_group
    wheel_brake_pose_bone.bone.layers = wheel_pose_bone.bone.layers

    cns = wheel_brake_pose_bone.constraints.new('LIMIT_SCALE')
    cns.name = 'Brakes'
    cns.use_transform_limit = True
    cns.owner_space = 'LOCAL'
    cns.use_max_x = True
    cns.use_min_x = True
    cns.min_x = 1.0
    cns.max_x = 1.0
    cns.use_max_y = True
    cns.use_min_y = True
    cns.min_y = .5
    cns.max_y = 1.0
    cns.use_max_z = True
    cns.use_min_z = True
    cns.min_z = .5
    cns.max_z = 1.0


class ArmatureGenerator(object):

    def __init__(self, ob):
        self.ob = ob

    def generate(self, scene, adjust_origin):
        define_custom_property(self.ob,
                               name='wheels_on_y_axis',
                               value=False,
                               description="Activate wheels rotation when moving the root bone along the Y axis")
        define_custom_property(self.ob,
                               name='suspension_factor',
                               value=0.0,
                               description="Influence of the dampers over the pitch of the body")
        define_custom_property(self.ob,
                               name='suspension_rolling_factor',
                               value=0.0,
                               description="Influence of the dampers over the roll of the body")
        define_custom_property(self.ob,
                               name='camber',
                               value=0.0,
                               description="Camber angle")
        define_custom_property(self.ob,
                               name='wheel_offset',
                               value=(0.0, 0.0, 0.0),
                               description="Wheel offset")
        # define_custom_property(self.ob,
        #                        name='sb_mass',
        #                        value=.25,
        #                        description="The mass of the vehicle in the physics simulation")
        # define_custom_property(self.ob,
        #                        name='sb_friction',
        #                        value=4.0,
        #                        description="Friction of the physics simulation")
        # define_custom_property(self.ob,
        #                        name='sb_stiffness',
        #                        value=0.05,
        #                        description="Stiffness of the physics simulation")
        # define_custom_property(self.ob,
        #                        name='sb_roll',
        #                        value=1.0,
        #                        description="The effect of physics simulation on roll")
        # define_custom_property(self.ob,
        #                        name='sb_pitch',
        #                        value=0.25,
        #                        description="The effect of physics simulation on pitch")

        # DONE add parameters
        # REJECTED add button to bake and clear softbody cache
        # DONE split in different panels
        # DONE automatic follow path
        # REJECTED path picker exposed
        # DONE SW to Project by default
        # REJECTED Z constraint on suspension
        # DONE single bake button for wheels
        # DONE batch rename softbody to physics
        # DONE change from SHP-ROOT to ROOT
        # DONE copy paste tool
        # DONE expose friction
        # REJECTED split to a new rig - too much hassle
        # REJECTED change constraint influence method to generic method
        # DONE autoname rig according to *CAR* - including physics obj
        # DONE better name search + lower()
        # REJECTED NLA strip switcher
        # REJECTED refresh drivers in anim transfer
        # TODO convert from bone-based to object based follow path
        # DONE physics cache end frame to 1000+
        # DONE Z constraint on suspension - but place Physics on suspension position
        # DONE unlink variables from UI? -- kinda useless
        # DONE add proxy by default
        # TODO implement error handling on _check_selection
        # DONE car body center should always be in the center of wheels..no?
        # TODO prepurge to avoid issues while renaming?
        # TODO camber (WIP)
        # TODO wheels offset
        # TODO better reset position for brakes and body (or new approach altogether)

        location = self.ob.location.copy()
        self.ob.location = (0, 0, 0)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            self.dimension = CarDimension(self.ob)
            self.generate_animation_rig()
            self.ob.data['Car Rig'] = True
            deselect_edit_bones(self.ob)

            if adjust_origin:
                bpy.ops.object.mode_set(mode='OBJECT')
                self.set_origin(scene)

            bpy.ops.object.mode_set(mode='POSE')
            self.generate_constraints_on_rig()
            self.ob.display_type = 'WIRE'

            self.generate_bone_groups()
            dispatch_bones_to_armature_layers(self.ob)
            self.generate_physics_rig()
            self.position_proxy()

        finally:
            self.ob.location += location

    def generate_animation_rig(self):

        amt = self.ob.data
        body = amt.edit_bones['DEF-Body']
        root = amt.edit_bones.new('Root')
        if self.dimension.has_back_wheels:
            root.head = self.dimension.wheels_back_position
        elif self.dimension.has_front_wheels:
            root.head = self.dimension.wheels_front_position
        else:
            root.head = self.dimension.body_center
        root.head.z = 0
        root.tail = root.head
        root.tail.y += max(self.dimension.length / 1.95, self.dimension.width * 1.1)
        root.use_deform = False

        shape_root = amt.edit_bones.new('SHP-Root')
        shape_root.head = self.dimension.car_center
        shape_root.head.z = 0.01
        shape_root.tail = shape_root.head
        shape_root.tail.y += root.length
        shape_root.use_deform = False
        shape_root.parent = root

        drift = amt.edit_bones.new('Drift')
        drift.head = self.dimension.wheels_front_position
        drift.head.z = self.dimension.wheels_back_position.z
        drift.tail = drift.head
        drift.tail.y -= self.dimension.width * .95
        drift.roll = math.pi
        drift.use_deform = False
        drift.parent = root
        base_bone_parent = drift

        if self.dimension.has_front_wheels:
            groundsensor_axle_front = amt.edit_bones.new('GroundSensor.Axle.Ft')
            groundsensor_axle_front.head = self.dimension.wheels_front_position
            groundsensor_axle_front.tail = groundsensor_axle_front.head
            groundsensor_axle_front.tail.y += self.dimension.length / 16
            groundsensor_axle_front.parent = root

            shp_groundsensor_axle_front = amt.edit_bones.new('SHP-GroundSensor.Axle.Ft')
            shp_groundsensor_axle_front.head = groundsensor_axle_front.head
            shp_groundsensor_axle_front.tail = groundsensor_axle_front.tail
            shp_groundsensor_axle_front.head.z = shp_groundsensor_axle_front.tail.z = 0.001
            shp_groundsensor_axle_front.parent = groundsensor_axle_front

            mch_root_axle_front = amt.edit_bones.new('MCH-Root.Axle.Ft')
            mch_root_axle_front.head = self.dimension.wheels_front_position
            mch_root_axle_front.head.z = 0.001
            mch_root_axle_front.tail = mch_root_axle_front.head
            mch_root_axle_front.tail.y += self.dimension.length / 6
            mch_root_axle_front.parent = groundsensor_axle_front
            if not self.dimension.has_back_wheels:
                drift.parent = mch_root_axle_front

        if self.dimension.has_back_wheels:
            groundsensor_axle_back = amt.edit_bones.new('GroundSensor.Axle.Bk')
            groundsensor_axle_back.head = self.dimension.wheels_back_position
            groundsensor_axle_back.tail = groundsensor_axle_back.head
            groundsensor_axle_back.tail.y += self.dimension.length / 16
            groundsensor_axle_back.parent = drift

            shp_groundsensor_axle_back = amt.edit_bones.new('SHP-GroundSensor.Axle.Bk')
            shp_groundsensor_axle_back.head = groundsensor_axle_back.head
            shp_groundsensor_axle_back.tail = groundsensor_axle_back.tail
            shp_groundsensor_axle_back.head.z = shp_groundsensor_axle_back.tail.z = 0.001
            shp_groundsensor_axle_back.parent = groundsensor_axle_back

            mch_root_axle_back = amt.edit_bones.new('MCH-Root.Axle.Bk')
            mch_root_axle_back.head = self.dimension.wheels_back_position
            mch_root_axle_back.head.z = 0
            mch_root_axle_back.tail = mch_root_axle_back.head
            mch_root_axle_back.tail.y += self.dimension.length / 6
            mch_root_axle_back.parent = groundsensor_axle_back
            base_bone_parent = mch_root_axle_back

        shape_drift = amt.edit_bones.new('SHP-Drift')
        shape_drift.head = self.dimension.body_center
        shape_drift.head.y = self.dimension.max_y + drift.length * .2
        shape_drift.head.z = self.dimension.wheels_back_position.z
        shape_drift.tail = shape_drift.head
        shape_drift.tail.y += drift.length
        shape_drift.use_deform = False
        shape_drift.parent = base_bone_parent

        for wheel_dimension in self.dimension.wheels_dimensions:
            for name_suffix, wheel_bounding_box in zip(wheel_dimension.name_suffixes(), wheel_dimension.wheels):
                self.generate_animation_wheel_bones(name_suffix, wheel_bounding_box, base_bone_parent)
            self.generate_wheel_damper(wheel_dimension, base_bone_parent)

        if self.dimension.has_front_wheels:
            wheel_ft_r = amt.edit_bones.get('DEF-Wheel.Ft.R')
            wheelFtL = amt.edit_bones.get('DEF-Wheel.Ft.L')

            axis_ft = amt.edit_bones.new('MCH-Axis.Ft')
            axis_ft.head = wheel_ft_r.head
            axis_ft.tail = wheelFtL.head
            axis_ft.use_deform = False
            axis_ft.parent = base_bone_parent

            mch_steering = amt.edit_bones.new('MCH-Steering')
            mch_steering.head = self.dimension.wheels_front_position
            mch_steering.tail = self.dimension.wheels_front_position
            mch_steering.tail.y += self.dimension.width / 2
            mch_steering.use_deform = False
            mch_steering.parent = groundsensor_axle_front if groundsensor_axle_front else root

            steering_rotation = amt.edit_bones.new('MCH-Steering.rotation')
            steering_rotation.head = mch_steering.head
            steering_rotation.tail = mch_steering.tail
            steering_rotation.tail.y += 1
            steering_rotation.use_deform = False

            steering = amt.edit_bones.new('Steering')
            steering.head = steering_rotation.head
            steering.head.y = self.dimension.min_y - 4 * wheelFtL.length
            steering.tail = steering.head
            steering.tail.y -= self.dimension.width / 2
            steering.use_deform = False
            steering.parent = steering_rotation

        if self.dimension.has_back_wheels:
            wheel_bk_r = amt.edit_bones.get('DEF-Wheel.Bk.R')
            wheel_bk_l = amt.edit_bones.get('DEF-Wheel.Bk.L')

            axisBk = amt.edit_bones.new('MCH-Axis.Bk')
            axisBk.head = wheel_bk_r.head
            axisBk.tail = wheel_bk_l.head
            axisBk.use_deform = False
            axisBk.parent = base_bone_parent

        suspension_bk = amt.edit_bones.new('MCH-Suspension.Bk')
        suspension_bk.head = self.dimension.suspension_back_position
        suspension_bk.tail = self.dimension.suspension_back_position
        suspension_bk.tail.y += 2
        suspension_bk.use_deform = False
        suspension_bk.parent = base_bone_parent

        suspension_ft = amt.edit_bones.new('MCH-Suspension.Ft')
        suspension_ft.head = self.dimension.suspension_front_position
        align_vector = suspension_bk.head - suspension_ft.head
        align_vector.magnitude = 2
        suspension_ft.tail = self.dimension.suspension_front_position + align_vector
        suspension_ft.use_deform = False
        suspension_ft.parent = base_bone_parent

        axis = amt.edit_bones.new('MCH-Axis')
        axis.head = suspension_ft.head
        axis.tail = suspension_bk.head
        axis.use_deform = False
        axis.parent = suspension_ft

        mch_body = amt.edit_bones.new('MCH-Body')
        mch_body.head = body.head
        mch_body.tail = body.tail
        mch_body.tail.y += 1
        mch_body.use_deform = False
        mch_body.parent = axis

        suspension = amt.edit_bones.new('Suspension')
        suspension.head = self.dimension.body_center
        suspension.head.z = self.dimension.height + self.dimension.width * .25
        suspension.tail = suspension.head
        suspension.tail.y += root.length * .5
        suspension.use_deform = False
        suspension.parent = axis

    def generate_animation_wheel_bones(self, name_suffix, wheel_bounding_box, parent_bone):
        amt = self.ob.data

        def_wheel_bone = amt.edit_bones.get(name_suffix.name('DEF-Wheel'))

        if def_wheel_bone is None:
            return

        ground_sensor = amt.edit_bones.new(name_suffix.name('GroundSensor'))
        ground_sensor.head = wheel_bounding_box.box_center
        ground_sensor.head.z = def_wheel_bone.head.z
        ground_sensor.tail = ground_sensor.head
        ground_sensor.tail.y += max(max(wheel_bounding_box.height, ground_sensor.head.z) / 2.5, wheel_bounding_box.width * 1.02)
        ground_sensor.use_deform = False
        ground_sensor.parent = parent_bone

        shp_ground_sensor = amt.edit_bones.new(name_suffix.name('SHP-GroundSensor'))
        shp_ground_sensor.head = ground_sensor.head
        shp_ground_sensor.tail = ground_sensor.tail
        shp_ground_sensor.head.z = shp_ground_sensor.tail.z = .001
        shp_ground_sensor.use_deform = False
        shp_ground_sensor.parent = ground_sensor

        mch_wheel = amt.edit_bones.new(name_suffix.name('MCH-Wheel'))
        mch_wheel.head = def_wheel_bone.head
        mch_wheel.tail = def_wheel_bone.tail
        mch_wheel.tail.y += .5
        mch_wheel.use_deform = False
        mch_wheel.parent = ground_sensor

        define_custom_property(self.ob,
                               name=name_suffix.name('Wheel.rotation'),
                               value=.0,
                               description="Animation property for wheel spinning")
        mch_wheel_rotation = amt.edit_bones.new(name_suffix.name('MCH-Wheel.rotation'))
        mch_wheel_rotation.head = def_wheel_bone.head
        mch_wheel_rotation.tail = def_wheel_bone.head
        mch_wheel_rotation.tail.y += mch_wheel_rotation.tail.z
        mch_wheel_rotation.use_deform = False

        def_wheel_brake_bone = amt.edit_bones.get(name_suffix.name('DEF-WheelBrake'))
        if def_wheel_brake_bone is not None:
            mch_wheel = amt.edit_bones.new(name_suffix.name('MCH-WheelBrake'))
            mch_wheel.head = def_wheel_brake_bone.head
            mch_wheel.tail = def_wheel_brake_bone.tail
            mch_wheel.tail.y += .5
            mch_wheel.use_deform = False
            mch_wheel.parent = ground_sensor

        wheel = amt.edit_bones.new(name_suffix.name('Wheel'))
        wheel.use_deform = False
        wheel.parent = ground_sensor
        wheel.head = def_wheel_bone.head
        wheel.head.x = wheel_bounding_box.compute_outer_x(wheel_bounding_box.length * .05)
        wheel.tail = wheel.head
        wheel.tail.y += wheel.tail.z * .9

        if name_suffix.is_left and name_suffix.is_first:
            wheel_brake = amt.edit_bones.new(name_suffix.name('WheelBrake'))
            create_wheel_brake_bone(wheel_brake, mch_wheel, wheel)

    def generate_wheel_damper(self, wheel_dimension, parent_bone):
        amt = self.ob.data

        if wheel_dimension.nb == 1:
            wheel_damper_parent = amt.edit_bones[wheel_dimension.name('GroundSensor')]
        else:
            wheel_damper_parent = amt.edit_bones.new(wheel_dimension.name('MCH-GroundSensor'))
            wheel_damper_parent.head = wheel_dimension.medium_position
            wheel_damper_parent.tail = wheel_dimension.medium_position
            wheel_damper_parent.tail.y += 1.0
            wheel_damper_parent.head.z = 0
            wheel_damper_parent.tail.z = 0
            wheel_damper_parent.use_deform = False
            wheel_damper_parent.parent = parent_bone

        wheel_damper = amt.edit_bones.new(wheel_dimension.name('WheelDamper'))
        wheel_damper.head = wheel_dimension.medium_position
        wheel_damper_scale_ratio = abs(wheel_damper.head.z)
        wheel_damper.head.x = wheel_dimension.compute_outer_x(wheel_damper_scale_ratio * .25)
        wheel_damper.head.z *= 1.5
        wheel_damper.tail = wheel_damper.head
        wheel_damper.tail.y += wheel_damper_scale_ratio
        wheel_damper.use_deform = False
        wheel_damper.parent = wheel_damper_parent

        mch_wheel_damper = amt.edit_bones.new(wheel_dimension.name('MCH-WheelDamper'))
        mch_wheel_damper.head = wheel_dimension.medium_position
        mch_wheel_damper.tail = wheel_dimension.medium_position
        mch_wheel_damper.tail.y += 2
        mch_wheel_damper.use_deform = False
        mch_wheel_damper.parent = wheel_damper

    def generate_constraints_on_rig(self):
        pose = self.ob.pose

        for b in pose.bones:
            if b.name.startswith('DEF-') or b.name.startswith('MCH-') or b.name.startswith('SHP-'):
                b.lock_location = (True, True, True)
                b.lock_rotation = (True, True, True)
                b.lock_scale = (True, True, True)
                b.lock_rotation_w = True

        for wheel_dimension in self.dimension.wheels_dimensions:
            for name_suffix in wheel_dimension.name_suffixes():
                self.generate_constraints_on_wheel_bones(name_suffix)
            self.generate_constraints_on_wheel_damper(wheel_dimension)

        self.generate_constraints_on_axle_bones('Ft')
        self.generate_constraints_on_axle_bones('Bk')

        mch_axis = pose.bones.get('MCH-Axis')
        if mch_axis is not None:
            for axis_pos, influence in (('Ft', 1), ('Bk', .5)):
                subtarget = 'MCH-Axis.%s' % axis_pos
                if subtarget in pose.bones:
                    cns = mch_axis.constraints.new('TRANSFORM')
                    cns.name = 'Rotation from %s' % subtarget
                    cns.target = self.ob
                    cns.subtarget = subtarget
                    cns.map_from = 'ROTATION'
                    cns.from_min_x_rot = math.radians(-180)
                    cns.from_max_x_rot = math.radians(180)
                    cns.map_to_y_from = 'X'
                    cns.map_to = 'ROTATION'
                    cns.to_min_y_rot = math.radians(180)
                    cns.to_max_y_rot = math.radians(-180)
                    cns.owner_space = 'LOCAL'
                    cns.target_space = 'LOCAL'
                    create_constraint_influence_driver(self.ob, cns, '["suspension_rolling_factor"]', base_influence=influence)

        root = pose.bones['Root']
        root.lock_scale = (True, True, True)
        root.custom_shape = get_widget('WGT-CarRig.Root')
        root.custom_shape_transform = pose.bones['SHP-Root']
        root.bone.show_wire = True
        tmp_const = root.constraints.new('FOLLOW_PATH')
        tmp_const.forward_axis = "TRACK_NEGATIVE_Y"
        tmp_const.use_fixed_location = True
        tmp_const.use_curve_follow = True

        for ground_sensor_axle_name in ('GroundSensor.Axle.Ft', 'GroundSensor.Axle.Bk'):
            groundsensor_axle = pose.bones.get(ground_sensor_axle_name)
            if groundsensor_axle:
                groundsensor_axle.lock_location = (True, True, False)
                groundsensor_axle.lock_rotation = (True, True, True)
                groundsensor_axle.lock_scale = (True, True, True)
                groundsensor_axle.custom_shape = get_widget('WGT-CarRig.GroundSensor.Axle')
                groundsensor_axle.lock_rotation_w = True
                groundsensor_axle.custom_shape_transform = pose.bones['SHP-%s' % groundsensor_axle.name]
                groundsensor_axle.bone.show_wire = True
                self.generate_ground_projection_constraint(groundsensor_axle)

                if groundsensor_axle.name == 'GroundSensor.Axle.Ft' and 'GroundSensor.Axle.Bk' in pose.bones:
                    cns = groundsensor_axle.constraints.new('LIMIT_DISTANCE')
                    cns.name = 'Limit distance from Root'
                    cns.limit_mode = 'LIMITDIST_ONSURFACE'
                    cns.target = self.ob
                    cns.subtarget = 'GroundSensor.Axle.Bk'
                    cns.use_transform_limit = True
                    cns.owner_space = 'POSE'
                    cns.target_space = 'POSE'

        mch_root_axle_front = pose.bones.get('MCH-Root.Axle.Ft')
        mch_root_axle_back = pose.bones.get('MCH-Root.Axle.Bk')
        if mch_root_axle_front and mch_root_axle_back:
            cns = mch_root_axle_back.constraints.new('DAMPED_TRACK')
            cns.name = 'Track front axle'
            cns.target = self.ob
            cns.subtarget = mch_root_axle_front.name
            cns.track_axis = 'TRACK_NEGATIVE_Y'

        drift = pose.bones['Drift']
        drift.lock_location = (True, True, True)
        drift.lock_rotation = (True, True, False)
        drift.lock_scale = (True, True, True)
        drift.rotation_mode = 'ZYX'
        drift.custom_shape = get_widget('WGT-CarRig.DriftHandle')
        drift.custom_shape_transform = pose.bones['SHP-Drift']
        drift.bone.show_wire = True

        suspension = pose.bones['Suspension']
        suspension.lock_rotation = (True, True, True)
        suspension.lock_scale = (True, True, True)
        suspension.lock_rotation_w = True
        suspension.custom_shape = get_widget('WGT-CarRig.Suspension')
        suspension.bone.show_wire = True

        steering = pose.bones.get('Steering')
        if steering is not None:
            steering.lock_location = (False, True, True)
            steering.lock_rotation = (True, True, True)
            steering.lock_scale = (True, True, True)
            steering.lock_rotation_w = True
            steering.custom_shape = get_widget('WGT-CarRig.Steering')
            steering.bone.show_wire = True

            mch_steering_rotation = pose.bones['MCH-Steering.rotation']
            mch_steering_rotation.rotation_mode = 'QUATERNION'
            define_custom_property(self.ob,
                                   name='Steering.rotation',
                                   value=.0,
                                   description="Animation property for steering")
            create_translation_x_driver(self.ob, mch_steering_rotation, '["Steering.rotation"]')

            if mch_root_axle_back:
                cns = mch_steering_rotation.constraints.new('COPY_ROTATION')
                cns.name = 'Copy back axle rotation'
                cns.target = self.ob
                cns.subtarget = mch_root_axle_back.name
                cns.use_x = True
                cns.use_y = False
                cns.use_z = False
                cns.owner_space = 'LOCAL'
                cns.target_space = 'LOCAL'

            self.generate_childof_constraint(mch_steering_rotation, mch_root_axle_front if mch_root_axle_front else root)

            mch_steering = pose.bones['MCH-Steering']
            cns = mch_steering.constraints.new('DAMPED_TRACK')
            cns.name = 'Track steering bone'
            cns.target = self.ob
            cns.subtarget = 'Steering'
            cns.track_axis = 'TRACK_NEGATIVE_Y'

            cns = mch_steering.constraints.new('COPY_ROTATION')
            cns.name = 'Drift counter animation'
            cns.target = self.ob
            cns.subtarget = 'Drift'
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.use_offset = True
            cns.owner_space = 'LOCAL'
            cns.target_space = 'LOCAL'

        mch_body = self.ob.pose.bones['MCH-Body']
        cns = mch_body.constraints.new('TRANSFORM')
        cns.name = 'Suspension on rollover'
        cns.target = self.ob
        cns.subtarget = 'Suspension'
        cns.map_from = 'LOCATION'
        cns.from_min_x = -2
        cns.from_max_x = 2
        cns.from_min_y = -2
        cns.from_max_y = 2
        cns.map_to_x_from = 'Y'
        cns.map_to_y_from = 'X'
        cns.map_to = 'ROTATION'
        cns.to_min_x_rot = math.radians(6)
        cns.to_max_x_rot = math.radians(-6)
        cns.to_min_y_rot = math.radians(-7)
        cns.to_max_y_rot = math.radians(7)
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        cns = mch_body.constraints.new('TRANSFORM')
        cns.name = 'Suspension on vertical'
        cns.target = self.ob
        cns.subtarget = 'Suspension'
        cns.map_from = 'LOCATION'
        cns.from_min_z = -0.5
        cns.from_max_z = 0.5
        cns.map_to_z_from = 'Z'
        cns.map_to = 'LOCATION'
        cns.to_min_z = -0.1
        cns.to_max_z = 0.1
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        body = self.ob.pose.bones['DEF-Body']
        cns = body.constraints.new('COPY_TRANSFORMS')
        cns.target = self.ob
        cns.subtarget = 'MCH-Body'

    def generate_ground_projection_constraint(self, bone):
        cns = bone.constraints.new('SHRINKWRAP')
        cns.name = 'Ground projection'
        cns.shrinkwrap_type = 'PROJECT'
        cns.project_axis_space = 'LOCAL'
        cns.project_axis = 'NEG_Z'
        cns.distance = abs(bone.head.z)

    def generate_childof_constraint(self, child, parent):
        cns = child.constraints.new('CHILD_OF')
        cns.target = self.ob
        cns.subtarget = parent.name
        cns.inverse_matrix = self.ob.data.bones[parent.name].matrix_local.inverted()
        cns.use_location_x = True
        cns.use_location_y = True
        cns.use_location_z = True
        cns.use_rotation_x = True
        cns.use_rotation_y = True
        cns.use_rotation_z = True
        return cns

    def generate_constraints_on_axle_bones(self, position):
        pose = self.ob.pose

        subtarget = 'MCH-Axis.%s' % position
        if subtarget in pose.bones:
            mch_suspension = pose.bones['MCH-Suspension.%s' % position]
            cns = mch_suspension.constraints.new('COPY_LOCATION')
            cns.name = 'Location from %s' % subtarget
            cns.target = self.ob
            cns.subtarget = subtarget
            cns.head_tail = .5
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.owner_space = 'WORLD'
            cns.target_space = 'WORLD'
            create_constraint_influence_driver(self.ob, cns, '["suspension_factor"]')

            if position == 'Ft':
                cns = mch_suspension.constraints.new('DAMPED_TRACK')
                cns.name = 'Track suspension back'
                cns.target = self.ob
                cns.subtarget = 'MCH-Suspension.Bk'
                cns.track_axis = 'TRACK_Y'

        mch_axis = pose.bones.get('MCH-Axis.%s' % position)
        if mch_axis is not None:
            cns = mch_axis.constraints.new('COPY_LOCATION')
            cns.name = 'Copy location from right wheel'
            cns.target = self.ob
            cns.subtarget = 'MCH-WheelDamper.%s.R' % position
            cns.use_x = True
            cns.use_y = True
            cns.use_z = True
            cns.owner_space = 'WORLD'
            cns.target_space = 'WORLD'

            mch_axis = pose.bones['MCH-Axis.%s' % position]
            cns = mch_axis.constraints.new('DAMPED_TRACK')
            cns.name = 'Track Left Wheel'
            cns.target = self.ob
            cns.subtarget = 'MCH-WheelDamper.%s.L' % position
            cns.track_axis = 'TRACK_Y'

    def generate_constraints_on_wheel_bones(self, name_suffix):

        pose = self.ob.pose

        def_wheel = pose.bones.get(name_suffix.name('DEF-Wheel'))
        if def_wheel is None:
            return

        cns = def_wheel.constraints.new('COPY_TRANSFORMS')
        cns.target = self.ob
        cns.subtarget = name_suffix.name('MCH-Wheel')

        def_wheel_brake = pose.bones.get(name_suffix.name('DEF-WheelBrake'))

        if def_wheel_brake is not None:
            cns = def_wheel_brake.constraints.new('COPY_TRANSFORMS')
            cns.target = self.ob
            cns.subtarget = name_suffix.name('MCH-WheelBrake')

        ground_sensor = pose.bones[name_suffix.name('GroundSensor')]
        ground_sensor.lock_location = (True, True, False)
        ground_sensor.lock_rotation = (True, True, True)
        ground_sensor.lock_rotation_w = True
        ground_sensor.lock_scale = (True, True, True)
        ground_sensor.custom_shape = get_widget('WGT-CarRig.GroundSensor')
        ground_sensor.custom_shape_transform = pose.bones['SHP-%s' % ground_sensor.name]
        ground_sensor.bone.show_wire = True

        if name_suffix.is_front:
            cns = ground_sensor.constraints.new('COPY_ROTATION')
            cns.name = 'Steering rotation'
            cns.target = self.ob
            cns.subtarget = 'MCH-Steering'
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.owner_space = 'LOCAL'
            cns.target_space = 'LOCAL'

        self.generate_ground_projection_constraint(ground_sensor)

        cns = ground_sensor.constraints.new('LIMIT_LOCATION')
        cns.name = 'Ground projection limitation'
        cns.use_transform_limit = True
        cns.owner_space = 'LOCAL'
        cns.use_max_x = True
        cns.use_min_x = True
        cns.min_x = 0
        cns.max_x = 0
        cns.use_max_y = True
        cns.use_min_y = True
        cns.min_y = 0
        cns.max_y = 0
        cns.use_max_z = True
        cns.use_min_z = True
        cns.min_z = -.2
        cns.max_z = .2

        wheel = pose.bones.get(name_suffix.name('Wheel'))
        wheel.rotation_mode = "XYZ"
        wheel.lock_location = (True, True, True)
        wheel.lock_rotation = (False, True, True)
        wheel.lock_scale = (True, True, True)
        wheel.custom_shape = get_widget('WGT-CarRig.Wheel')
        wheel.bone.show_wire = True

        wheel_brake = pose.bones.get(name_suffix.name('WheelBrake'))

        print("OCIO BRAKES 1 " + str(wheel_brake) + " " + str(name_suffix.name('WheelBrake')))

        # TODO: re enable these constrainst? they look useless
        #if wheel_brake:

            #generate_constraint_on_wheel_brake_bone(wheel_brake, wheel)

        mch_brake = pose.bones[name_suffix.name('MCH-WheelBrake')]

        if mch_brake is not None:
            mch_brake.rotation_mode = "XYZ"

            print("OOOK" + str(mch_brake))

            if name_suffix.is_left:
                create_rotation_euler_y_driver(self.ob, mch_brake, '["camber"]', True)
            else:
                create_rotation_euler_y_driver(self.ob, mch_brake, '["camber"]', False)

        mch_wheel = pose.bones[name_suffix.name('MCH-Wheel')]
        mch_wheel.rotation_mode = "XYZ"

        cns = mch_wheel.constraints.new('COPY_ROTATION')
        cns.name = 'Bake animation wheels'
        cns.target = self.ob
        cns.subtarget = name_suffix.name('MCH-Wheel.rotation')
        cns.use_x = True
        cns.use_y = False
        cns.use_z = False
        cns.use_offset = False
        cns.owner_space = 'POSE'
        cns.target_space = 'POSE'

        cns = mch_wheel.constraints.new('TRANSFORM')
        cns.name = 'Wheel rotation along Y axis'
        cns.target = self.ob
        cns.subtarget = 'Root'
        cns.use_motion_extrapolate = True
        cns.map_from = 'LOCATION'
        cns.from_min_y = - math.pi * abs(mch_wheel.head.z if mch_wheel.head.z != 0 else 1)
        cns.from_max_y = - cns.from_min_y
        cns.map_to_x_from = 'Y'
        cns.map_to = 'ROTATION'
        cns.to_min_x_rot = math.pi
        cns.to_max_x_rot = -math.pi
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        create_constraint_influence_driver(self.ob, cns, '["wheels_on_y_axis"]')

        cns = mch_wheel.constraints.new('COPY_ROTATION')
        cns.name = 'Animation wheels'
        cns.target = self.ob
        cns.subtarget = wheel.name
        cns.use_x = True
        cns.use_y = False
        cns.use_z = False
        cns.use_offset = True
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        mch_wheel_rotation = pose.bones[name_suffix.name('MCH-Wheel.rotation')]
        mch_wheel_rotation.rotation_mode = "XYZ"
        self.generate_childof_constraint(mch_wheel_rotation, ground_sensor)

        create_rotation_euler_x_driver(self.ob, mch_wheel_rotation, '["%s"]' % name_suffix.name('Wheel.rotation'))

        if name_suffix.is_left:
            create_rotation_euler_y_driver(self.ob, mch_wheel, '["camber"]', True)
        else:
            create_rotation_euler_y_driver(self.ob, mch_wheel, '["camber"]', False)

        # create_constraint_generic_driver(self.ob, sb_mod.settings, '["sb_friction"]', "friction")

    def generate_constraints_on_wheel_damper(self, wheel_dimension):
        pose = self.ob.pose

        wheel_damper = pose.bones.get(wheel_dimension.name('WheelDamper'))
        if wheel_damper is not None:
            wheel_damper.lock_location = (True, True, False)
            wheel_damper.lock_rotation = (True, True, True)
            wheel_damper.lock_rotation_w = True
            wheel_damper.lock_scale = (True, True, True)
            wheel_damper.custom_shape = get_widget('WGT-CarRig.WheelDamper')
            wheel_damper.bone.show_wire = True

        mch_ground_sensor = pose.bones.get(wheel_dimension.name('MCH-GroundSensor'))
        if mch_ground_sensor is not None:
            fcurve = mch_ground_sensor.driver_add('location', 2)
            drv = fcurve.driver
            drv.type = 'MAX'

            for i, ground_sensor_name in enumerate(wheel_dimension.names('GroundSensor')):
                if ground_sensor_name in pose.bones:
                    var = drv.variables.new()
                    var.name = 'groundSensor%03d' % i
                    var.type = 'TRANSFORMS'

                    targ = var.targets[0]
                    targ.id = self.ob
                    targ.bone_target = ground_sensor_name
                    targ.transform_space = 'LOCAL_SPACE'
                    targ.transform_type = 'LOC_Z'

    def generate_bone_groups(self):
        pose = self.ob.pose
        create_bone_group(pose, 'Direction', color_set='THEME04', bone_names=('Root', 'Drift', 'SHP-Root', 'SHP-Drift'))
        create_bone_group(pose, 'Suspension', color_set='THEME09', bone_names=('Suspension', 'WheelDamper.Ft.L', 'WheelDamper.Ft.R', 'WheelDamper.Bk.L', 'WheelDamper.Bk.R'))

        wheel_widgets = ('Steering',)
        for wheel_dimension in self.dimension.wheels_dimensions:
            wheel_widgets += tuple(wheel_dimension.names('Wheel'))
            wheel_widgets += tuple(wheel_dimension.names('WheelBrake'))
        create_bone_group(pose, 'Wheel', color_set='THEME03', bone_names=wheel_widgets)

        ground_sensor_names = ('GroundSensor.Axle.Ft', 'GroundSensor.Axle.Bk', 'SHP-GroundSensor.Axle.Ft', 'SHP-GroundSensor.Axle.Bk')
        for wheel_dimension in self.dimension.wheels_dimensions:
            ground_sensor_names += tuple(wheel_dimension.names('GroundSensor'))
        ground_sensor_names += tuple("SHP-%s" % i for i in ground_sensor_names)
        create_bone_group(pose, 'GroundSensor', color_set='THEME02', bone_names=ground_sensor_names)

    def generate_physics_rig(self):

        for c in self.ob.children:
            for m in c.modifiers:
                if m.type == "SOFT_BODY":
                    sb_physics_obj = c

        # connection of suspension ctrl
        susp_ctrl = self.ob.pose.bones.get("Suspension")
        tmp_constr = susp_ctrl.constraints.new("COPY_LOCATION")
        tmp_constr.target = sb_physics_obj
        tmp_constr.subtarget = "mass"
        tmp_constr.influence = 1
        tmp_constr.use_x = True
        tmp_constr.use_y = False
        tmp_constr.use_z = False
        tmp_constr.target_space = "CUSTOM"
        tmp_constr.owner_space = "CUSTOM"
        tmp_constr.space_object = self.ob
        tmp_constr.space_subtarget = "Root"
        # create_constraint_influence_driver(self.ob, tmp_constr, '["sb_roll"]')

        tmp_constr = susp_ctrl.constraints.new("COPY_LOCATION")
        tmp_constr.target = sb_physics_obj
        tmp_constr.subtarget = "mass"
        tmp_constr.influence = 0.05
        tmp_constr.use_x = False
        tmp_constr.use_y = True
        tmp_constr.use_z = False
        tmp_constr.target_space = "CUSTOM"
        tmp_constr.owner_space = "CUSTOM"
        tmp_constr.space_object = self.ob
        tmp_constr.space_subtarget = "Root"
        # create_constraint_influence_driver(self.ob, tmp_constr, '["sb_pitch"]')

        tmp_constr = susp_ctrl.constraints.new("COPY_LOCATION")
        tmp_constr.target = sb_physics_obj
        tmp_constr.subtarget = "mass"
        tmp_constr.influence = 0.5
        tmp_constr.use_x = False
        tmp_constr.use_y = False
        tmp_constr.use_z = True
        tmp_constr.target_space = "CUSTOM"
        tmp_constr.owner_space = "CUSTOM"
        tmp_constr.space_object = self.ob
        tmp_constr.space_subtarget = "Root"
        # create_constraint_influence_driver(self.ob, tmp_constr, '["sb_pitch"]')

        # creation of 4 location constraints to follow wheels
        tmp_constr = sb_physics_obj.constraints.new("COPY_LOCATION")
        tmp_constr.target = self.ob
        tmp_constr.subtarget = "GroundSensor.Ft.L"
        tmp_constr.use_z = False
        tmp_constr.influence = 1

        tmp_constr = sb_physics_obj.constraints.new("COPY_LOCATION")
        tmp_constr.target = self.ob
        tmp_constr.subtarget = "GroundSensor.Ft.R"
        tmp_constr.use_z = False
        tmp_constr.influence = 0.333333

        tmp_constr = sb_physics_obj.constraints.new("COPY_LOCATION")
        tmp_constr.target = self.ob
        tmp_constr.subtarget = "GroundSensor.Bk.L"
        tmp_constr.use_z = False
        tmp_constr.influence = 0.333333

        tmp_constr = sb_physics_obj.constraints.new("COPY_LOCATION")
        tmp_constr.target = self.ob
        tmp_constr.subtarget = "GroundSensor.Bk.R"
        tmp_constr.use_z = False
        tmp_constr.influence = 0.333333

        sb_physics_obj.location = [0, 0, 0]
        susp_ctrl_w_loc = self.ob.location + susp_ctrl.head
        sb_physics_obj.location = [0, 0, susp_ctrl_w_loc[2]]


    def position_proxy(self):

        for c in self.ob.children:
            if "proxy" in c.name.lower():
                proxy_obj = c

        def_body_location = self.ob.pose.bones.get("DEF-Body").head
        proxy_obj.location = def_body_location


    def set_origin(self, scene):
        object_location = self.ob.location[:]
        root = self.ob.data.bones.get('Root')
        if root:
            cursor_location = scene.cursor.location[:]
            scene.cursor.location = root.head
            try:
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            finally:
                scene.cursor.location = cursor_location
                self.ob.location = object_location


class OBJECT_OT_armatureCarDeformationRig(bpy.types.Operator):
    bl_idname = "object.armature_car_deformation_rig_v2"
    bl_label = "Add car deformation rig (V2)"
    bl_description = "Creates the base rig for a car, including physics"
    bl_options = {'REGISTER', 'UNDO'}

    body_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                  description='Extra translation added to location of the car body',
                                                  size=3,
                                                  default=(0, 0, 0),
                                                  subtype='TRANSLATION')

    nb_front_wheels_pairs: bpy.props.IntProperty(name='Pairs',
                                                 description='Number of front wheels pairs',
                                                 default=1,
                                                 min=0)

    front_wheel_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                         description='Extra translation added to location of the front wheels',
                                                         size=3,
                                                         default=(0, 0, 0),
                                                         subtype='TRANSLATION')

    nb_back_wheels_pairs: bpy.props.IntProperty(name='Pairs',
                                                description='Number of back wheels pairs',
                                                default=1,
                                                min=0)

    back_wheel_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                        description='Extra translation added to location of the back wheels',
                                                        size=3,
                                                        default=(0, 0, 0),
                                                        subtype='TRANSLATION')

    nb_front_wheel_brakes_pairs: bpy.props.IntProperty(name='Front Pairs',
                                                       description='Number of front wheel brakes pairs',
                                                       default=0,
                                                       min=0)

    front_wheel_brakes_pos_delta: bpy.props.FloatProperty(name='Front Delta Location',
                                                          description='Extra translation added to location of the front brakes',
                                                          default=0)

    nb_back_wheel_brakes_pairs: bpy.props.IntProperty(name='Back Pairs',
                                                      description='Number of back wheel brakes pairs',
                                                      default=0,
                                                      min=0)

    back_wheel_brakes_pos_delta: bpy.props.FloatProperty(name='Back Delta Location',
                                                         description='Extra translation added to location of the back brakes',
                                                         default=0)

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.label(text='Body')
        layout = self.layout.box()
        layout.prop(self, 'body_pos_delta')
        self.layout.label(text='Front wheels')
        layout = self.layout.box()
        layout.prop(self, 'nb_front_wheels_pairs')
        layout.prop(self, 'front_wheel_pos_delta')
        self.layout.label(text='Back wheels')
        layout = self.layout.box()
        layout.prop(self, 'nb_back_wheels_pairs')
        layout.prop(self, 'back_wheel_pos_delta')
        self.layout.label(text='Brakes')
        layout = self.layout.box()
        layout.prop(self, 'nb_front_wheel_brakes_pairs')
        layout.prop(self, 'front_wheel_brakes_pos_delta')
        layout.prop(self, 'nb_back_wheel_brakes_pairs')
        layout.prop(self, 'back_wheel_brakes_pos_delta')

    def invoke(self, context, event):
        self.bones_position = {
            'Body':       mathutils.Vector((0.0,  0,  .8)),
            'Wheel.Ft.L': mathutils.Vector((0.9, -2,  .5)),
            'Wheel.Ft.R': mathutils.Vector((-.9, -2,  .5)),
            'Wheel.Bk.L': mathutils.Vector((0.9,  2,  .5)),
            'Wheel.Bk.R': mathutils.Vector((-.9,  2,  .5)),
            'WheelBrake.Ft.L': mathutils.Vector((0.8, -2,  .5)),
            'WheelBrake.Ft.R': mathutils.Vector((-.8, -2,  .5)),
            'WheelBrake.Bk.L': mathutils.Vector((0.8,  2,  .5)),
            'WheelBrake.Bk.R': mathutils.Vector((-.8,  2,  .5))
        }

        self.target_objects = {}

        # find body and extract prefix
        res = self._find_generic_obj(context, 'Body')

        if res == False:
            print("no body found")
            return self.execute(context)

        self._find_generic_obj(context, 'Wheel.Ft.L')
        self._find_generic_obj(context, 'Wheel.Ft.R')
        self._find_generic_obj(context, 'Wheel.Bk.L')
        self._find_generic_obj(context, 'Wheel.Bk.R')

        self._find_generic_obj(context, 'WheelBrake.Ft.L')
        self._find_generic_obj(context, 'WheelBrake.Ft.R')
        self._find_generic_obj(context, 'WheelBrake.Bk.L')
        self._find_generic_obj(context, 'WheelBrake.Bk.R')

        # TODO: this is needed for multiple rear/front wheels. cool!
        # self.nb_front_wheels_pairs = max(nb_wheels_ft_l, nb_wheels_ft_r)
        # self.nb_back_wheels_pairs = max(nb_wheels_bk_l, nb_wheels_bk_r)
        # self.nb_front_wheel_brakes_pairs = max(nb_wheel_brakes_ft_l, nb_wheel_brakes_ft_r)
        # self.nb_back_wheel_brakes_pairs = max(nb_wheel_brakes_bk_l, nb_wheel_brakes_bk_r)

        # enforcing 2 axles
        self.nb_front_wheels_pairs = 1
        self.nb_back_wheels_pairs = 1
        self.nb_front_wheel_brakes_pairs = 1
        self.nb_back_wheel_brakes_pairs = 1

        def move_origin(target_obj, location):
            mat = Matrix.Translation(location - target_obj.location)
            target_obj.location = location
            target_obj.data.transform(mat.inverted())
            target_obj.data.update()

        # TODO this body reset sounds clever but move stuff around. need to rethink approach.
        # tweak body origin so that it's centered on wheels
        # obj = self.target_objects["Body"]
        # children = []
        #
        # for c in children:
        #     children.append(c)
        #     c.parent = None
        #
        # target_position = (self.target_objects["Wheel.Ft.L"].location + self.target_objects["Wheel.Ft.R"].location + \
        #                    self.target_objects["Wheel.Bk.L"].location + self.target_objects["Wheel.Bk.R"].location)/4
        #
        # move_origin(obj, target_position)
        # self.bones_position["Body"] = obj.location.copy()
        #
        # for c in children:
        #     c.parent = obj

        # tweak brakes origin so that they are centered on wheels (needed for cambering)
        # TODO this creates issues with instances - they move around. You need to add a camber bone, just admit it.
        obj = self.target_objects["WheelBrake.Ft.L"]
        target_position = self.target_objects["Wheel.Ft.L"].location.copy()
        move_origin(obj, target_position)
        self.bones_position["WheelBrake.Ft.L"] = obj.location.copy()

        obj = self.target_objects["WheelBrake.Ft.R"]
        target_position = self.target_objects["Wheel.Ft.R"].location.copy()
        move_origin(obj, target_position)
        self.bones_position["WheelBrake.Ft.R"] = obj.location.copy()

        obj = self.target_objects["WheelBrake.Bk.L"]
        target_position = self.target_objects["Wheel.Bk.L"].location.copy()
        move_origin(obj, target_position)
        self.bones_position["WheelBrake.Bk.L"] = obj.location.copy()

        obj = self.target_objects["WheelBrake.Bk.R"]
        target_position = self.target_objects["Wheel.Bk.R"].location.copy()
        move_origin(obj, target_position)
        self.bones_position["WheelBrake.Bk.R"] = obj.location.copy()

        # ORIGINAL CODE
        # has_body_target = self._find_target_object(context, 'Body')
        #
        # nb_wheels_ft_l = self._find_target_object_for_wheels(context, 'Wheel.Ft.L')
        # nb_wheels_ft_r = self._find_target_object_for_wheels(context, 'Wheel.Ft.R')
        # nb_wheels_bk_l = self._find_target_object_for_wheels(context, 'Wheel.Bk.L')
        # nb_wheels_bk_r = self._find_target_object_for_wheels(context, 'Wheel.Bk.R')
        #
        # nb_wheel_brakes_ft_l = self._find_target_object_for_wheels(context, 'WheelBrake.Ft.L')
        # nb_wheel_brakes_ft_r = self._find_target_object_for_wheels(context, 'WheelBrake.Ft.R')
        # nb_wheel_brakes_bk_l = self._find_target_object_for_wheels(context, 'WheelBrake.Bk.L')
        # nb_wheel_brakes_bk_r = self._find_target_object_for_wheels(context, 'WheelBrake.Bk.R')
        #
        # self.nb_front_wheels_pairs = max(nb_wheels_ft_l, nb_wheels_ft_r)
        # self.nb_back_wheels_pairs = max(nb_wheels_bk_l, nb_wheels_bk_r)
        # self.nb_front_wheel_brakes_pairs = max(nb_wheel_brakes_ft_l, nb_wheel_brakes_ft_r)
        # self.nb_back_wheel_brakes_pairs = max(nb_wheel_brakes_bk_l, nb_wheel_brakes_bk_r)

        return self.execute(context)

    def _check_selection(self, context):

        body = False
        prefix = "NONE"

        wheels = {
            "Wheel.Ft.L": False,
            "Wheel.Ft.R": False,
            "Wheel.Bk.L": False,
            "Wheel.Bk.R": False
        }

        wheelbrakes = {
            "WheelBrake.Ft.L": False,
            "WheelBrake.Ft.R": False,
            "WheelBrake.Bk.L": False,
            "WheelBrake.Bk.R": False
        }

        for obj in context.selected_objects:

            name_low = obj.name.lower()

            if "body" in name_low:
                body = True

                chunks = name_low.split("body")
                len_prefix = len(chunks[0])
                prefix = obj.name[0:len_prefix]  # same length but from original name
                prefix = "".join(filter(str.isalnum, prefix))  # cleanup (alphanumeric only)

        for key in wheels:

            key_low = key.lower()

            for obj in context.selected_objects:
                if key_low in obj.name.lower():
                    wheels[key] = True

        for key in wheelbrakes:

            key_low = key.lower()

            for obj in context.selected_objects:
                if key_low in obj.name.lower():
                    wheels[key] = True

        print(f"body, passed: {body}")

        for key in wheels:
            print(f"{key}, passed: {wheels[key]}")

        for key in wheelbrakes:
            print(f"{key}, passed: {wheelbrakes[key]}")

        return True, prefix

    def _find_generic_obj(self, context, key):

        key_low = key.lower()

        for obj in context.selected_objects:

            name_low = obj.name.lower()

            if key_low in name_low:
                self.target_objects[key] = obj
                self.bones_position[key] = obj.location.copy()
                return True

        return False

    # def _find_target_object_for_wheels(self, context, suffix_name):
    #     for count, name in enumerate(name_range(suffix_name)):
    #         if not self._find_target_object(context, name):
    #             return count
    #
    # def _find_target_object(self, context, name):
    #     escaped_name = re.escape(name).replace(r'\.', r'[\.-_ ]')
    #     pattern = re.compile(f"^.*{escaped_name}$", re.IGNORECASE)
    #     for obj in context.selected_objects:
    #         if pattern.match(obj.name):
    #             self.target_objects_name[name] = obj.name
    #             self.bones_position[name] = obj.location.copy()
    #             return True
    #     return False

    def execute(self, context):
        """Creates the meta rig with basic bones"""
        amt = bpy.data.armatures.new('Car Rig Data')
        amt['Car Rig'] = False

        res, prefix = self._check_selection(context)
        rig = bpy_extras.object_utils.object_data_add(context, amt, name=f'{prefix}-car-rig')

        # TODO: cannot edit new object added to a hidden collection
        # Could be a better fix (steal code from other addons).
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except TypeError:
            self.report({'ERROR'}, "Cannot edit the new armature! Please make sure the active collection is visible and editable")
            return {'CANCELLED'}

        self._create_bone(rig, 'Body', delta_pos=self.body_pos_delta)

        self._create_wheel_bones(rig, 'Wheel.Ft.L', self.nb_front_wheels_pairs, self.front_wheel_pos_delta)
        self._create_wheel_bones(rig, 'Wheel.Ft.R', self.nb_front_wheels_pairs, self.front_wheel_pos_delta.reflect(mathutils.Vector((1, 0, 0))))
        self._create_wheel_bones(rig, 'Wheel.Bk.L', self.nb_back_wheels_pairs, self.back_wheel_pos_delta)
        self._create_wheel_bones(rig, 'Wheel.Bk.R', self.nb_back_wheels_pairs, self.back_wheel_pos_delta.reflect(mathutils.Vector((1, 0, 0))))

        front_wheel_brakes_delta_pos = self.front_wheel_pos_delta.copy()
        front_wheel_brakes_delta_pos.x = self.front_wheel_brakes_pos_delta
        self._create_wheel_bones(rig, 'WheelBrake.Ft.L', self.nb_front_wheel_brakes_pairs, front_wheel_brakes_delta_pos)
        self._create_wheel_bones(rig, 'WheelBrake.Ft.R', self.nb_front_wheel_brakes_pairs, front_wheel_brakes_delta_pos.reflect(mathutils.Vector((1, 0, 0))))
        back_wheel_brakes_delta_pos = self.back_wheel_pos_delta.copy()
        back_wheel_brakes_delta_pos.x = self.back_wheel_brakes_pos_delta
        self._create_wheel_bones(rig, 'WheelBrake.Bk.L', self.nb_back_wheel_brakes_pairs, back_wheel_brakes_delta_pos)
        self._create_wheel_bones(rig, 'WheelBrake.Bk.R', self.nb_back_wheel_brakes_pairs, back_wheel_brakes_delta_pos.reflect(mathutils.Vector((1, 0, 0))))

        deselect_edit_bones(rig)

        bpy.ops.object.mode_set(mode='OBJECT')

        # creation of a mesh with a single vertex and a vertex group
        sb_mesh = bpy.data.meshes.new(prefix + "-Physics")
        sb_physics_obj = bpy.data.objects.new(sb_mesh.name, sb_mesh)
        col = bpy.context.collection
        col.objects.link(sb_physics_obj)
        bpy.context.view_layer.objects.active = sb_physics_obj

        # softbody modifier for auto movement
        sb_mod = sb_physics_obj.modifiers.new("Softbody", "SOFT_BODY")
        sb_mod.settings.goal_default = 0.95
        sb_mod.settings.goal_friction = 4
        sb_mod.settings.mass = 0.25
        sb_mod.settings.goal_spring = 0.05
        sb_mod.point_cache.frame_end = 2000

        # create_constraint_generic_driver(self.ob, sb_mod.settings, '["sb_mass"]', "")
        # create_constraint_generic_driver(self.ob, sb_mod.settings, '["sb_stiffness"]', "goal_spring")
        # create_constraint_generic_driver(self.ob, sb_mod.settings, '["sb_friction"]', "friction")

        verts = [(0, 0, 0)]
        edges = []
        faces = []
        sb_mesh.from_pydata(verts, edges, faces)

        vx_group = bpy.context.active_object.vertex_groups.new(name='mass')
        vx_indeces = [0]
        vx_group.add(vx_indeces, 1.0, 'ADD')

        sb_physics_obj.parent = rig

        # creation of a proxy to enable datasmith-based workflow
        proxy_mesh = bpy.data.meshes.new(prefix + "-Proxy")
        proxy_obj = bpy.data.objects.new(proxy_mesh.name, proxy_mesh)
        col = bpy.context.collection
        col.objects.link(proxy_obj)
        bpy.context.view_layer.objects.active = proxy_obj

        verts = [(-1.0e-05, -1.0e-05, 0.0), (-1.0e-05, 1.0e-05, 0.0), (1.0e-05, 1.0e-05, 0.0), (1.0e-05, -1.0e-05, 0.0)]

        edges = []
        faces = [[0, 1, 2, 3]]
        proxy_mesh.from_pydata(verts, edges, faces)
        proxy_obj.parent = rig

        return {'FINISHED'}

    def _create_bone(self, rig, name, delta_pos):
        b = rig.data.edit_bones.new('DEF-' + name)

        b.head = self.bones_position[name] + delta_pos
        b.tail = b.head
        if name == 'Body':
            b.tail.y += b.tail.z * 4
        else:
            b.tail.y += b.tail.z

        target_obj = self.target_objects.get(name)

        if target_obj is not None:
            if name == 'Body':
                b.tail = b.head
                b.tail.y += target_obj.dimensions[1] / 2 if target_obj.dimensions and target_obj.dimensions[0] != 0 else 1
            target_obj.parent = rig
            target_obj.parent_bone = b.name
            target_obj.parent_type = 'BONE'
            target_obj.location += rig.matrix_world.to_translation()
            target_obj.matrix_parent_inverse = (rig.matrix_world @ mathutils.Matrix.Translation(b.tail)).inverted()

        return b

    def _create_wheel_bones(self, rig, base_wheel_name, nb_wheels, delta_pos):
        for wheel_name in name_range(base_wheel_name, nb_wheels):
            if wheel_name not in self.bones_position:
                wheel_position = previous_wheel_default_pos.copy()
                wheel_position.y += abs(previous_wheel.head.z * 2.2)
                self.bones_position[wheel_name] = wheel_position
            previous_wheel = self._create_bone(rig, wheel_name, delta_pos)
            previous_wheel_default_pos = self.bones_position[wheel_name]


class POSE_OT_carAnimationRigGenerate(bpy.types.Operator):
    bl_idname = "pose.car_animation_rig_generate"
    bl_label = "Generate car animation rig"
    bl_description = "Creates the complete armature for animating the car."
    bl_options = {'REGISTER', 'UNDO'}

    adjust_origin: bpy.props.BoolProperty(name='Move origin',
                                          description='Set origin of the armature at the same location as root bone',
                                          default=True)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.data is not None and 'Car Rig' in context.object.data

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.prop(self, 'adjust_origin')

    def execute(self, context):
        if context.object.data['Car Rig']:
            self.report({'INFO'}, 'Rig already generated')
            return {"CANCELLED"}

        if 'DEF-Body' not in context.object.data.bones:
            self.report({'ERROR'}, 'No bone named DEF-Body. This is not a valid armature!')
            return {"CANCELLED"}

        armature_generator = ArmatureGenerator(context.object)
        armature_generator.generate(context.scene, self.adjust_origin)
        return {"FINISHED"}


class POSE_OT_carAnimationAddBrakeWheelBones(bpy.types.Operator):
    bl_idname = "pose.car_animation_add_brake_wheel_bones"
    bl_label = "Add missing brake wheel bones"
    bl_description = "Generates missing brake wheel bones for each selected wheel widget."
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.mode == 'POSE' and\
               context.object is not None and context.object.data is not None and\
               context.object.data.get('Car Rig')

    def execute(self, context):
        mode = context.object.mode
        re_wheel_bone_name = re.compile(r'^Wheel\.(Ft|Bk)\.([LR])(\.\d+)?$')
        for pose_bone in context.selected_pose_bones:
            matcher = re_wheel_bone_name.match(pose_bone.name)
            if matcher:
                wheelbrake_name = 'WheelBrake.%s.%s%s' % matcher.groups(default='')
                parent_name = 'MCH-Wheel.%s.%s%s' % matcher.groups(default='')
                self.create_wheelbrake_bone(context, pose_bone, wheelbrake_name, parent_name)
        bpy.ops.object.mode_set(mode=mode)
        return {"FINISHED"}

    def create_wheelbrake_bone(self, context, wheel_pose_bone, name, parent_name):
        obj = context.object
        amt = context.object.data
        if name not in amt.bones and parent_name in amt.bones:
            bpy.ops.object.mode_set(mode='EDIT')
            create_wheel_brake_bone(amt.edit_bones.new(name), amt.edit_bones[parent_name], amt.edit_bones[wheel_pose_bone.name])
            bpy.ops.object.mode_set(mode='POSE')
            generate_constraint_on_wheel_brake_bone(obj.pose.bones[name], wheel_pose_bone)


def register():
    bpy.utils.register_class(POSE_OT_carAnimationRigGenerate)
    bpy.utils.register_class(OBJECT_OT_armatureCarDeformationRig)
    bpy.utils.register_class(POSE_OT_carAnimationAddBrakeWheelBones)


def unregister():
    bpy.utils.unregister_class(POSE_OT_carAnimationAddBrakeWheelBones)
    bpy.utils.unregister_class(OBJECT_OT_armatureCarDeformationRig)
    bpy.utils.unregister_class(POSE_OT_carAnimationRigGenerate)


if __name__ == "__main__":

    # main
    register()
