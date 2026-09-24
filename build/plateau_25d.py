# Construit "LE PLATEAU UNIFLOW" en rig 2.5D : plans de profondeur + sprites + dolly.
# Usage: blender.sh [--background] --python build/plateau_25d.py
import os
import bpy

BASE = "/home/ravel/Documents/Projet KERNEL FORGE/video"
KEN = os.path.join(BASE, "assets/kenney/kenney_background-elements-remastered/PNG/Default")
ART = os.path.join(BASE, "assets")
BLEND = os.path.join(BASE, "plateau_25d.blend")

SHOT_W, SHOT_H, FPS = 1280, 720, 25
FRAMES = 125

_img_cache = {}


def img(path):
    if path not in _img_cache:
        _img_cache[path] = bpy.data.images.load(path, check_existing=True)
    im = _img_cache[path]
    try:
        im.colorspace_settings.name = "sRGB"
    except Exception:
        pass
    return im


def alpha_mat(name, image, repeat_x=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND" if repeat_x == 1.0 else "REPEAT"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (repeat_x, 1.0, 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (0.8, 0.8, 0.8, 1.0)
    return m


def sky_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.93, 0.66, 0.36, 1.0)
    ramp.color_ramp.elements[1].position = 1.00
    ramp.color_ramp.elements[1].color = (0.035, 0.075, 0.20, 1.0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def plane(name, mat, width, height, loc, rot=(1.5707963, 0.0, 0.0)):
    mesh = bpy.data.meshes.new(name)
    hw, hh = width / 2.0, height / 2.0
    mesh.from_pydata([(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)],
                     [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def sprite(name, image, height, loc, y_rot=0.0):
    w = height * (image.size[0] / max(1, image.size[1]))
    o = plane(name, alpha_mat("m_" + name, image), w, height, loc,
              (1.5707963, 0.0, y_rot))
    return o


def band(name, image, tiles, base_y, base_h, z):
    """Bande repetee calee au sol, largeur deduite du ratio de l'image."""
    ratio = image.size[1] / max(1, image.size[0])
    h = base_h
    w = h / max(ratio, 1e-4)
    return plane(name, alpha_mat("m_" + name, image, repeat_x=float(tiles)),
                 w * tiles, h, (0, base_y, z + h / 2.0))


bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.resolution_x = SHOT_W
scn.render.resolution_y = SHOT_H
scn.render.fps = FPS
scn.frame_start = 1
scn.frame_end = FRAMES

world = bpy.data.worlds.new("monde")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.05, 0.08, 0.18, 1.0)
    bg.inputs[1].default_value = 1.0

# --- plans de profondeur, du plus lointain au plus proche -------------------
plane("L0_ciel", sky_mat("m_ciel"), 130.0, 70.0, (0, 46.0, 24.0))

sun = img(os.path.join(KEN, "sun.png"))
plane("L0_soleil", alpha_mat("m_soleil", sun), 9.0, 9.0, (-16.0, 44.0, 22.0))

for i, fn in enumerate(("cloud1.png", "cloud4.png", "cloud7.png", "cloud8.png")):
    c = img(os.path.join(KEN, fn))
    plane("L1_nuage_%d" % i, alpha_mat("m_nuage%d" % i, c),
          11.0, 11.0 * c.size[1] / c.size[0],
          (-15.0 + 10.0 * i, 40.0, 25.0 - 2.5 * (i % 3)))

band("L2_batiments", img(os.path.join(KEN, "castleSmall.png")), 9, 30.0, 15.0, 0.0)
band("L2_arbres", img(os.path.join(KEN, "treeLong.png")), 14, 22.0, 8.5, 0.0)
band("L3_futaies", img(os.path.join(KEN, "treePineOrange.png")), 11, 14.0, 6.5, 0.0)

# --- decor plateau ----------------------------------------------------------
sol = bpy.data.materials.new("m_sol")
sol.use_nodes = True
bsdf = sol.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.055, 0.075, 0.13, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.65
ground = plane("L4_sol", sol, 90.0, 90.0, (0, 12.0, 0.0), (0.0, 0.0, 0.0))

bak = bpy.data.materials.new("m_fond")
bak.use_nodes = True
b = bak.node_tree.nodes.get("Principled BSDF")
if b:
    b.inputs["Base Color"].default_value = (0.02, 0.11, 0.16, 1.0)
    b.inputs["Roughness"].default_value = 0.8
plane("L4_ecran", bak, 10.5, 5.6, (0, 8.6, 3.0))

wm = img(os.path.join(ART, "uniflow-wordmark-blanc-net-2400.png"))
plane("L4_wordmark", alpha_mat("m_wordmark", wm), 7.4,
      7.4 * wm.size[1] / wm.size[0], (0, 8.4, 3.4))

desk_mat = bpy.data.materials.new("m_bureau")
desk_mat.use_nodes = True
d = desk_mat.node_tree.nodes.get("Principled BSDF")
if d:
    d.inputs["Base Color"].default_value = (0.16, 0.24, 0.30, 1.0)
    d.inputs["Roughness"].default_value = 0.42

bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 2.6, 0.40))
desk = bpy.context.view_layer.objects.active
desk.name = "L4_bureau"
desk.scale = (4.2, 0.72, 0.80)
desk.data.materials.append(desk_mat)

logo = img(os.path.join(ART, "uniflow-ecusson-net-1024.png"))
plane("L5_ecusson", alpha_mat("m_ecusson", logo), 0.62, 0.62, (0, 2.22, 0.46))

# --- personnages ------------------------------------------------------------
uni = sprite("L4_UNI", img(os.path.join(ART, "uni_wave.png")), 1.78,
             (-1.12, 1.55, 0.89))
arch = sprite("L4_ARCHLORD", img(os.path.join(ART, "archlord_pointing.png")), 1.78,
              (1.22, 1.55, 0.89))

for i, (fn, x, w) in enumerate((("bush1.png", -3.5, 1.9), ("fence.png", 3.6, 2.1))):
    c = img(os.path.join(KEN, fn))
    plane("L6_fore_%d" % i, alpha_mat("m_fore%d" % i, c),
          w, w * c.size[1] / c.size[0], (x, -5.0, w * c.size[1] / c.size[0] / 2.0))

# --- lumiere : le sol et le bureau sont en Principled, il faut un soleil -----
sun_data = bpy.data.lights.new("soleil", type="SUN")
sun_data.energy = 3.2
sun_data.color = (1.0, 0.86, 0.70)
sun_data.angle = 0.03
lamp = bpy.data.objects.new("Soleil", sun_data)
bpy.context.collection.objects.link(lamp)
lamp.rotation_euler = (0.72, -0.22, 0.48)

# --- camera : dolly avant + legere chute ------------------------------------
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 38.0
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
scn.camera = cam
cam.rotation_euler = (1.5707963, 0.0, 0.0)
cam.location = (0.0, -9.2, 2.05)
cam.keyframe_insert("location", frame=1)
cam.location = (0.0, -6.5, 1.45)
cam.keyframe_insert("location", frame=FRAMES)
try:
    for strip in cam.animation_data.action.layers[0].strips:
        for cb in strip.channelbags:
            for fc in cb.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing = "EASE_IN_OUT"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
except (IndexError, AttributeError) as exc:
    print("PLATEAU_25D easing ignore:", exc)

# --- rendu ------------------------------------------------------------------
for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try:
        scn.render.engine = cand
    except Exception:
        continue
    if scn.render.engine == cand:
        break
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(BASE, "work", "plateau_25d_preview_####")

if bpy.context.preferences.view.show_splash:
    bpy.context.preferences.view.show_splash = False

for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == "VIEW_3D":
        for sp in area.spaces:
            if sp.type == "VIEW_3D":
                sp.shading.type = "MATERIAL"
                sp.region_3d.view_perspective = "CAMERA"
                sp.overlay.show_overlays = False
                area.tag_redraw()

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("PLATEAU_25D OK engine=%s blend=%s" % (scn.render.engine, BLEND))
