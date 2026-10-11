const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const pkg = require(path.join(root, 'node_modules/gsap/package.json'));
if (pkg.version !== '3.14.2') throw new Error('Expected GSAP 3.14.2');
const data = fs.readFileSync(path.join(root, 'node_modules/gsap/dist/gsap.min.js'));
for (const name of ['background', 'intro']) {
  const dest = path.join(root, 'assets', name, 'assets', 'gsap.min.js');
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, data);
  console.log(name + ': gsap ' + pkg.version + ' sha256=' + crypto.createHash('sha256').update(data).digest('hex'));
}
