# Security and privacy

The application processes images locally, bundles both AI models, and does not upload images, perform cloud inference, collect telemetry or check for updates at runtime. Build tools use network access for dependencies and upstream resources. Cloud-synced input/output folders remain controlled by their sync service.

Model weights are SHA-256 checked before loading and use PyTorch `weights_only=True`. Output does not copy source EXIF/GPS. Source images are not overwritten. Temporary AI buffers are created in local temporary directories and cleaned up at the end of the job.

For a potential security issue, use the repository's private vulnerability reporting feature if available. Do not post credentials, confidential images or exploit details involving private user data in a public Issue. General non-sensitive reports can describe version, operating system and reproducible steps using synthetic fixtures.

The 1.x release line is the current supported line. Dependencies and build checks are pinned for reproducibility; maintainers should review updates before changing those pins.
