import bpy
import pprint

class OP_CarTansferAnimation(bpy.types.Operator):
    bl_idname = 'anim.car_transfer_animation'
    bl_label = 'Transfer Animation'
    bl_description = 'Transfer follow path constraints and animation data from the Active to the Selected rig'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        selected_objs = bpy.context.selected_objects

        if len(selected_objs) != 2:
            self.report({'ERROR'}, 'Select two objects')
            return {'FINISHED'}

        source_obj = bpy.context.object

        selected_objs.remove(source_obj)
        target_obj = selected_objs[0]

        pprint.pprint(source_obj)
        pprint.pprint(target_obj)

        source_root = [b for b in source_obj.pose.bones if b.name == "Root"][0]
        target_root = [b for b in target_obj.pose.bones if b.name == "Root"][0]

        print(source_root.constraints)
        print(target_root.constraints)

        # remove constraints on target
        for c in target_root.constraints:
            target_root.constraints.remove(c)

        # transfer constraints from root
        for c in source_root.constraints:

            new_const = target_root.constraints.new(c.type)

            for prop in dir(c):
                try:
                    setattr(new_const, prop, getattr(c, prop))
                except:
                    pass

        # transfer animation data
        bpy.ops.object.make_links_data(type='ANIMATION')

        self.report({'INFO'}, 'Transfer done')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OP_CarTansferAnimation)


def unregister():
    bpy.utils.unregister_class(OP_CarTansferAnimation)


if __name__ == "__main__":
    register()
    bpy.ops.anim.car_transfer_animation()

