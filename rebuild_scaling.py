"""
rebuild_scaling.py — Rebuilds Stats_Scaling_NumPlayers with rows for 5 and 6 players.
Uses targeted binary patching instead of full header parsing.
"""

import struct, os

BASE = "C:/Users/joaop/Desenvolvimento/Projects/remnant-mod/extracted"
OUTPUT = "C:/Users/joaop/Desenvolvimento/Projects/remnant-mod/modified"

UASSET_PATH = os.path.join(BASE, "Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uasset")
UEXP_PATH = os.path.join(BASE, "Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uexp")


def find_all_int32(data, value):
    """Find all offsets where int32 == value."""
    results = []
    for off in range(0, len(data) - 3):
        if struct.unpack_from('<i', data, off)[0] == value:
            results.append(off)
    return results


def read_fstring_at(data, off):
    """Read FString at offset, return (string, end_offset)."""
    slen = struct.unpack_from('<i', data, off)[0]; off += 4
    if slen > 0:
        s = data[off:off + slen - 1].decode('utf-8', errors='replace')
        off += slen
        return s, off
    elif slen < 0:
        chars = -slen
        s = data[off:off + chars * 2].decode('utf-16-le', errors='replace').rstrip('\x00')
        off += chars * 2
        return s, off
    return '', off


def main():
    os.makedirs(OUTPUT, exist_ok=True)

    with open(UASSET_PATH, 'rb') as f:
        uasset_orig = f.read()
    with open(UEXP_PATH, 'rb') as f:
        uexp_orig = f.read()

    print(f"Original .uasset: {len(uasset_orig)} bytes")
    print(f"Original .uexp: {len(uexp_orig)} bytes")

    # === STEP 1: Understand the uasset structure ===
    # We know from previous analysis:
    # - NameCount = 32, NameOffset = 193
    # - The header is at the beginning, name table at offset 193
    # Let me find these values in the header

    # Parse minimal header
    off = 0
    tag = struct.unpack_from('<I', uasset_orig, off)[0]; off += 4
    assert tag == 0x9E2A83C1, f"Bad magic: 0x{tag:08X}"

    legacy_ver = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4
    off += 4  # legacy UE3
    off += 4  # file version UE4
    off += 4  # file version licensee

    # Custom versions
    if legacy_ver <= -7:
        num_custom = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4
        off += num_custom * 20

    total_hdr_size_off = off
    total_hdr_size = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    # FolderName
    folder_str, off = read_fstring_at(uasset_orig, off)

    pkg_flags_off = off
    off += 4  # package flags

    name_count_off = off
    name_count = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4
    name_offset_off = off
    name_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    # Gatherable text
    gath_count_off = off; off += 4
    gath_offset_off = off
    gath_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    export_count_off = off
    export_count = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4
    export_offset_off = off
    export_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    import_count_off = off
    import_count = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4
    import_offset_off = off
    import_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    depends_offset_off = off
    depends_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    soft_pkg_count_off = off; off += 4
    soft_pkg_offset_off = off
    soft_pkg_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    searchable_offset_off = off
    searchable_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    thumbnail_offset_off = off
    thumbnail_offset = struct.unpack_from('<i', uasset_orig, off)[0]; off += 4

    print(f"\nHeader fields:")
    print(f"  TotalHeaderSize: {total_hdr_size} (at offset {total_hdr_size_off})")
    print(f"  NameCount: {name_count} (at offset {name_count_off})")
    print(f"  NameOffset: {name_offset} (at offset {name_offset_off})")
    print(f"  GathOffset: {gath_offset} (at offset {gath_offset_off})")
    print(f"  ExportCount: {export_count} (at offset {export_count_off})")
    print(f"  ExportOffset: {export_offset} (at offset {export_offset_off})")
    print(f"  ImportCount: {import_count} (at offset {import_count_off})")
    print(f"  ImportOffset: {import_offset} (at offset {import_offset_off})")
    print(f"  DependsOffset: {depends_offset} (at offset {depends_offset_off})")
    print(f"  SoftPkgOffset: {soft_pkg_offset} (at offset {soft_pkg_offset_off})")
    print(f"  SearchableOffset: {searchable_offset} (at offset {searchable_offset_off})")
    print(f"  ThumbnailOffset: {thumbnail_offset} (at offset {thumbnail_offset_off})")

    # === STEP 2: Read name table ===
    names = []
    nt_off = name_offset
    for i in range(name_count):
        s, nt_off = read_fstring_at(uasset_orig, nt_off)
        h = struct.unpack_from('<I', uasset_orig, nt_off)[0]; nt_off += 4
        names.append((s, h))

    name_table_end = nt_off
    print(f"\n  Name table: {name_offset} - {name_table_end} ({name_table_end - name_offset} bytes)")

    # === STEP 3: Build new name entries ===
    # "5" = int32(2) + "5\0" + uint32(hash)
    def build_name_entry(s, hash_val=0):
        encoded = (s + '\x00').encode('utf-8')
        return struct.pack('<i', len(encoded)) + encoded + struct.pack('<I', hash_val)

    name5 = build_name_entry("5")
    name6 = build_name_entry("6")
    extra = name5 + name6
    shift = len(extra)

    print(f"\n  Adding 2 names: {shift} bytes inserted at offset {name_table_end}")

    # === STEP 4: Build new .uasset ===
    new_uasset = bytearray()
    new_uasset += uasset_orig[:name_table_end]
    new_uasset += extra
    new_uasset += uasset_orig[name_table_end:]

    # Patch NameCount
    struct.pack_into('<i', new_uasset, name_count_off, name_count + 2)

    # Patch TotalHeaderSize
    struct.pack_into('<i', new_uasset, total_hdr_size_off, total_hdr_size + shift)

    # Patch all offsets that are >= name_table_end
    offset_fields = [
        ('GathOffset', gath_offset_off, gath_offset),
        ('ExportOffset', export_offset_off, export_offset),
        ('ImportOffset', import_offset_off, import_offset),
        ('DependsOffset', depends_offset_off, depends_offset),
        ('SoftPkgOffset', soft_pkg_offset_off, soft_pkg_offset),
        ('SearchableOffset', searchable_offset_off, searchable_offset),
        ('ThumbnailOffset', thumbnail_offset_off, thumbnail_offset),
    ]

    for field_name, field_off, old_val in offset_fields:
        if old_val > 0 and old_val >= name_table_end:
            new_val = old_val + shift
            struct.pack_into('<i', new_uasset, field_off, new_val)
            print(f"  Shifted {field_name}: {old_val} -> {new_val}")

    # Find and update generation name counts
    # Search for the generation array by looking for the guid followed by gen data
    # The guid is 16 bytes, then int32 gen_count, then gen_count * (int32 export_count + int32 name_count)
    # We know name_count=32, so look for int32=32 after the guid area
    # Actually, let me search for int32=32 that's in the generation array
    # It should be at an even offset, paired with an export count (likely 1 or 2)

    # Scan the header area for generation entries
    # Generations come after: guid(16) + gen_count(4)
    # Each gen: export_count(4) + name_count(4)
    # The name_count in generations should match the package name_count

    # Find GUID (16 bytes) in the header - it's after the searchable/thumbnail offsets
    # Let's find it by looking for gen_count=1 followed by (export_count, 32)
    print("\n  Looking for generation entries...")
    for scan_off in range(off, min(off + 200, len(new_uasset) - 16)):
        gen_count = struct.unpack_from('<i', new_uasset, scan_off)[0]
        if gen_count == 1:
            # Check if next 8 bytes look like a generation entry
            gen_exports = struct.unpack_from('<i', new_uasset, scan_off + 4)[0]
            gen_names = struct.unpack_from('<i', new_uasset, scan_off + 8)[0]
            if gen_names == name_count and 0 < gen_exports < 100:
                print(f"  Found generation at offset {scan_off}: exports={gen_exports}, names={gen_names}")
                # Patch name count in generation
                struct.pack_into('<i', new_uasset, scan_off + 8, gen_names + 2)
                print(f"  Patched generation names: {gen_names} -> {gen_names + 2}")
                break

    # Find and update export entry's SerialSize
    # Export table entry layout for UE4:
    # int32 ClassIndex, int32 SuperIndex, int32 TemplateIndex, int32 OuterIndex,
    # FName ObjectName (int32 + int32), uint32 ObjectFlags,
    # int64 SerialSize, int64 SerialOffset, ...
    if export_count > 0:
        exp_table_off = export_offset + shift  # shifted
        print(f"\n  Export table at offset {exp_table_off}:")

        # Read export entry fields
        e_off = exp_table_off
        class_idx = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        super_idx = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        template_idx = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        outer_idx = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        obj_name_idx = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        obj_name_extra = struct.unpack_from('<i', new_uasset, e_off)[0]; e_off += 4
        obj_flags = struct.unpack_from('<I', new_uasset, e_off)[0]; e_off += 4

        serial_size_off = e_off
        serial_size = struct.unpack_from('<q', new_uasset, e_off)[0]; e_off += 8
        serial_offset = struct.unpack_from('<q', new_uasset, e_off)[0]; e_off += 8

        obj_name = names[obj_name_idx][0] if 0 <= obj_name_idx < len(names) else f"idx{obj_name_idx}"
        print(f"    ClassIdx={class_idx}, SuperIdx={super_idx}, Name='{obj_name}'")
        print(f"    SerialSize={serial_size} at offset {serial_size_off}")
        print(f"    SerialOffset={serial_offset}")

        # Calculate new serial size (uexp will be bigger)
        row_size = 8 + 13 * 29 + 8  # FName + 13 properties + None = 393
        new_serial_size = serial_size + 2 * row_size
        struct.pack_into('<q', new_uasset, serial_size_off, new_serial_size)
        print(f"    New SerialSize: {serial_size} -> {new_serial_size}")

        # Patch SerialOffset to match new TotalHeaderSize
        new_serial_offset = total_hdr_size + shift
        struct.pack_into('<q', new_uasset, serial_size_off + 8, new_serial_offset)
        print(f"    New SerialOffset: {serial_offset} -> {new_serial_offset}")

    # === STEP 5: Build new .uexp ===
    print(f"\n--- Building new .uexp ---")

    # Row data builder
    def build_row(row_name_idx, values):
        """Build one DataTable row (FName + 13 props + None)."""
        row = bytearray()
        row += struct.pack('<ii', row_name_idx, 0)  # FName

        props = [
            (19, "EnemyHealthScalar"),
            (18, "EnemyDamageScalar"),
            (27, "SpawnQuantityScalar"),
            (28, "SpawnWeightScalar"),
            (13, "CurrencyScalar"),
            (20, "ExperienceScalar"),
            (22, "FriendlyFireDamageScalar"),
            (17, "EliteHealthScalar"),
            (16, "EliteDamageScalar"),
            (11, "BruteHealthScalar"),
            (10, "BruteDamageScalar"),
            (9, "BossHealthScalar"),
            (8, "BossDamageScalar"),
        ]

        for idx, name in props:
            row += struct.pack('<ii', idx, 0)   # prop name FName
            row += struct.pack('<ii', 21, 0)    # "FloatProperty" FName
            row += struct.pack('<ii', 4, 0)     # size=4, arrayIdx=0
            row += struct.pack('<B', 0)          # no guid
            row += struct.pack('<f', values.get(name, 1.0))

        row += struct.pack('<ii', 23, 0)  # None terminator
        return row

    idx_5 = len(names)      # 32
    idx_6 = len(names) + 1  # 33

    row5 = build_row(idx_5, {"SpawnQuantityScalar": 2.33, "SpawnWeightScalar": 1.60})
    row6 = build_row(idx_6, {"SpawnQuantityScalar": 2.66, "SpawnWeightScalar": 1.60})

    print(f"  Row 5: {len(row5)} bytes")
    print(f"  Row 6: {len(row6)} bytes")

    # Build new uexp
    footer = uexp_orig[-4:]  # C1 83 2A 9E
    new_uexp = bytearray(uexp_orig[:-4])  # everything except footer
    new_uexp += row5 + row6 + footer

    # Patch NumRows: 4 -> 6 at offset 41
    struct.pack_into('<i', new_uexp, 41, 6)

    print(f"  New .uexp: {len(new_uexp)} bytes (was {len(uexp_orig)})")

    # === STEP 6: Save files ===
    out_dir = os.path.join(OUTPUT, "Remnant/Content/_Core/Stats")
    os.makedirs(out_dir, exist_ok=True)

    uasset_out = os.path.join(out_dir, "Stats_Scaling_NumPlayers.uasset")
    uexp_out = os.path.join(out_dir, "Stats_Scaling_NumPlayers.uexp")

    with open(uasset_out, 'wb') as f:
        f.write(new_uasset)
    with open(uexp_out, 'wb') as f:
        f.write(new_uexp)

    print(f"\n  Saved: {uasset_out} ({len(new_uasset)} bytes)")
    print(f"  Saved: {uexp_out} ({len(new_uexp)} bytes)")

    # === STEP 7: Verify ===
    print(f"\n--- Verification ---")
    name_map = {i: n[0] for i, n in enumerate(names)}
    name_map[idx_5] = "5"
    name_map[idx_6] = "6"

    nr = struct.unpack_from('<i', new_uexp, 41)[0]
    print(f"  NumRows: {nr}")
    v_off = 45
    for r in range(nr):
        ridx = struct.unpack_from('<i', new_uexp, v_off)[0]
        rname = name_map.get(ridx, f"idx{ridx}")
        v_off += 8
        non_default = []
        for p in range(13):
            pidx = struct.unpack_from('<i', new_uexp, v_off)[0]
            v_off += 8 + 8 + 4 + 4 + 1  # skip name + type + size + arr + guid
            fval = struct.unpack_from('<f', new_uexp, v_off)[0]
            v_off += 4
            pname = name_map.get(pidx, f"idx{pidx}")
            if fval != 1.0:
                non_default.append(f"{pname}={fval:.2f}")
        v_off += 8  # None

        status = ', '.join(non_default) if non_default else "all 1.0"
        print(f"  Row '{rname}': {status}")

    remaining = len(new_uexp) - v_off
    print(f"  Footer: {remaining} bytes")


if __name__ == '__main__':
    main()
