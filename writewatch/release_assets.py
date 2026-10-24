"""Canonical download names plus aliases for previously shipped updaters."""
ASSETS = {
    'Windows-portable.zip': 'Windows-x64-Portable.zip',
    'Windows-Setup.exe': 'Windows-x64-Setup.exe',
    'Linux-x86_64.tar.gz': 'Linux-x64.tar.gz',
    'x86_64.AppImage': 'Linux-x64.AppImage',
    'amd64.deb': 'Linux-x64.deb',
    'macOS-AppleSilicon.dmg': 'macOS-arm64.dmg',
    'macOS-AppleSilicon.zip': 'macOS-arm64.zip',
    'macOS-Intel.dmg': 'macOS-x64.dmg',
    'macOS-Intel.zip': 'macOS-x64.zip',
}


def download_notes(version, notes):
    base = f'https://github.com/JPLuker/WriteWatch/releases/download/v{version}/WriteWatch-{version}-'
    def link(label, suffix):
        return f'[{label}]({base}{suffix})'
    rows = [
        ('Windows x64', link('Installer', ASSETS['Windows-Setup.exe']) + ' · ' + link('Portable ZIP', ASSETS['Windows-portable.zip'])),
        ('Linux x64', link('DEB installer', ASSETS['amd64.deb']) + ' · ' + link('AppImage', ASSETS['x86_64.AppImage']) + ' · ' + link('tar.gz', ASSETS['Linux-x86_64.tar.gz'])),
        ('Mac Apple Silicon', link('DMG', ASSETS['macOS-AppleSilicon.dmg']) + ' · ' + link('ZIP', ASSETS['macOS-AppleSilicon.zip'])),
        ('Mac Intel', link('DMG', ASSETS['macOS-Intel.dmg']) + ' · ' + link('ZIP', ASSETS['macOS-Intel.zip'])),
    ]
    table = '| Platform | Downloads |\n| --- | --- |\n' + ''.join(f'| {platform} | {links} |\n' for platform, links in rows)
    return table + '\nOlder filename aliases are also attached for compatibility with existing updaters; their contents are identical. SHA256SUMS.txt covers every package.\n\n' + notes
