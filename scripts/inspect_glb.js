const fs = require('fs');

const filePath = process.argv[2];
if (!filePath) {
    console.log("Usage: node inspect_glb.js <path>");
    process.exit(1);
}

const buffer = fs.readFileSync(filePath);

// GLB Header: magic(4) + version(4) + length(4)
const magic = buffer.readUInt32LE(0);
if (magic !== 0x46546C67) { // 'glTF'
    console.log("Not a valid GLB");
    process.exit(1);
}

// Chunk 0: length(4) + type(4) + data
const chunkLength = buffer.readUInt32LE(12);
const chunkType = buffer.readUInt32LE(16);

if (chunkType !== 0x4E4F534A) { // 'JSON'
    console.log("First chunk is not JSON");
    process.exit(1);
}

const jsonData = buffer.subarray(20, 20 + chunkLength).toString('utf8');
const json = JSON.parse(jsonData);

if (json.nodes) {
    console.log("Nodes found:");
    json.nodes.forEach((node, i) => {
        if (node.name) console.log(`${i}: ${node.name}`);
    });
} else {
    console.log("No nodes found");
}
