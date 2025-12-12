import fs from 'node:fs'
import parseTorrent from 'parse-torrent'

const filename = process.argv[2]
if (!filename) {
  console.error('Usage: node parse.js <torrent-file>')
  process.exit(1)
}

const buffer = fs.readFileSync(filename)
const torrent = parseTorrent(buffer)

// 1. Get the name of the torrent
console.log('Torrent Name:', torrent.name)

// 2. List all files
// The .files property handles both single and multi-file structures automatically
torrent.files.forEach((file, index) => {
  console.log(`${index + 1}. ${file.path} (${file.length} bytes)`)
})