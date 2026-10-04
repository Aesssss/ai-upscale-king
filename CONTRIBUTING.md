# Contributing

Bug reports, documentation improvements and pull requests are welcome. Use Traditional Chinese or English. See `docs/BUILDING.md` for setup and tests.

Keep the main interface simple: one size choice and one primary action; disclose less-used options under advanced settings. Preserve the offline processing promise, source files, aspect ratio and orientation by default. Do not add telemetry, automatic uploads or runtime model fetching.

For behaviour changes, run the relevant core tests and Qt acceptance checks. For packaging changes, run native builds and packaged export checks on the affected platform. Explain the actual behaviour, validation, and material limitations in the pull request.

Use synthetic or openly licensed fixtures. Do not commit private design files, credentials, local account paths, proprietary reference software or generated build directories. Model weights stay outside Git and are fetched from the pinned upstream manifest.

Contributions are licensed under Apache-2.0. Retain upstream attribution and third-party notices when adapting code.
