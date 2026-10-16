# Third-party notices

WriteWatch uses dynamically loaded PySide6 / Qt for Python and Shiboken6 (LGPLv3/GPL/commercial terms) and defusedxml (PSF license). PyInstaller's bootloader carries its distribution exception. Bundled Qt modules and dependencies retain their individual notices and terms.

Dependency license files from installed wheels are copied into packaged builds under `licenses/`. Qt shared libraries remain separate in the `_internal` directory of portable/installed distributions and can be replaced with compatible builds. The AppImage can be extracted to access those same libraries. No restriction is imposed on reverse engineering for debugging modifications to LGPL-covered components.

Corresponding upstream sources and license information:

- Qt for Python / Shiboken: https://code.qt.io/cgit/pyside/pyside-setup.git/ (version matching requirements.txt)
- Qt: https://code.qt.io/cgit/qt/ (matching bundled Qt version)
- Qt licensing: https://www.qt.io/licensing/open-source-lgpl-obligations
- defusedxml: https://github.com/tiran/defusedxml
- PyInstaller: https://github.com/pyinstaller/pyinstaller
- AppImage tooling: https://github.com/AppImage/appimagetool

Fade In and its marks belong to their respective owners. WriteWatch is an independent companion application.

Additional format readers: striprtf (BSD-3-Clause), markdown-it-py and mdurl (MIT), and pypdf (BSD-3-Clause). Their wheel license notices are included under `licenses/`. Sources: https://github.com/joshy/striprtf , https://github.com/executablebooks/markdown-it-py , https://github.com/executablebooks/mdurl , https://github.com/py-pdf/pypdf .
