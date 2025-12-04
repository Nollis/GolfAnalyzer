import struct
import json
import sys

print("Script started...")

def parse_glb(file_path):
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            print("Not a valid GLB file")
            return

        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]

        # Read chunk 0 (JSON)
        chunk_length = struct.unpack('<I', f.read(4))[0]
        chunk_type = f.read(4)
        
        if chunk_type != b'JSON':
            print("First chunk is not JSON")
            return

        json_data = f.read(chunk_length)
        data = json.loads(json_data)
        
        if 'nodes' in data:
            print("Nodes found:")
            for i, node in enumerate(data['nodes']):
                if 'name' in node:
                    print(f"{i}: {node['name']}")
        
        if 'skins' in data:
            print("\nSkins found:")
            for skin in data['skins']:
                print(f"Skin name: {skin.get('name', 'unnamed')}")
                if 'joints' in skin:
                    print("Joints:")
                    for joint_idx in skin['joints']:
                        # Find name of this joint node
                        node_name = data['nodes'][joint_idx].get('name', f"Node {joint_idx}")
                        print(f"  - {node_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_glb.py <path_to_glb>")
    else:
        parse_glb(sys.argv[1])
