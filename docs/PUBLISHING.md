# Publishing

- Repository: https://github.com/alandarev/pi-quote
- Npm package: https://www.npmjs.com/package/pi-quote-jev

`pi-quote` is already owned on npm by someone else. Keep `pi-quote-jev` as the npm name.

## Before release

```bash
npm ci
npm run check
npm run test:e2e
npm pack --dry-run
```

The tarball should contain only `package.json`, `src/index.ts`, `README.md`, and `LICENSE`. No test output, local settings, credentials, or installed dependencies belong in it.

Check that README's supported Pi version matches `REVIEWED_PI_VERSION` in the source. Do not widen the version guard without reviewing the host APIs and running fullscreen tests on that version.

## Publish to npm

From this repository:

```bash
npm login
npm whoami
npm publish --access public
```

An expired npm token can produce a misleading 404 during publish. Check `npm whoami`; 401 means login needs renewal. Never commit `.npmrc` credentials or paste tokens into issues.

Verify publication:

```bash
npm view pi-quote-jev version
pi install npm:pi-quote-jev
```

Do not load this package alongside the old standalone `quote-selection.ts` extension. Disable that copy first. Reload or restart Pi only when no active tasks or children would be interrupted.

## GitHub release

Update the package version and lockfile before a new release. For the first release, version is already `0.1.0`.

```bash
VERSION=$(node -p 'JSON.parse(require("fs").readFileSync("package.json", "utf8")).version')
git add src test docs .github README.md LICENSE package.json package-lock.json tsconfig.json .gitignore
git commit -m "Release $VERSION"
git tag "v$VERSION"
git push origin master --follow-tags
gh release create "v$VERSION" --title "v$VERSION" --notes "Select text in Pi fullscreen, press Alt+Q, and reply below the quote. No clipboard needed. Requires Pi 1.0.3."
```

Until npm publication is complete, install the tagged GitHub release:

```bash
pi install git:github.com/alandarev/pi-quote@v0.1.2
```
