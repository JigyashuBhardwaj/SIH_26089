// Babel configuration for the mobile app.
// babel-preset-expo bundles the JSX/TypeScript transforms Expo Router and
// React Native need. No other plugins are added until a real requirement
// appears (see code quality rule: no unnecessary dependencies).
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
  };
};
