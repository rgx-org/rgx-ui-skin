import os
import shutil
import subprocess
import tempfile

DEST_NAME = 'dist'
IGNORE_DIRS = [DEST_NAME, ".git", "olde"]
GIMP_PATH = '/Applications/GIMP.app/Contents/MacOS/gimp'
CONTENT_WIDTH = 15

XCF_TASKS = {
    'RGX/basic_interface/collection_bg.xcf': {
        'handler': 'collection_bg',
        'direction': 'right',
        'offset': 5,
        'layer_offset_x': 0,
        'layer_offset_y': 0,
    },
}

source_dir = os.getcwd()
destination_dir = os.path.join(source_dir, DEST_NAME)

os.makedirs(destination_dir, exist_ok=True)

extensions = ['.bmp', '.tga', '.jpg']

for root, dirs, files in os.walk(source_dir):
    print(f"PRE_DIR: {dirs}")
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    print(f"POST_DIR: {dirs}")
    for file in files:
        if file.lower().endswith(tuple(extensions)):
            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, source_dir)
            target_folder = os.path.join(destination_dir, relative_path)
            os.makedirs(target_folder, exist_ok=True)

            dest_path = os.path.join(target_folder, file)
            shutil.copy2(source_path, dest_path)
            print(f"Copied: {source_path} → {dest_path}")


# ---------------------------------------------------------------------------
# GIMP batch processing (Python-Fu, GIMP 3 GI bindings)
# ---------------------------------------------------------------------------

def run_gimp_python(script_path):
    if not os.path.exists(GIMP_PATH):
        print(f"Error: GIMP not found at {GIMP_PATH}")
        return None
    print("Running GIMP Python-Fu batch...")
    result = subprocess.run(
        [GIMP_PATH, '-i', '--quit',
         '--batch-interpreter=python-fu-eval',
         '-b', f'exec(open("{script_path}").read())'],
        capture_output=True, text=True, timeout=300,
    )
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"GIMP error (exit {result.returncode}):\n{result.stderr}")
    return result


def process_collection_bg(xcf_rel_path, direction, offset,
                          layer_offset_x, layer_offset_y):
    xcf_abs = os.path.join(source_dir, xcf_rel_path)
    rel_dir = os.path.dirname(xcf_rel_path)
    dest = os.path.join(destination_dir, rel_dir)
    os.makedirs(dest, exist_ok=True)

    script = f'''import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gio

CONTENT_WIDTH = {CONTENT_WIDTH}
DIRECTION = "{direction}"
OFFSET = {offset}
LAYER_OFFSET_X = {layer_offset_x}
LAYER_OFFSET_Y = {layer_offset_y}

def find_layer(image, name):
    for layer in image.get_layers():
        if layer.get_name() == name:
            return layer
    return None

def move_layer(layer, dx, dy):
    if layer is None or (dx == 0 and dy == 0):
        return
    success, ox, oy = layer.get_offsets()
    layer.set_offsets(ox + dx, oy + dy)

def export_bmp_flat(flat_image, path):
    """Export an already-flattened image to BMP."""
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure('file-bmp-export')
    config = proc.create_config()
    config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
    config.set_property('image', flat_image)
    config.set_property('file', Gio.File.new_for_path(path))
    config.set_property('rgb-format', 'rgb-888')
    config.set_property('write-color-space', False)
    proc.run(config)
    print("Exported: " + path)

def export_bmp(image, path):
    """Duplicate, flatten, export, delete duplicate."""
    dup = image.duplicate()
    dup.flatten()
    export_bmp_flat(dup, path)
    dup.delete()

def duplicate_lv_layer(work, layer_name, count):
    """Duplicate layer_name `count` times in work image, returning
    a list of [original, copy1, copy2, ...] (length count+1)."""
    original = find_layer(work, layer_name)
    if original is None:
        return []
    layers = [original]
    pdb = Gimp.get_pdb()
    for i in range(count):
        copy_proc = pdb.lookup_procedure('gimp-layer-copy')
        copy_cfg = copy_proc.create_config()
        copy_cfg.set_property('layer', original)
        copy_result = copy_proc.run(copy_cfg)
        cp = copy_result.index(1)
        insert_proc = pdb.lookup_procedure('gimp-image-insert-layer')
        insert_cfg = insert_proc.create_config()
        insert_cfg.set_property('image', work)
        insert_cfg.set_property('layer', cp)
        insert_cfg.set_property('parent', None)
        insert_cfg.set_property('position', 0)
        insert_proc.run(insert_cfg)
        layers.append(cp)
    return layers

# Load XCF
xcf_file = Gio.File.new_for_path("{xcf_abs}")
image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, xcf_file)
print("Loaded: {xcf_abs}")

# Step 1: export with current visible layers
export_bmp(image, "{os.path.join(dest, 'collection_bg.bmp')}")

# Step 2: show lv1, export g1..g5
lv1 = find_layer(image, "lv1")
move_layer(lv1, LAYER_OFFSET_X, LAYER_OFFSET_Y)
if lv1:
    lv1.set_visible(True)

for i in range(1, 6):
    export_bmp(image, "{dest}/collection_bg_g" + str(i) + ".bmp")

# Hide lv1
if lv1:
    lv1.set_visible(False)

# Step 3: lv2, lv3, lv4
for x in range(2, 5):
    # Hide previous level
    if x > 2:
        prev = find_layer(image, "lv" + str(x - 1))
        if prev:
            prev.set_visible(False)

    # Move current level layers by X/Y offset before anything else
    lv = find_layer(image, "lv" + str(x))
    move_layer(lv, LAYER_OFFSET_X, LAYER_OFFSET_Y)

    # Show current level
    if lv:
        lv.set_visible(True)

    # Duplicate image for layer copy work
    work = image.duplicate()
    work_lv = find_layer(work, "lv" + str(x))

    if work_lv:
        step = OFFSET + CONTENT_WIDTH
        success, ox, oy = work_lv.get_offsets()

        copies = duplicate_lv_layer(work, "lv" + str(x), x - 1)
        for n in range(1, len(copies)):
            cp = copies[n]
            if DIRECTION == "right":
                cp.set_offsets(ox + n * step, oy)
            elif DIRECTION == "left":
                cp.set_offsets(ox - n * step, oy)
            elif DIRECTION == "down":
                cp.set_offsets(ox, oy + n * step)
            elif DIRECTION == "up":
                cp.set_offsets(ox, oy - n * step)

    work.flatten()

    # Export 5 BMPs: g[(x-1)*5+1] .. g[x*5]
    start = (x - 1) * 5 + 1
    for i in range(5):
        idx = start + i
        export_bmp_flat(work, "{dest}/collection_bg_g" + str(idx) + ".bmp")

    work.delete()

image.delete()
'''

    fd, script_path = tempfile.mkstemp(suffix='.py', prefix='gimp_batch_')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(script)
        print(f"Processing XCF: {xcf_rel_path}")
        run_gimp_python(script_path)
        print(f"Done: {xcf_rel_path}")
    finally:
        os.unlink(script_path)


# -- XCF processing phase --------------------------------------------------
for xcf_path, cfg in XCF_TASKS.items():
    if not os.path.exists(os.path.join(source_dir, xcf_path)):
        print(f"Warning: XCF not found: {xcf_path}")
        continue
    if cfg['handler'] == 'collection_bg':
        process_collection_bg(
            xcf_path, cfg['direction'], cfg['offset'],
            cfg.get('layer_offset_x', 0), cfg.get('layer_offset_y', 0),
        )
