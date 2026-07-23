// SPDX-FileCopyrightText: 2026 Bora Yarkın
// SPDX-License-Identifier: GPL-3.0-only

import {createHash} from 'node:crypto'
import {mkdir, writeFile} from 'node:fs/promises'
import {dirname, join} from 'node:path'
import {fileURLToPath} from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const outputRoot = join(root, 'public')
const owner = process.env.IMPRESS_REMOTE_REPO_OWNER || 'bora-yarkin'
const repo = process.env.IMPRESS_REMOTE_REPO_NAME || 'libreoffice-impress-remote'
const ref = process.env.IMPRESS_REMOTE_SOURCE_REF || 'main'
const rawRoot = `https://raw.githubusercontent.com/${owner}/${repo}/${ref}`
const apiRoot = `https://api.github.com/repos/${owner}/${repo}/contents`
const webFiles = ['index.html', 'app.css', 'app.js']

async function fetchText(url){
  const response = await fetch(url, {
    headers: {
      'Accept': url.startsWith(apiRoot)
        ? 'application/vnd.github+json'
        : 'text/plain, application/json',
      'User-Agent': 'impress-remote-cloudflare-build',
    },
  })
  if(!response.ok){
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`)
  }
  return response.text()
}

function sha256(data){
  return createHash('sha256').update(data).digest()
}

function sha256Hex(data){
  return sha256(data).toString('hex')
}

function sha256Sri(data){
  return `sha256-${sha256(data).toString('base64')}`
}

async function writePublicFile(relativePath, data){
  const destination = join(outputRoot, relativePath)
  await mkdir(dirname(destination), {recursive: true})
  await writeFile(destination, data)
}

async function fetchSharedFile(relativePath){
  return fetchText(`${rawRoot}/shared/${relativePath}`)
}

async function localizationNames(){
  const payload = JSON.parse(
    await fetchText(`${apiRoot}/shared/localizations?ref=${encodeURIComponent(ref)}`),
  )
  if(!Array.isArray(payload)){
    throw new Error('GitHub localization listing did not return an array.')
  }
  return payload
    .map(entry => typeof entry.name === 'string' ? entry.name : '')
    .filter(name => /^[a-z][a-z0-9_-]*\.json$/i.test(name))
    .sort()
}

function assetEntry(data){
  return {
    sha256: sha256Hex(data),
    sha256SRI: sha256Sri(data),
    bytes: Buffer.byteLength(data),
  }
}

function assetManifest(files){
  const bundleHash = createHash('sha256')
  const entries = {}
  for(const [relativePath, data] of files){
    const entry = assetEntry(data)
    entries[relativePath] = entry
    bundleHash.update(relativePath)
    bundleHash.update(Buffer.from([0]))
    bundleHash.update(entry.sha256)
  }
  return {
    version: 1,
    bundleSha256: bundleHash.digest('hex'),
    files: entries,
  }
}

function localizationManifest(locales){
  return {
    version: 1,
    defaultLocale: 'en',
    locales,
  }
}

async function main(){
  const files = []
  const rawWeb = new Map()
  for(const file of webFiles){
    rawWeb.set(file, await fetchSharedFile(`webui/${file}`))
  }

  const trustedIndex = rawWeb
    .get('index.html')
    .replace('href="/app.css"', `href="/app.css" integrity="${sha256Sri(rawWeb.get('app.css'))}"`)
    .replace('src="/app.js"', `src="/app.js" integrity="${sha256Sri(rawWeb.get('app.js'))}"`)

  await writePublicFile('index.html', trustedIndex)
  files.push(['index.html', trustedIndex])
  for(const file of ['app.css', 'app.js']){
    const data = rawWeb.get(file)
    await writePublicFile(file, data)
    files.push([file, data])
  }

  const localeFiles = await localizationNames()
  const locales = []
  for(const file of localeFiles){
    const data = await fetchSharedFile(`localizations/${file}`)
    await writePublicFile(`localizations/${file}`, data)
    files.push([`localizations/${file}`, data])
    locales.push(file.replace(/\.json$/i, ''))
  }

  const localizationManifestText = JSON.stringify(localizationManifest(locales), null, 2) + '\n'
  await writePublicFile('localizations/manifest.json', localizationManifestText)
  files.push(['localizations/manifest.json', localizationManifestText])

  const assetManifestText = JSON.stringify(assetManifest(files), null, 2) + '\n'
  await writePublicFile('asset-manifest.json', assetManifestText)
}

main().catch(error => {
  console.error(error)
  process.exit(1)
})
