const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

// The mobile app is one part of a multi-folder repo (mobile/, admin/,
// backend/, shared/). Metro only watches its own project root by default,
// so we extend it to the repo root to resolve imports from `shared/`
// without npm workspaces or symlink tooling.
const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [path.resolve(projectRoot, 'node_modules')];

module.exports = config;
