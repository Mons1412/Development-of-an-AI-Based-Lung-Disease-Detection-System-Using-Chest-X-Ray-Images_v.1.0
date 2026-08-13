# Third-party software

The portable package contains CPython and Python dependencies required by the
application.

- CPython license: `runtime/LICENSE.txt`
- Exact packaged Python distributions: `PORTABLE_RUNTIME_PACKAGES.txt`
- Dependency metadata and bundled license texts:
  `runtime/Lib/site-packages/*.dist-info/`
- Project dependency constraints: `app/pyproject.toml`
- Source environment lock snapshot: `app/requirements-lock.txt`

Third-party components remain subject to their respective licenses. This notice
does not replace the license text shipped with each component.
